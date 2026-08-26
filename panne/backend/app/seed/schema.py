"""Criação isolada e Alembic 0001→0020. Só _demo/_smoke."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.seed.target import SeedTargetError, assert_seed_target, describe_target, parse_database_name, sync_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def apply_alembic(url: str) -> None:
    async_url = url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    os.environ["PANNE_DATABASE_URL"] = async_url
    get_settings.cache_clear()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", async_url)
    command.upgrade(config, "head")


def current_alembic(url: str) -> str | None:
    engine = create_engine(sync_url(url), future=True)
    with engine.connect() as connection:
        exists = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
        if not exists:
            return None
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def recreate_isolated_database(url: str, env: str) -> dict[str, str]:
    target = describe_target(url, env)
    name = target["database"]
    print(f"Alvo resolvido: {name} em {target['host']}:{target['port']} (env={env})")
    admin = sync_url(url)
    parsed_admin = admin.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(parsed_admin, isolation_level="AUTOCOMMIT", future=True)
    quoted = name.replace('"', "")
    with engine.connect() as connection:
        connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": name},
        )
        connection.execute(text(f'DROP DATABASE IF EXISTS "{quoted}"'))
        connection.execute(text(f'CREATE DATABASE "{quoted}"'))
    return target


def refuse_if_logical_panne(url: str) -> None:
    if parse_database_name(url) == "panne":
        raise SeedTargetError("banco lógico panne recusado")
    assert_seed_target(url, "local")
