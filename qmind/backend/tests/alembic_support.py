"""Shared helpers for the Alembic round-trip tests.

These tests walk the migration history backwards and forwards again. That is
only safe on a database nobody is keeping data in: from ISOI-008 onwards some
migrations deliberately refuse to downgrade when audit history exists, because
throwing away measurement records and evidence links silently would be worse
than failing. On the shared local database (`qmind_dev`) that history is almost
always present, so the round-trips are skipped there and the refusal itself is
asserted by `test_alembic_0024_downgrade_guard`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from tests.conftest import ADMIN_URL

BACKEND = Path(__file__).resolve().parents[1]

__all__ = [
    "ADMIN_URL",
    "GUARDED_TABLES",
    "alembic_cfg",
    "alembic_head",
    "guarded_history_rows",
    "has_column",
    "has_index",
    "require_reversible_database",
    "roundtrip",
]

# Tables whose rows a downgrade would have to destroy. Keep in sync with the
# guard in the ISOI-008 migration.
GUARDED_TABLES = (
    "measurement_records",
    "outcome_observation_measurements",
    "indicator_definitions",
    "action_measurement_plans",
)


def alembic_cfg() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", ADMIN_URL)
    # alembic/env.py prefers DATABASE_URL; pin to QMind admin so a shell
    # DATABASE_URL from another ecosystem (e.g. Hub) cannot hijack migrations.
    os.environ["DATABASE_URL"] = ADMIN_URL
    os.environ["QMIND_DB_ADMIN_URL"] = ADMIN_URL
    os.environ["DATABASE_URL_ADMIN"] = ADMIN_URL
    return cfg


def alembic_head() -> str:
    """The head revision as declared by the migration scripts on disk."""
    return ScriptDirectory.from_config(alembic_cfg()).get_current_head()


def guarded_history_rows() -> int:
    """How many rows the guarded (append-only) tables currently hold."""
    eng = create_engine(ADMIN_URL)
    try:
        with eng.connect() as conn:
            total = 0
            for table in GUARDED_TABLES:
                exists = conn.execute(
                    text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}
                ).scalar()
                if exists is None:
                    continue
                total += (
                    conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() or 0
                )
            return total
    finally:
        eng.dispose()


def require_reversible_database() -> None:
    """Skip a round-trip test when the database holds protected history."""
    rows = guarded_history_rows()
    if rows:
        pytest.skip(
            f"shared database holds {rows} rows of ISOI-008 audit history; "
            "migration round-trips need a disposable database"
        )


def roundtrip(
    down_to: str,
    *,
    at_head,
    at_down,
) -> None:
    """upgrade → assert → downgrade → assert → upgrade → assert.

    `at_head` and `at_down` receive an open connection and assert whatever the
    revision under test is supposed to have added or removed.
    """
    require_reversible_database()
    cfg = alembic_cfg()
    eng = create_engine(ADMIN_URL)
    try:
        command.upgrade(cfg, "head")
        with eng.connect() as conn:
            at_head(conn)

        command.downgrade(cfg, down_to)
        with eng.connect() as conn:
            at_down(conn)

        command.upgrade(cfg, "head")
        with eng.connect() as conn:
            at_head(conn)
    finally:
        eng.dispose()


def has_column(conn, table: str, column: str) -> bool:
    return (
        conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c
                """
            ),
            {"t": table, "c": column},
        ).first()
        is not None
    )


def has_index(conn, name: str) -> bool:
    return (
        conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = :n"), {"n": name}
        ).first()
        is not None
    )
