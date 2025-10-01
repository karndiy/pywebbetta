from pathlib import Path

from flask import Flask
from flask_babel import Babel
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager

from .config import Config
from .models import User, db, init_db, register_cli_commands
from .services.settings import sync_settings_to_app_config

babel = Babel()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour", "20/minute"])


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    cfg = config_object or Config()
    app.config.from_object(cfg)

    if hasattr(cfg, "init_app"):
        cfg.init_app(app)

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    babel.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        init_db()
        register_cli_commands(app)
        sync_settings_to_app_config(app)

    from .blueprints.store import store_bp
    from .blueprints.admin import admin_bp
    from .blueprints.api import api_bp

    app.register_blueprint(store_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    login_manager.login_view = "admin.login"

    @app.context_processor
    def inject_globals():
        return {
            "currency": app.config.get("CURRENCY", "THB"),
            "promptpay_id": app.config.get("PROMPTPAY_ID", ""),
        }

    return app

