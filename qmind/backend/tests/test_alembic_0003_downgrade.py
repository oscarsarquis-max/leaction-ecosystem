"""Exercise Alembic 0003 upgrade/downgrade/re-upgrade."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.conftest import ADMIN_URL

BACKEND = Path(__file__).resolve().parents[1]


def _cfg() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", ADMIN_URL)
    return cfg


def _has_column(conn, table: str, column: str) -> bool:
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


def test_0003_downgrade_and_upgrade_roundtrip():
    eng = create_engine(ADMIN_URL)
    cfg = _cfg()
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert _has_column(conn, "findings", "rework_of_finding_id")
        assert _has_column(conn, "action_items", "source_finding_withdrawn")

    command.downgrade(cfg, "20260803_0002")
    with eng.connect() as conn:
        assert not _has_column(conn, "findings", "rework_of_finding_id")
        assert not _has_column(conn, "action_items", "source_finding_withdrawn")

    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert _has_column(conn, "findings", "rework_of_finding_id")
        assert _has_column(conn, "action_items", "source_finding_withdrawn")
        # discarded allowed again
        allowed = conn.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conname = 'findings_status_check'
                """
            )
        ).scalar_one()
        assert "discarded" in allowed
    eng.dispose()
