from __future__ import annotations

import secrets
from datetime import datetime
from uuid import uuid4

import stripe

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..models import (
    Cart,
    CartItem,
    Coupon,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductTag,
    Tag,
    Variant,
    db,
)
from ..services import payments as payment_service
from ..services import shipping as shipping_service

store_bp = Blueprint("store", __name__)


def _get_or_create_cart() -> Cart:
    cart_id = session.get("cart_id")
    if cart_id:
        cart = Cart.query.get(cart_id)
        if cart:
            return cart
    session_id = session.get("session_id")
    if not session_id:
        session_id = uuid4().hex
        session["session_id"] = session_id
    cart = Cart(session_id=session_id)
    db.session.add(cart)
    db.session.commit()
    session["cart_id"] = cart.id
    return cart


@store_bp.route("/")
def index():
    products = (
        Product.query.filter_by(status="active")
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    featured_tags = Tag.query.limit(6).all()
    return render_template("store/index.html", products=products, featured_tags=featured_tags)


@store_bp.get("/products")
def product_list():
    query = Product.query.filter_by(status="active")
    tail = request.args.get("tail")
    color = request.args.get("color")
    grade = request.args.get("grade")
    status = request.args.get("status")
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)

    if status == "available":
        query = query.join(Product.variants).filter(Variant.stock_qty > 0)

    if tail or color or grade:
        query = query.join(Product.tags).join(ProductTag.tag)
        if tail:
            query = query.filter(Tag.slug == tail.lower())
        if color:
            query = query.filter(Tag.slug == color.lower())
        if grade:
            query = query.filter(Tag.slug == grade.lower())

    products = query.order_by(Product.created_at.desc()).all()

    if price_min or price_max:
        filtered = []
        for product in products:
            variant = product.primary_variant()
            if not variant:
                continue
            price = variant.price
            if price_min and price < price_min:
                continue
            if price_max and price > price_max:
                continue
            filtered.append(product)
        products = filtered

    return render_template("store/products.html", products=products)


@store_bp.get("/product/<string:sku>")
def product_detail(sku: str):
    product = Product.query.filter_by(sku=sku).first_or_404()
    variant = product.primary_variant()
    gallery = [pm.media for pm in product.media]
    return render_template("store/product_detail.html", product=product, variant=variant, gallery=gallery)


@store_bp.post("/cart/add")
def add_to_cart():
    variant_id = request.form.get("variant_id", type=int)
    if not variant_id:
        flash("เลือกสินค้าที่ต้องการก่อน", "error")
        return redirect(request.referrer or url_for("store.product_list"))

    variant = Variant.query.get_or_404(variant_id)
    if variant.stock_qty <= 0:
        flash("สินค้าหมดแล้ว", "error")
        return redirect(url_for("store.product_detail", sku=variant.product.sku))

    cart = _get_or_create_cart()
    existing = next((item for item in cart.items if item.variant_id == variant_id), None)

    if existing:
        existing.qty += 1
    else:
        item = CartItem(cart=cart, variant=variant, qty=1, price_at=variant.price)
        db.session.add(item)

    db.session.commit()
    flash("เพิ่มสินค้าในตะกร้าแล้ว", "success")
    return redirect(url_for("store.cart_view"))


@store_bp.get("/cart")
def cart_view():
    cart = _get_or_create_cart()
    totals = {
        "subtotal": cart.total(),
        "shipping": 0,
        "grand_total": cart.total(),
    }
    return render_template("store/cart.html", cart=cart, totals=totals)


@store_bp.post("/cart/remove/<int:item_id>")
def remove_from_cart(item_id: int):
    cart = _get_or_create_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("ลบสินค้าออกจากตะกร้าแล้ว", "info")
    return redirect(url_for("store.cart_view"))


@store_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = _get_or_create_cart()
    if not cart.items:
        flash("ตะกร้าว่าง", "error")
        return redirect(url_for("store.product_list"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        country = request.form.get("country", "TH")
        coupon_code = request.form.get("coupon")
        payment_method = request.form.get("payment_method", "promptpay")

        subtotal = cart.total()
        shipping_quote = (
            shipping_service.calculate_domestic()
            if country.upper() == "TH"
            else shipping_service.calculate_international()
        )

        discount = 0
        coupon: Coupon | None = None
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon and coupon.is_valid(subtotal):
                discount = coupon.discount_amount(subtotal)
            else:
                flash("คูปองไม่ถูกต้องหรือหมดอายุ", "warning")

        order_no = f"BT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(999):03d}"
        order = Order(
            order_no=order_no,
            status="pending",
            payment_method=payment_method,
            subtotal=subtotal,
            shipping_fee=shipping_quote.fee,
            discount=discount,
            currency="THB" if country.upper() == "TH" else "USD",
        )
        db.session.add(order)
        db.session.flush()

        for item in cart.items:
            variant = item.variant
            order_item = OrderItem(
                order=order,
                variant=variant,
                title_snapshot=variant.product.localized_title("th"),
                attrs_snapshot=variant.attributes_json,
                qty=item.qty,
                unit_price=item.price_at,
                total_price=item.total_price,
            )
            db.session.add(order_item)

        order.update_totals()

        payment = Payment(
            order=order,
            method=payment_method,
            amount=order.grand_total,
            status="init",
        )
        db.session.add(payment)

        if payment_method == "stripe":
            try:
                intent = payment_service.create_stripe_payment_intent(
                    amount=order.grand_total,
                    currency=order.currency,
                    metadata={"order_no": order.order_no},
                )
            except stripe.error.StripeError as exc:
                current_app.logger.exception(
                    "Stripe payment intent creation failed for order %s: %s",
                    order.order_no,
                    getattr(exc, 'user_message', str(exc)),
                )
                db.session.rollback()
                flash("Unable to start Stripe payment, please try again.", "error")
                return redirect(url_for("store.checkout"))
            payment.ref = intent.id
            payment.status = intent.status or payment.status
            amount_value = getattr(intent, "amount", None)
            if amount_value is not None:
                payment.amount = round(amount_value / 100, 2)

        if coupon:
            coupon.used_count += 1

        for item in list(cart.items):
            db.session.delete(item)
        db.session.commit()

        session.pop("cart_id", None)

        flash("สร้างคำสั่งซื้อแล้ว กรุณาชำระเงิน", "success")
        return redirect(url_for("store.order_status", order_no=order.order_no))

    return render_template("store/checkout.html", cart=cart)


@store_bp.get("/payment/qr/<string:order_no>")
def promptpay_qr(order_no: str) -> Response:
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    if order.grand_total <= 0:
        flash("ยอดชำระไม่ถูกต้อง", "error")
        return redirect(url_for("store.order_status", order_no=order_no))
    qr_bytes = payment_service.generate_promptpay_qr(order.grand_total)
    return Response(qr_bytes, mimetype="image/png")


@store_bp.get("/payment/stripe-intent/<string:order_no>")
def stripe_payment_intent(order_no: str):
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    if order.payment_method != "stripe":
        return jsonify({"error": "unsupported_method"}), 400
    payment: Payment | None = order.payments[-1] if order.payments else None
    if not payment or not payment.ref:
        return jsonify({"error": "payment_not_ready"}), 400
    try:
        intent = payment_service.retrieve_stripe_payment_intent(payment.ref)
    except stripe.error.StripeError as exc:
        current_app.logger.exception(
            "Stripe intent retrieval failed for order %s: %s",
            order.order_no,
            getattr(exc, 'user_message', str(exc)),
        )
        return jsonify({"error": "stripe_error"}), 502
    publishable_key = current_app.config.get("STRIPE_PUBLIC_KEY")
    if not publishable_key:
        return jsonify({"error": "missing_publishable_key"}), 500
    return jsonify(
        {
            "client_secret": intent.client_secret,
            "status": intent.status,
            "publishable_key": publishable_key,
            "amount": intent.amount,
            "currency": intent.currency,
        }
    )


@store_bp.post("/payment/stripe/confirm/<string:order_no>")
def stripe_confirm_payment(order_no: str):
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    payment: Payment | None = order.payments[-1] if order.payments else None
    if not payment or payment.method != "stripe" or not payment.ref:
        return jsonify({"error": "payment_not_found"}), 400
    try:
        intent = payment_service.retrieve_stripe_payment_intent(payment.ref)
    except stripe.error.StripeError as exc:
        current_app.logger.exception(
            "Stripe intent retrieval failed for order %s: %s",
            order.order_no,
            getattr(exc, 'user_message', str(exc)),
        )
        return jsonify({"error": "stripe_error"}), 502
    payment.status = intent.status
    if intent.status == "succeeded":
        payment.paid_at = datetime.utcnow()
        amount_received = getattr(intent, "amount_received", None) or getattr(intent, "amount", None)
        if amount_received is not None:
            payment.amount = round(amount_received / 100, 2)
        order.status = "paid"
    db.session.commit()
    return jsonify({"status": payment.status})


@store_bp.post("/payment/slip/<string:order_no>")
def upload_slip(order_no: str):
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    file: FileStorage | None = request.files.get("slip")
    if not file or file.filename == "":
        flash("กรุณาอัปโหลดสลิป", "error")
        return redirect(url_for("store.order_status", order_no=order_no))
    filename = secure_filename(f"{order_no}_slip_{datetime.utcnow().timestamp():.0f}.png")
    from ..services.media import save_upload

    url = save_upload(file, filename)
    payment = order.payments[-1] if order.payments else Payment(order=order, method="transfer")
    payment.slip_url = url
    payment.status = "init"
    db.session.add(payment)
    db.session.commit()
    flash("อัปโหลดสลิปเรียบร้อย รอตรวจสอบ", "success")
    return redirect(url_for("store.order_status", order_no=order_no))


@store_bp.get("/order/<string:order_no>")
def order_status(order_no: str):
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    return render_template("store/order_status.html", order=order)


@store_bp.get("/help")
def help_page():
    return render_template("store/help.html")
