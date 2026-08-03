"""Alembic 0005 upgrade / downgrade / re-upgrade."""

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


def test_0005_roundtrip():
    eng = create_engine(ADMIN_URL)
    cfg = _cfg()
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert conn.execute(
            text(
                """
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'uq_reports_one_published_per_assessment'
                """
            )
        ).first()

    command.downgrade(cfg, "20260803_0004")
    with eng.connect() as conn:
        assert (
            conn.execute(
                text(
                    """
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'uq_reports_one_published_per_assessment'
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
                WHERE indexname = 'uq_reports_one_published_per_assessment'
                """
            )
        ).first()
    eng.dispose()
