"""Exercise Alembic 0002 upgrade/downgrade on upload_expires_at."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.conftest import ADMIN_URL

BACKEND = Path(__file__).resolve().parents[1]


def _alembic_cfg() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", ADMIN_URL)
    return cfg


def test_0002_downgrade_and_upgrade_roundtrip():
    eng = create_engine(ADMIN_URL)
    cfg = _alembic_cfg()

    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'evidences' AND column_name = 'upload_expires_at'
                """
            )
        ).first()

    command.downgrade(cfg, "20260803_0001")
    with eng.connect() as conn:
        assert (
            conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'evidences' AND column_name = 'upload_expires_at'
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
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'evidences' AND column_name = 'upload_expires_at'
                """
            )
        ).first()
    eng.dispose()
