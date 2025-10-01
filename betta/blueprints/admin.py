from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from ..services.settings import SETTINGS_SCHEMA, get_settings_values, save_settings
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from slugify import slugify

from ..models import (
    BlogPost,
    Media,
    Order,
    Payment,
    Product,
    ProductMedia,
    Shipment,
    User,
    Variant,
    db,
)
from ..services.media import save_upload

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_app_request
def require_login_for_admin_pages():
    if request.blueprint == "admin" and request.endpoint not in {"admin.login", "admin.static"}:
        if not current_user.is_authenticated:
            return redirect(url_for("admin.login"))
        if not current_user.is_admin():
            flash("ไม่มีสิทธิ์เข้าถึงหน้าผู้ดูแล", "error")
            return redirect(url_for("store.index"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password) and user.is_admin():
            login_user(user)
            flash("เข้าสู่ระบบแล้ว", "success")
            return redirect(url_for("admin.dashboard"))
        flash("อีเมลหรือรหัสผ่านไม่ถูกต้อง", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ออกจากระบบแล้ว", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    orders_pending = Order.query.filter_by(status="pending").count()
    orders_paid = Order.query.filter_by(status="paid").count()
    total_revenue = db.session.query(db.func.sum(Order.grand_total)).scalar() or 0
    products_active = Product.query.filter_by(status="active").count()
    latest_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        orders_pending=orders_pending,
        orders_paid=orders_paid,
        total_revenue=total_revenue,
        products_active=products_active,
        latest_orders=latest_orders,
    )


@admin_bp.route("/products")
@login_required
def product_list():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/product_list.html", products=products)


@admin_bp.route("/products/create", methods=["GET", "POST"])
@login_required
def product_create():
    if request.method == "POST":
        sku = request.form.get("sku")
        title_th = request.form.get("title_th")
        title_en = request.form.get("title_en")
        price = request.form.get("price", type=float) or 0
        is_unique = bool(request.form.get("is_unique"))
        tail = request.form.get("tail")
        color = request.form.get("color")
        grade = request.form.get("grade")
        sex = request.form.get("sex")
        age = request.form.get("age", type=int)
        health = request.form.get("health")
        lineage_sire = request.form.get("lineage_sire")
        lineage_dam = request.form.get("lineage_dam")
        weight = request.form.get("weight_grams", type=int)
        stock_qty = request.form.get("stock_qty", type=int) or 1

        product = Product(
            sku=sku,
            title_th=title_th,
            title_en=title_en,
            desc_th=request.form.get("desc_th"),
            desc_en=request.form.get("desc_en"),
            category=request.form.get("category", "unique"),
            is_unique=is_unique,
            status="active",
        )
        db.session.add(product)
        db.session.flush()

        variant = Variant(
            product=product,
            price=price,
            stock_qty=1 if is_unique else stock_qty,
            weight_grams=weight,
        )
        variant.attributes = {
            "tail": tail,
            "color": color,
            "grade": grade,
            "sex": sex,
            "age_months": age,
            "health": health,
            "lineage": {"sire": lineage_sire, "dam": lineage_dam},
        }
        db.session.add(variant)

        files = request.files.getlist("media")
        for order, file in enumerate(files):
            if not file or file.filename == "":
                continue
            filename = secure_filename(f"{sku}_{order}_{file.filename}")
            url = save_upload(file, filename)
            media = Media(url=url, kind="image", alt_text=title_en or title_th)
            db.session.add(media)
            db.session.flush()
            db.session.add(ProductMedia(product=product, media=media, sort_order=order))

        db.session.commit()
        flash("สร้างสินค้าเรียบร้อย", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/product_form.html", product=None)



@admin_bp.route("/blog")
@login_required
def blog_list():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("admin/blog_list.html", posts=posts)


@admin_bp.route("/blog/create", methods=["GET", "POST"])
@login_required
def blog_create():
    if request.method == "POST":
        title = request.form.get("title")
        slug_value = request.form.get("slug") or title or ""
        content = request.form.get("content")
        hero_image = request.form.get("hero_image")
        is_published = bool(request.form.get("is_published"))
        if not title or not content:
            flash("กรุณากรอกข้อมูลให้ครบถ้วน", "error")
            return render_template("admin/blog_form.html", post=None)
        base_slug = slugify(slug_value)
        if not base_slug:
            base_slug = f"post-{int(datetime.utcnow().timestamp())}"
        unique_slug = base_slug
        counter = 2
        while BlogPost.query.filter_by(slug=unique_slug).first():
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        post = BlogPost(title=title, slug=unique_slug, content=content, hero_image=hero_image, is_published=is_published)
        if is_published:
            post.publish()
        db.session.add(post)
        db.session.commit()
        flash("สร้างบทความเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.blog_list"))
    return render_template("admin/blog_form.html", post=None)


@admin_bp.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def blog_edit(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    if request.method == "POST":
        title = request.form.get("title")
        slug_value = request.form.get("slug") or title or post.slug
        content = request.form.get("content")
        hero_image = request.form.get("hero_image")
        is_published = bool(request.form.get("is_published"))
        if not title or not content:
            flash("กรุณากรอกข้อมูลให้ครบถ้วน", "error")
            return render_template("admin/blog_form.html", post=post)
        base_slug = slugify(slug_value) or post.slug
        unique_slug = base_slug
        if unique_slug != post.slug and BlogPost.query.filter(BlogPost.slug == unique_slug, BlogPost.id != post.id).first():
            counter = 2
            while BlogPost.query.filter(BlogPost.slug == f"{base_slug}-{counter}", BlogPost.id != post.id).first():
                counter += 1
            unique_slug = f"{base_slug}-{counter}"
        post.title = title
        post.slug = unique_slug
        post.content = content
        post.hero_image = hero_image
        post.is_published = is_published
        if is_published:
            post.publish()
        else:
            post.published_at = None
        db.session.commit()
        flash("อัปเดตบทความแล้ว", "success")
        return redirect(url_for("admin.blog_list"))
    return render_template("admin/blog_form.html", post=post)


@admin_bp.post("/blog/<int:post_id>/delete")
@login_required
def blog_delete(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("ลบบทความแล้ว", "info")
    return redirect(url_for("admin.blog_list"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    tab = request.values.get("tab", request.args.get("tab", "profile"))
    if tab not in SETTINGS_SCHEMA:
        tab = "profile"

    if request.method == "POST":
        chosen_tab = request.form.get("tab", tab) or tab
        if chosen_tab not in SETTINGS_SCHEMA:
            chosen_tab = "profile"
        errors = save_settings(chosen_tab, request.form)
        if errors:
            for message in errors:
                flash(message, "error")
        else:
            flash("บันทึกการตั้งค่าเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.settings", tab=chosen_tab))

    section, values = get_settings_values(tab)
    tabs = [
        {"key": key, "label": meta["label"]}
        for key, meta in SETTINGS_SCHEMA.items()
    ]
    return render_template(
        "admin/settings.html",
        tabs=tabs,
        active_tab=tab,
        section=section,
        values=values,
    )


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id: int):
    product = Product.query.get_or_404(product_id)
    variant = product.primary_variant()
    if request.method == "POST":
        product.title_th = request.form.get("title_th")
        product.title_en = request.form.get("title_en")
        product.status = request.form.get("status", "active")
        product.is_unique = bool(request.form.get("is_unique"))
        if variant:
            variant.price = request.form.get("price", type=float) or variant.price
            variant.weight_grams = request.form.get("weight_grams", type=int) or variant.weight_grams
            attrs = variant.attributes
            attrs.update(
                {
                    "tail": request.form.get("tail"),
                    "color": request.form.get("color"),
                    "grade": request.form.get("grade"),
                    "sex": request.form.get("sex"),
                    "age_months": request.form.get("age", type=int),
                    "health": request.form.get("health"),
                    "lineage": {
                        "sire": request.form.get("lineage_sire"),
                        "dam": request.form.get("lineage_dam"),
                    },
                }
            )
            variant.attributes = attrs
        db.session.commit()
        flash("อัปเดตสินค้าแล้ว", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/product_form.html", product=product, variant=variant)


@admin_bp.post("/orders/<int:order_id>/confirm_payment")
@login_required
def confirm_payment(order_id: int):
    order = Order.query.get_or_404(order_id)
    payment: Payment | None = order.payments[-1] if order.payments else None
    if payment:
        payment.status = "confirmed"
        payment.paid_at = datetime.utcnow()
    else:
        payment = Payment(order=order, method="transfer", amount=order.grand_total, status="confirmed", paid_at=datetime.utcnow())
        db.session.add(payment)
    order.status = "paid"
    db.session.commit()
    flash("ยืนยันการชำระเงินแล้ว", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/orders/<int:order_id>/ship")
@login_required
def ship_order(order_id: int):
    order = Order.query.get_or_404(order_id)
    order.status = "shipped"
    shipment = order.shipment
    if not shipment:
        label_url = "/static/labels/placeholder.pdf"
        shipment = Shipment(
            order=order,
            carrier=request.form.get("carrier", "Kerry Express"),
            tracking_no=request.form.get("tracking_no") or f"KR{datetime.utcnow().strftime('%Y%m%d')}-{order.id:05d}",
            label_url=label_url,
            status="shipped",
            shipped_at=datetime.utcnow(),
        )
        db.session.add(shipment)
    else:
        shipment.status = "shipped"
        shipment.carrier = request.form.get("carrier", shipment.carrier)
        shipment.tracking_no = request.form.get("tracking_no", shipment.tracking_no)
        shipment.shipped_at = datetime.utcnow()
    db.session.commit()
    flash("อัปเดตสถานะการจัดส่งแล้ว", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/orders/<int:order_id>/cancel")
@login_required
def cancel_order(order_id: int):
    order = Order.query.get_or_404(order_id)
    if order.status in {"canceled", "canceled_damaged"}:
        flash("คำสั่งซื้อนี้ถูกยกเลิกแล้ว", "info")
        return redirect(url_for("admin.dashboard"))

    action = request.form.get("action", "restock")
    restock = action == "restock"
    damaged = action == "damaged"

    if not restock and not damaged:
        flash("ไม่สามารถดำเนินการได้", "error")
        return redirect(url_for("admin.dashboard"))

    if restock:
        for item in order.items:
            variant = item.variant
            if not variant:
                continue
            variant.stock_qty = (variant.stock_qty or 0) + item.qty
            product = variant.product
            if product and product.status != "active":
                product.status = "active"
    else:
        for item in order.items:
            variant = item.variant
            if variant and variant.stock_qty < 0:
                variant.stock_qty = 0

    for payment in order.payments:
        payment.status = "canceled"
        payment.paid_at = None

    if order.shipment:
        order.shipment.status = "canceled"
        order.shipment.shipped_at = None
        order.shipment.received_at = None

    order.status = "canceled" if restock else "canceled_damaged"
    db.session.commit()

    if restock:
        flash("ยกเลิกคำสั่งซื้อและคืนสินค้าเข้าสู่สต็อกแล้ว", "success")
    else:
        flash("ยกเลิกคำสั่งซื้อโดยระบุว่าสินค้าเสียหายแล้ว", "warning")

    return redirect(url_for("admin.dashboard"))


