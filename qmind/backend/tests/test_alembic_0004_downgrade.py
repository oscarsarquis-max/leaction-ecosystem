"""Alembic 0004 upgrade / downgrade / re-upgrade."""

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


def test_0004_roundtrip():
    eng = create_engine(ADMIN_URL)
    cfg = _cfg()
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert conn.execute(
            text(
                """
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'uq_maturity_one_approved_per_assessment'
                """
            )
        ).first()
        assert conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'assessments' AND column_name = 'close_waiver_reason'
                """
            )
        ).first()

    command.downgrade(cfg, "20260803_0003")
    with eng.connect() as conn:
        assert (
            conn.execute(
                text(
                    """
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'uq_maturity_one_approved_per_assessment'
                    """
                )
            ).first()
            is None
        )

    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert conn.execute(
            text(
                """
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'uq_maturity_one_approved_per_assessment'
                """
            )
        ).first()
    eng.dispose()
