"""Exercise Alembic 0002 upgrade/downgrade on upload_expires_at."""

from __future__ import annotations

from tests.alembic_support import has_column, roundtrip


def _at_head(conn):
    assert has_column(conn, "evidences", "upload_expires_at")


def _at_down(conn):
    assert not has_column(conn, "evidences", "upload_expires_at")


def test_0002_downgrade_and_upgrade_roundtrip():
    roundtrip("20260803_0001", at_head=_at_head, at_down=_at_down)
