#!/usr/bin/env python3
"""Prompt 114 — datetime-local naive vira America/Sao_Paulo. Sem I/O de prod."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from secretaria_routes import TZ_ESCOLA, _parse_dt_local  # noqa: E402


def main() -> int:
    dt = _parse_dt_local("2026-09-08T21:22")
    assert dt is not False and dt is not None
    assert dt.tzinfo is not None
    assert dt.tzinfo == TZ_ESCOLA
    assert dt.hour == 21
    assert dt.date().isoformat() == "2026-09-08"
    aware = _parse_dt_local("2026-09-09T00:22:00+00:00")
    assert aware.astimezone(TZ_ESCOLA).hour == 21
    empty = _parse_dt_local("", required=False)
    assert empty is None
    print("ok 114 school tz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
