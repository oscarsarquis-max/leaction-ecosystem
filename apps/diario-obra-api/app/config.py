import os
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent


def _build_default_database_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5433")
    user = quote_plus(os.getenv("DB_USER", "admin"))
    password = quote_plus(os.getenv("DB_PASSWORD", "password123"))
    name = os.getenv("DB_NAME", "diario-obra")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-diario-obra-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", _build_default_database_url())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:4000,http://localhost:5010,http://localhost:6173",
        ).split(",")
        if origin.strip()
    ]
    DEBUG = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
