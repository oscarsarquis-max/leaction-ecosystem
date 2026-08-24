"""Alembic 0005 upgrade / downgrade / re-upgrade."""

from __future__ import annotations

from tests.alembic_support import has_index, roundtrip

INDEX = "uq_reports_one_published_per_assessment"


def _at_head(conn):
    assert has_index(conn, INDEX)


def _at_down(conn):
    assert not has_index(conn, INDEX)


def test_0005_roundtrip():
    roundtrip("20260803_0004", at_head=_at_head, at_down=_at_down)
