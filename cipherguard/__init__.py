import sys
from datetime import datetime
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
if VENDOR_DIR.is_dir() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from flask import Flask, render_template

from cipherguard.config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)

    from cipherguard import auth, cart, catalog, filters, monitoring
    from cipherguard.views import account, admin, api, storefront
    from cipherguard.views import auth as auth_views

    for blueprint in (storefront.bp, auth_views.bp, account.bp, admin.bp, api.bp):
        app.register_blueprint(blueprint)

    filters.register(app)
    monitoring.register(app)

    @app.context_processor
    def shared_context():
        return {
            "cart_count": cart.count(),
            "current_username": auth.current_username(),
            "is_admin": auth.is_admin(),
            "categories": catalog.CATEGORIES,
            "levels": catalog.LEVELS,
            "sort_options": catalog.SORT_OPTIONS,
            "year": datetime.now().year,
        }

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    with app.app_context():
        auth.seed_demo_accounts()

    return app
