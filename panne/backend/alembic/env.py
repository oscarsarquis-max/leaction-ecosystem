import asyncio
from logging.config import fileConfig

from alembic import context
from app.config import get_settings
from app.db import Base
from app.modules.ai_orchestration import models as _ai_models  # noqa: F401
from app.modules.compliance import models as _compliance_models  # noqa: F401
from app.modules.formula_lab import models as _formula_models  # noqa: F401
from app.modules.identity_organization import models as _identity_models  # noqa: F401
from app.modules.ingredient_catalog import models as _ingredient_models  # noqa: F401
from app.modules.knowledge_grounding import models as _knowledge_models  # noqa: F401
from app.modules.labeling_compliance import models as _labeling_models  # noqa: F401
from app.modules.nutrition_calculation import models as _nutrition_models  # noqa: F401
from app.modules.production_execution import models as _execution_models  # noqa: F401
from app.modules.production_planning import models as _production_models  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
