from typing import Literal

from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.config import get_settings


class ReadyResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["panne"] = "panne"


def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


_ping_engine = create_engine(
    _sync_url(get_settings().database_url),
    echo=False,
    pool_pre_ping=True,
    pool_size=1,
)


def assert_database_ready() -> None:
    with _ping_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
