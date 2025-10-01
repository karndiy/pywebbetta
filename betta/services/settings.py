from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import current_app

from ..models import Setting, db


@dataclass(frozen=True)
class SettingField:
    key: str
    label: str
    input_type: str = "text"
    config_key: str | None = None
    placeholder: str | None = None
    help_text: str | None = None
    cast: type | None = None
    empty_value: Any | None = None
    default: Any | None = None


SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "profile": {
        "label": "โปรไฟล์ร้าน",
        "description": "ข้อมูลพื้นฐานของร้านที่จะใช้แสดงในหน้าเว็บไซต์และเอกสาร",
        "fields": [
            SettingField(
                key="profile.shop_name",
                label="ชื่อร้าน",
                config_key="SHOP_NAME",
                placeholder="Betta Paradise",
                default="Betta Paradise",
            ),
            SettingField(
                key="profile.shop_email",
                label="อีเมลติดต่อ",
                input_type="email",
                config_key="SHOP_EMAIL",
                placeholder="support@example.com",
                default="support@bettaparadise.test",
            ),
            SettingField(
                key="profile.shop_phone",
                label="เบอร์ติดต่อ",
                config_key="SHOP_PHONE",
                placeholder="+66-000-0000",
                default="+66-000-0000",
            ),
            SettingField(
                key="profile.shop_address",
                label="ที่อยู่",
                input_type="textarea",
                config_key="SHOP_ADDRESS",
                placeholder="Bangkok, Thailand",
                default="Bangkok, Thailand",
            ),
        ],
    },
    "payments": {
        "label": "การชำระเงิน",
        "description": "ตั้งค่า PromptPay และ Stripe สำหรับการชำระเงิน",
        "fields": [
            SettingField(
                key="payments.promptpay_id",
                label="PromptPay ID",
                config_key="PROMPTPAY_ID",
                placeholder="0812345678",
            ),
            SettingField(
                key="payments.promptpay_display",
                label="PromptPay Display Name",
                config_key="PROMPTPAY_DISPLAY_NAME",
                placeholder="Betta Shop",
            ),
            SettingField(
                key="payments.stripe_public",
                label="Stripe Publishable Key",
                config_key="STRIPE_PUBLIC_KEY",
            ),
            SettingField(
                key="payments.stripe_secret",
                label="Stripe Secret Key",
                input_type="password",
                config_key="STRIPE_SECRET_KEY",
                help_text="คีย์ลับจะถูกบันทึกในฐานข้อมูลของระบบ",
            ),
        ],
    },
    "seo": {
        "label": "SEO & Social",
        "description": "ตั้งค่าข้อมูล SEO พื้นฐานและ Open Graph",
        "fields": [
            SettingField(
                key="seo.meta_title",
                label="Default Meta Title",
                config_key="SEO_META_TITLE",
                placeholder="Betta Paradise - Unique Betta Fish",
            ),
            SettingField(
                key="seo.meta_description",
                label="Default Meta Description",
                input_type="textarea",
                config_key="SEO_META_DESCRIPTION",
                placeholder="Show grade betta fish for sale.",
            ),
            SettingField(
                key="seo.og_image",
                label="Open Graph Image URL",
                config_key="SEO_OG_IMAGE",
                placeholder="https://example.com/og-image.jpg",
            ),
        ],
    },
    "operations": {
        "label": "ค่าดำเนินการ",
        "description": "การตั้งค่าสกุลเงินและค่าขนส่งพื้นฐาน",
        "fields": [
            SettingField(
                key="ops.currency",
                label="สกุลเงินหลัก",
                config_key="CURRENCY",
                placeholder="THB",
                default="THB",
            ),
            SettingField(
                key="ops.shipping_domestic",
                label="ค่าส่งภายในประเทศ (บาท)",
                input_type="number",
                config_key="DEFAULT_SHIPPING_DOMESTIC",
                cast=float,
                empty_value=150.0,
                default=150.0,
            ),
            SettingField(
                key="ops.shipping_international",
                label="ค่าส่งต่างประเทศ (บาท)",
                input_type="number",
                config_key="DEFAULT_SHIPPING_INTERNATIONAL",
                cast=float,
                empty_value=650.0,
                default=650.0,
            ),
        ],
    },
}

SETTINGS_CONFIG_MAP = {
    field.key: field.config_key
    for section in SETTINGS_SCHEMA.values()
    for field in section["fields"]
    if field.config_key
}


def _get_default(field: SettingField) -> Any:
    app_value = current_app.config.get(field.config_key, field.default) if field.config_key else field.default
    return app_value


def get_settings_values(tab: str) -> tuple[dict[str, Any], dict[str, str]]:
    section = SETTINGS_SCHEMA.get(tab) or SETTINGS_SCHEMA["profile"]
    keys = [field.key for field in section["fields"]]
    records = Setting.query.filter(Setting.key.in_(keys)).all()
    record_map = {record.key: record.value for record in records}
    values: dict[str, str] = {}
    for field in section["fields"]:
        raw_value: Any = record_map.get(field.key)
        if raw_value is None:
            raw_value = _get_default(field)
        if field.cast is float and isinstance(raw_value, (int, float)):
            raw_value = f"{raw_value:.2f}"
        values[field.key] = str(raw_value) if raw_value is not None else ""
    return section, values


def save_settings(tab: str, form_data: dict[str, Any]) -> list[str]:
    section = SETTINGS_SCHEMA.get(tab)
    if not section:
        return ["ไม่พบหมวดการตั้งค่าที่เลือก"]

    errors: list[str] = []
    updates: list[tuple[SettingField, str, Any]] = []

    for field in section["fields"]:
        raw_value = form_data.get(field.key, "")
        if isinstance(raw_value, str):
            raw_value = raw_value.strip()
        value_to_store: str = raw_value or ""
        config_value: Any = raw_value

        if field.cast is float:
            if raw_value == "":
                config_value = field.empty_value if field.empty_value is not None else 0.0
                value_to_store = f"{float(config_value):.2f}"
            else:
                try:
                    casted = float(raw_value)
                except (TypeError, ValueError):
                    errors.append(f"{field.label} ต้องเป็นตัวเลข")
                    continue
                config_value = casted
                value_to_store = f"{casted:.2f}"
        elif raw_value == "" and field.default is not None:
            config_value = field.default
            value_to_store = str(field.default)

        updates.append((field, value_to_store, config_value))

    if errors:
        return errors

    for field, stored_value, config_value in updates:
        setting = Setting.query.get(field.key)
        if setting:
            setting.value = stored_value
        else:
            db.session.add(Setting(key=field.key, value=stored_value))
        if field.config_key:
            current_app.config[field.config_key] = config_value

    db.session.commit()
    return []


def sync_settings_to_app_config(app) -> None:
    keys = list(SETTINGS_CONFIG_MAP.keys())
    if not keys:
        return
    records = Setting.query.filter(Setting.key.in_(keys)).all()
    for record in records:
        target = SETTINGS_CONFIG_MAP.get(record.key)
        if not target:
            continue
        value: Any = record.value
        field = next((f for s in SETTINGS_SCHEMA.values() for f in s["fields"] if f.key == record.key), None)
        if field and field.cast is float:
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
        app.config[target] = value
