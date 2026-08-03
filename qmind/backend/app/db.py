"""DB engines — admin bootstrap vs qmind_app + RLS org context."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from app.config import get_settings

_admin_engine: Engine | None = None
_app_engine: Engine | None = None


def get_admin_engine() -> Engine:
    global _admin_engine
    if _admin_engine is None:
        _admin_engine = create_engine(
            get_settings().database_url_admin,
            pool_pre_ping=True,
        )
    return _admin_engine


def get_app_engine() -> Engine:
    global _app_engine
    if _app_engine is None:
        _app_engine = create_engine(
            get_settings().database_url_app,
            pool_pre_ping=True,
        )
    return _app_engine


@contextmanager
def admin_connection() -> Generator[Connection, None, None]:
    with get_admin_engine().connect() as conn:
        yield conn


@contextmanager
def tenant_connection(organization_id: UUID) -> Generator[Connection, None, None]:
    """Connection as qmind_app with FORCE RLS scoped to organization_id."""
    with get_app_engine().connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(organization_id)},
        )
        yield conn


def ping_database() -> dict[str, str]:
    with admin_connection() as conn:
        conn.execute(text("SELECT 1"))
        db = conn.execute(text("SELECT current_database()")).scalar_one()
    return {"database": str(db), "status": "ok"}
