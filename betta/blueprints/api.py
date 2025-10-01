from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..models import Order, Product, Variant

api_bp = Blueprint("api", __name__)


@api_bp.get("/products")
def api_products():
    products = Product.query.filter_by(status="active").all()
    data = []
    for product in products:
        variant = product.primary_variant()
        if not variant:
            continue
        data.append(
            {
                "sku": product.sku,
                "title_th": product.title_th,
                "title_en": product.title_en,
                "price": variant.price,
                "stock_qty": variant.stock_qty,
                "attributes": variant.attributes,
            }
        )
    return jsonify(data)


@api_bp.get("/products/<string:sku>")
def api_product_detail(sku: str):
    product = Product.query.filter_by(sku=sku).first_or_404()
    variant = product.primary_variant()
    media = [pm.media.url for pm in product.media]
    return jsonify(
        {
            "sku": product.sku,
            "title_th": product.title_th,
            "title_en": product.title_en,
            "description": product.desc_en,
            "price": variant.price if variant else None,
            "stock_qty": variant.stock_qty if variant else 0,
            "attributes": variant.attributes if variant else {},
            "media": media,
        }
    )


@api_bp.get("/orders/<string:order_no>")
def api_order_status(order_no: str):
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    return jsonify(
        {
            "order_no": order.order_no,
            "status": order.status,
            "grand_total": order.grand_total,
            "currency": order.currency,
            "items": [
                {
                    "variant_id": item.variant_id,
                    "qty": item.qty,
                    "unit_price": item.unit_price,
                }
                for item in order.items
            ],
        }
    )


@api_bp.get("/variants/<int:variant_id>")
def api_variant(variant_id: int):
    variant = Variant.query.get_or_404(variant_id)
    return jsonify(
        {
            "id": variant.id,
            "product_id": variant.product_id,
            "price": variant.price,
            "stock_qty": variant.stock_qty,
            "attributes": variant.attributes,
        }
    )
