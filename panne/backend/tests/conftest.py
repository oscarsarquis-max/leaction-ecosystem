import os
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest
from app.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def pytest_configure() -> None:
    get_settings.cache_clear()


def _raw_url() -> str:
    raw = os.environ.get("PANNE_DATABASE_URL") or get_settings().database_url
    if "mysql" in raw.lower():
        raise RuntimeError("alvo mysql proibido")
    return raw


def postgres_url() -> str:
    raw = _raw_url()
    if "postgresql+asyncpg://" in raw:
        raw = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    parsed = urlparse(raw)
    if parsed.scheme.split("+")[0] != "postgresql":
        raise RuntimeError("mecanismo invalido")
    if parsed.path.lstrip("/") != "panne":
        raise RuntimeError("banco logico invalido")
    if get_settings().env not in {"local", "test"}:
        raise RuntimeError("ambiente desconhecido")
    return raw


@pytest.fixture(scope="session")
def engine() -> Engine:
    return create_engine(postgres_url(), future=True)


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, future=True)()
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
