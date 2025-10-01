from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from flask import current_app


@dataclass
class ShippingQuote:
    method: str
    fee: float
    eta_days: int
    international: bool = False


DOMESTIC_CARRIERS = {
    "kerry": ShippingQuote(method="Kerry Express", fee=0, eta_days=2),
    "flash": ShippingQuote(method="Flash Express", fee=0, eta_days=3),
    "ems": ShippingQuote(method="Thailand Post EMS", fee=0, eta_days=2),
}


INTERNATIONAL_BASE = {
    "dhl": ShippingQuote(method="DHL Express", fee=0, eta_days=7, international=True),
    "ups": ShippingQuote(method="UPS Worldwide", fee=0, eta_days=6, international=True),
}


def calculate_domestic(weight_grams: int | None = None) -> ShippingQuote:
    base_fee = current_app.config.get("DEFAULT_SHIPPING_DOMESTIC", 150)
    fee = base_fee
    if weight_grams and weight_grams > 500:
        fee += (weight_grams - 500) * 0.5
    quote = DOMESTIC_CARRIERS["kerry"]
    return ShippingQuote(method=quote.method, fee=round(fee, 2), eta_days=quote.eta_days)


def calculate_international(weight_grams: int | None = None) -> ShippingQuote:
    base_fee = current_app.config.get("DEFAULT_SHIPPING_INTERNATIONAL", 650)
    fee = base_fee
    if weight_grams and weight_grams > 500:
        fee += (weight_grams - 500) * 1.2
    quote = INTERNATIONAL_BASE["dhl"]
    return ShippingQuote(method=quote.method, fee=round(fee, 2), eta_days=quote.eta_days, international=True)


def generate_shipping_label(order_no: str, carrier: str, address: dict[str, str]) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"label_{order_no}_{timestamp}.pdf"
    # In a full implementation, generate PDF label. For now, return placeholder path.
    return f"/static/labels/{filename}"
