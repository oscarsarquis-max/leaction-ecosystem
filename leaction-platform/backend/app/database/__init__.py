"""Persistência isolada do plugin Marketplace."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

db = None
DB_AVAILABLE = False

try:
    from flask_sqlalchemy import SQLAlchemy

    db = SQLAlchemy()
    DB_AVAILABLE = True
except ImportError:
    logger.warning(
        "flask-sqlalchemy não instalado — curadoria usará seed em memória. "
        "Execute: pip install -r requirements.txt"
    )


def init_db(app) -> bool:
    """Inicializa SQLAlchemy. Retorna False se DB indisponível."""
    if not DB_AVAILABLE or db is None:
        app.config["MARKETPLACE_DB_ENABLED"] = False
        return False

    database_url = (
        os.getenv("MARKETPLACE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()
    if not database_url:
        logger.warning("DATABASE_URL ausente — curadoria em modo seed.")
        app.config["MARKETPLACE_DB_ENABLED"] = False
        return False

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MARKETPLACE_DB_ENABLED"] = True
    db.init_app(app)
    return True
