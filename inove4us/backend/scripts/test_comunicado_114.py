#!/usr/bin/env python3
"""Prompt 114 — fuso America/Sao_Paulo + vigência do comunicado. Sem I/O de prod."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from school_integracao_routes import (  # noqa: E402
    TZ_ESCOLA,
    _comunicado_vigente,
    _to_agenda_naive,
)


def test_naive_utc_strip_becomes_brazil_wall() -> None:
    # Legado 113: 2026-09-09T00:22:24+00:00 virava dia 09 na agenda.
    utc = datetime(2026, 9, 9, 0, 22, 24, tzinfo=timezone.utc)
    naive = _to_agenda_naive(utc)
    assert naive.tzinfo is None
    assert naive.date().isoformat() == "2026-09-08"
    assert naive.hour == 21
    assert naive.minute == 22


def test_brazil_offset_keeps_same_day() -> None:
    br = datetime(2026, 9, 8, 21, 22, 0, tzinfo=TZ_ESCOLA)
    naive = _to_agenda_naive(br)
    assert naive.date().isoformat() == "2026-09-08"
    assert naive.hour == 21


def test_vigencia_expired() -> None:
    past = datetime(2026, 1, 10, 11, 0, tzinfo=timezone.utc)
    assert _comunicado_vigente("ativo", past) is False
    future = datetime(2099, 1, 10, 11, 0, tzinfo=timezone.utc)
    assert _comunicado_vigente("ativo", future) is True
    assert _comunicado_vigente("ativo", None) is True
    assert _comunicado_vigente("cancelado", future) is False


def test_tz_escola_is_sao_paulo() -> None:
    assert TZ_ESCOLA == ZoneInfo("America/Sao_Paulo")


def main() -> int:
    test_naive_utc_strip_becomes_brazil_wall()
    test_brazil_offset_keeps_same_day()
    test_vigencia_expired()
    test_tz_escola_is_sao_paulo()
    print("ok 114 unit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
