"""CURSOR-027-C3-H3 — Alembic env that never puts credentials into ConfigParser.

Uses config.attributes["connection"] when provided by the migration runner.
Offline mode fails closed with a sanitized message.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from app.db import Base
from app.modules.ai_orchestration import models as _ai_models  # noqa: F401
from app.modules.compliance import models as _compliance_models  # noqa: F401
from app.modules.formula_lab import models as _formula_models  # noqa: F401
from app.modules.identity_organization import models as _identity_models  # noqa: F401
from app.modules.ingredient_catalog import models as _ingredient_models  # noqa: F401
from app.modules.knowledge_grounding import models as _knowledge_models  # noqa: F401
from app.modules.labeling_compliance import models as _labeling_models  # noqa: F401
from app.modules.costing_pricing import models as _costing_models  # noqa: F401
from app.modules.reporting_analytics import models as _reporting_models  # noqa: F401
from app.modules.inventory_procurement import models as _inventory_models  # noqa: F401
from app.modules.nutrition_calculation import models as _nutrition_models  # noqa: F401
from app.modules.production_execution import models as _execution_models  # noqa: F401
from app.modules.production_planning import models as _production_models  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

config = context.config
if config.config_file_name is not None:
    # Logging only — never inject sqlalchemy.url into ConfigParser.
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    raise RuntimeError(
        "alembic offline mode is disabled for Panne migrations "
        "(credentials must not be rendered into ConfigParser/URL strings)"
    )


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    shared = config.attributes.get("connection")
    if shared is not None:
        do_run_migrations(shared)
        return

    engine = config.attributes.get("async_engine")
    if engine is None:
        raise RuntimeError(
            "no database connection provided; set config.attributes['connection'] "
            "or config.attributes['async_engine'] (never ConfigParser sqlalchemy.url)"
        )
    if not isinstance(engine, AsyncEngine):
        raise RuntimeError("async_engine attribute has unexpected type")

    async def _run() -> None:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await engine.dispose()

    asyncio.run(_run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
