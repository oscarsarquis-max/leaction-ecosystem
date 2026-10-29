from collections.abc import AsyncIterator, Iterator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings
from app.db_urls import RuntimeUrlError, configured_runtime_url


class Base(DeclarativeBase):
    """Metadados SQLAlchemy. Modelos de domínio entram pelos módulos."""


def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

try:
    _runtime_url = configured_runtime_url(_settings.database_url, _settings.runtime_database_url)
except RuntimeUrlError:
    _runtime_url = _settings.database_url if _settings.env == "demo" else None
if _runtime_url is None and _settings.env == "demo":
    _runtime_url = _settings.database_url

runtime_engine = (
    create_engine(_sync_url(_runtime_url), echo=False, pool_pre_ping=True, pool_size=5)
    if _runtime_url is not None
    else None
)
RuntimeSessionLocal = (
    sessionmaker(bind=runtime_engine, expire_on_commit=False, future=True)
    if runtime_engine is not None
    else None
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Sessão administrativa. Não é fallback de runtime e não serve a /me."""
    async with SessionLocal() as session:
        yield session


def get_runtime_session() -> Iterator[Session]:
    if RuntimeSessionLocal is None:
        raise HTTPException(status_code=503, detail="indisponivel")
    session = RuntimeSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
