import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INSTANCE_PATH = BASE_DIR / "instance"
DEFAULT_DB_PATH = DEFAULT_INSTANCE_PATH / "shop.db"
DEFAULT_MEDIA_ROOT = BASE_DIR / "betta" / "static" / "uploads"
DEFAULT_QR_ROOT = BASE_DIR / "betta" / "static" / "qr"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PROMPTPAY_ID = os.getenv("PROMPTPAY_ID", "")
    PROMPTPAY_DISPLAY_NAME = os.getenv("PROMPTPAY_DISPLAY_NAME", "Betta Shop")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    CURRENCY = os.getenv("CURRENCY", "THB")
    SHOP_NAME = os.getenv("SHOP_NAME", "Betta Paradise")
    SHOP_EMAIL = os.getenv("SHOP_EMAIL", "support@bettaparadise.test")
    SHOP_PHONE = os.getenv("SHOP_PHONE", "+66-000-0000")
    SHOP_ADDRESS = os.getenv("SHOP_ADDRESS", "Bangkok, Thailand")
    SEO_META_TITLE = os.getenv("SEO_META_TITLE", "Betta Paradise - Unique Betta Fish")
    SEO_META_DESCRIPTION = os.getenv("SEO_META_DESCRIPTION", "Show grade betta fish for sale.")
    SEO_OG_IMAGE = os.getenv("SEO_OG_IMAGE", "")

    DEFAULT_SHIPPING_DOMESTIC = float(os.getenv("DEFAULT_SHIPPING_DOMESTIC", 150))
    DEFAULT_SHIPPING_INTERNATIONAL = float(os.getenv("DEFAULT_SHIPPING_INTERNATIONAL", 650))

    MEDIA_UPLOAD_FOLDER = os.getenv("MEDIA_UPLOAD_FOLDER", str(DEFAULT_MEDIA_ROOT))
    QR_OUTPUT_FOLDER = os.getenv("QR_OUTPUT_FOLDER", str(DEFAULT_QR_ROOT))

    BABEL_DEFAULT_LOCALE = os.getenv("BABEL_DEFAULT_LOCALE", "th")
    BABEL_TRANSLATION_DIRECTORIES = os.getenv("BABEL_TRANSLATION_DIRECTORIES", "betta/translations")
    LANGUAGES = ["th", "en"]

    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    @staticmethod
    def init_app(app):
        DEFAULT_INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
        upload_path = Path(app.config["MEDIA_UPLOAD_FOLDER"])
        upload_path.mkdir(parents=True, exist_ok=True)
        qr_path = Path(app.config["QR_OUTPUT_FOLDER"])
        qr_path.mkdir(parents=True, exist_ok=True)
