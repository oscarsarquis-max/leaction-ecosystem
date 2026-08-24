"""Exercise Alembic 0003 upgrade/downgrade/re-upgrade."""

from __future__ import annotations

from sqlalchemy import text

from tests.alembic_support import has_column, roundtrip


def _at_head(conn):
    assert has_column(conn, "findings", "rework_of_finding_id")
    assert has_column(conn, "action_items", "source_finding_withdrawn")
    # discarded is allowed again once the revision is applied
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


def _at_down(conn):
    assert not has_column(conn, "findings", "rework_of_finding_id")
    assert not has_column(conn, "action_items", "source_finding_withdrawn")


def test_0003_downgrade_and_upgrade_roundtrip():
    roundtrip("20260803_0002", at_head=_at_head, at_down=_at_down)
