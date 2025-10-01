from __future__ import annotations

import io
from dataclasses import dataclass

import qrcode
import stripe

from flask import current_app


@dataclass
class PromptPayPayload:
    promptpay_id: str
    amount: float
    merchant_name: str

    def encode(self) -> str:
        payload = (
            "000201010211"  # Header + static QR
            "29370016A000000677010111"  # PromptPay AID
            f"0113{self.promptpay_id:>013}"  # PromptPay ID (phone)
            "5802TH"  # Country Thailand
            f"5303764"  # Currency code THB (764)
            f"5406{_to_promptpay_amount(self.amount)}"  # Amount with 2 decimals
        )
        crc = _crc16(payload + "6304")
        return payload + "6304" + crc.upper()


def _to_promptpay_amount(amount: float) -> str:
    #value = int(round(amount * 100))
    value = int(round(amount))
    return f"{value:06d}"


def _crc16(data: str) -> str:
    crc = 0xFFFF
    poly = 0x1021
    for char in data:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04x}"


def build_promptpay_payload(amount: float) -> str:
    promptpay_id = current_app.config.get("PROMPTPAY_ID", "")
    display_name = current_app.config.get("PROMPTPAY_DISPLAY_NAME", "Betta Shop")
    payload = PromptPayPayload(promptpay_id=promptpay_id, amount=amount, merchant_name=display_name)
    return payload.encode()


def generate_promptpay_qr(amount: float) -> bytes:
    payload_text = build_promptpay_payload(amount)
    img = qrcode.make(payload_text)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def init_stripe():
    secret_key = current_app.config.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("Stripe secret key not configured")
    stripe.api_key = secret_key


def _to_stripe_amount(amount: float) -> int:
    return int(round(amount * 100))


def create_stripe_payment_intent(amount: float, currency: str, metadata: dict[str, str] | None = None):
    init_stripe()
    intent = stripe.PaymentIntent.create(
        amount=_to_stripe_amount(amount),
        currency=currency.lower(),
        metadata=metadata or {},
        automatic_payment_methods={"enabled": True},
    )
    return intent


def retrieve_stripe_payment_intent(intent_id: str):
    init_stripe()
    return stripe.PaymentIntent.retrieve(intent_id)
