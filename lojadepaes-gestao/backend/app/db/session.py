from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None
_loja_engine: Engine | None = None
_loja_factory: sessionmaker[Session] | None = None


def reset_engines() -> None:
    global _engine, _factory, _loja_engine, _loja_factory
    for engine in (_engine, _loja_engine):
        if engine is not None:
            engine.dispose()
    _engine = _factory = _loja_engine = _loja_factory = None


def get_engine() -> Engine:
    """Engine do banco `gestao` (leitura e escrita)."""
    global _engine, _factory
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=2,
            connect_args={"connect_timeout": max(1, settings.db_connect_timeout_seconds)},
        )
        _factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_loja_engine() -> Engine:
    """Engine do banco da Loja. Papel gestao_reader: só SELECT, transação somente leitura."""
    global _loja_engine, _loja_factory
    if _loja_engine is None:
        settings = get_settings()
        _loja_engine = create_engine(
            settings.loja_database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=1,
            connect_args={"connect_timeout": max(1, settings.db_connect_timeout_seconds)},
            execution_options={"postgresql_readonly": True},
        )
        _loja_factory = sessionmaker(bind=_loja_engine, expire_on_commit=False, future=True)
    return _loja_engine


def get_db() -> Iterator[Session]:
    get_engine()
    assert _factory is not None
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_loja_db() -> Iterator[Session]:
    get_loja_engine()
    assert _loja_factory is not None
    session = _loja_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
