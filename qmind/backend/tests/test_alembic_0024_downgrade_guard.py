"""ISOI-008 refuses to be downgraded over live audit history.

Measurement records and evidence links are append-only by design: the app role
cannot delete them, and a migration must not do quietly what the API forbids.
So the downgrade raises instead of dropping the tables, and the operator has to
archive the history deliberately first.
"""

from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from tests.alembic_support import (
    ADMIN_URL,
    alembic_cfg,
    alembic_head,
    guarded_history_rows,
)

PREVIOUS = "20260824_0023"


def _current_revision() -> str:
    eng = create_engine(ADMIN_URL)
    try:
        with eng.connect() as conn:
            return conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        eng.dispose()


def test_downgrade_refuses_while_history_exists():
    if not guarded_history_rows():
        pytest.skip("no ISOI-008 history in this database; nothing to protect")

    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    # ISOI-009 must be empty before Alembic can even reach the ISOI-008 guard.
    ei_backup = "_iso008_guard_ei_backup"
    eng = create_engine(ADMIN_URL)
    try:
        with eng.begin() as conn:
            exists = conn.execute(
                text(
                    "SELECT to_regclass('public.improvement_case_execution_intelligence_runs')"
                )
            ).scalar()
            if exists:
                conn.execute(text(f"DROP TABLE IF EXISTS {ei_backup}"))
                conn.execute(
                    text(
                        f"CREATE TABLE {ei_backup} AS "
                        "TABLE improvement_case_execution_intelligence_runs"
                    )
                )
                conn.execute(
                    text("DELETE FROM improvement_case_execution_intelligence_runs")
                )
    finally:
        eng.dispose()

    try:
        with pytest.raises(DatabaseError) as raised:
            command.downgrade(cfg, PREVIOUS)

        message = str(raised.value)
        assert "ISOI-008 downgrade refused" in message
        assert "measurement records" in message
        # Refusing has to leave the database exactly where it was.
        assert _current_revision() == alembic_head()
    finally:
        command.upgrade(cfg, "head")
        eng = create_engine(ADMIN_URL)
        try:
            with eng.begin() as conn:
                backup = conn.execute(
                    text("SELECT to_regclass(:name)"), {"name": ei_backup}
                ).scalar()
                if backup:
                    conn.execute(
                        text(
                            """
                            INSERT INTO improvement_case_execution_intelligence_runs
                            SELECT * FROM _iso008_guard_ei_backup
                            ON CONFLICT (id) DO NOTHING
                            """
                        )
                    )
                    conn.execute(text(f"DROP TABLE IF EXISTS {ei_backup}"))
        finally:
            eng.dispose()