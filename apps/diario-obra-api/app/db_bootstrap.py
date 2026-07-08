"""Garante que a base PostgreSQL dedicada exista antes do SQLAlchemy conectar."""

from __future__ import annotations

import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

logger = logging.getLogger(__name__)

_SAFE_DB_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


def ensure_database(database_url: str) -> None:
    url = make_url(database_url)
    db_name = url.database
    if not db_name:
        raise ValueError("DATABASE_URL sem nome de base de dados.")

    if not _SAFE_DB_NAME.match(db_name):
        raise ValueError(f"Nome de base inválido: {db_name}")

    admin_url = url.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    quoted_name = db_name.replace('"', '""')
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{quoted_name}"'))
            logger.info("Base de dados criada: %s", db_name)
