import os
from collections.abc import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Evita UnicodeDecodeError do libpq em locales Windows (ex.: pt-BR).
os.environ.setdefault("PGCLIENTENCODING", "UTF8")


def _build_database_url() -> str:
    """Prod: DATABASE_URL ou DB_*; local: fallback docker :5435."""
    explicit = (os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        return explicit

    host = (os.getenv("DB_HOST") or "").strip()
    if host:
        port = (os.getenv("DB_PORT") or "5432").strip()
        name = (os.getenv("DB_NAME") or "phanton").strip()
        user = (os.getenv("DB_USER") or "postgres").strip()
        password = os.getenv("DB_PASSWORD") or ""
        sslmode = (os.getenv("DB_SSLMODE") or "").strip()
        user_q = quote_plus(user)
        pass_q = quote_plus(password)
        url = f"postgresql+psycopg2://{user_q}:{pass_q}@{host}:{port}/{name}"
        if sslmode:
            url = f"{url}?sslmode={sslmode}"
        return url

    return "postgresql+psycopg2://postgres:password@127.0.0.1:5435/orquestrador"


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"client_encoding": "utf8"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
