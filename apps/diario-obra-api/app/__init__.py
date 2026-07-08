from flask import Flask
from flask_cors import CORS

from app.api import health_bp, integration_bp, rdo_bp
from app.config import Config
from app.db_bootstrap import ensure_database
from app.db_migrate import ensure_rdo_schema
from app.extensions import db

# Importa modelos para o metadata do SQLAlchemy registrar as tabelas.
from app.models import (  # noqa: F401
    DailyLog,
    EquipmentStatus,
    ExecutedService,
    Occurrence,
    ProjectDirectives,
    ProjectSite,
    Workforce,
)


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    ensure_database(app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    app.register_blueprint(health_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(rdo_bp)

    with app.app_context():
        db.create_all()
        ensure_rdo_schema()

    return app
