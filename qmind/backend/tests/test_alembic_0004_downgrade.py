"""Alembic 0004 upgrade / downgrade / re-upgrade."""

from __future__ import annotations

from tests.alembic_support import has_column, has_index, roundtrip

INDEX = "uq_maturity_one_approved_per_assessment"


def _at_head(conn):
    assert has_index(conn, INDEX)
    assert has_column(conn, "assessments", "close_waiver_reason")


def _at_down(conn):
    assert not has_index(conn, INDEX)


def test_0004_roundtrip():
    roundtrip("20260803_0003", at_head=_at_head, at_down=_at_down)
