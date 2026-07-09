"""Plugin Marketplace — micro-app Flask isolado do núcleo ActionHub/Gateway."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, request

from app.api.curation_routes import curation_bp
from app.api.ml_auth_routes import ml_auth_bp
from app.api.marketplace_routes import marketplace_bp
from app.database import init_db
from app.database.seed import seed_catalog_products_if_empty, seed_curation_if_empty
from app.env_loader import load_marketplace_env

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    load_marketplace_env()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    app = Flask(__name__)
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "1") == "1"

    if init_db(app):
        from app.database import db
        from app.database.models import MarketplaceCuration, MarketplaceProduct  # noqa: F401

        with app.app_context():
            try:
                db.create_all()
                seed_curation_if_empty()
                seed_catalog_products_if_empty()
            except Exception:
                logger.exception(
                    "Banco indisponível — vitrine/OAuth ML seguem em modo degradado"
                )
                app.config["MARKETPLACE_DB_ENABLED"] = False

    app.register_blueprint(marketplace_bp, url_prefix="/api/marketplace")
    app.register_blueprint(curation_bp, url_prefix="/api/marketplace")
    app.register_blueprint(ml_auth_bp, url_prefix="/api/marketplace")
    _enable_dev_cors(app)

    return app


def _enable_dev_cors(app: Flask) -> None:
    """CORS apenas em dev — widget ActionHub chama este serviço diretamente."""

    @app.after_request
    def add_cors_headers(response):
        if not app.debug and os.getenv("MARKETPLACE_CORS", "").lower() not in ("1", "true", "yes"):
            return response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, PUT, OPTIONS"
        return response

    @app.route("/api/marketplace/<path:_path>", methods=["OPTIONS"])
    def marketplace_preflight(_path: str):
        return "", 204
