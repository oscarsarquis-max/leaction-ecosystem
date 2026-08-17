"""Fail if Core wire DTOs drift from committed OI public JSON Schemas v1.

Exit 0 = compatible; exit 1 = incompatibility (prints contract/field diffs).

  python scripts/check_oi_contract_compatibility.py

Optional:

  $env:QMIND_OI_SCHEMAS_DIR = "C:\\Projetos\\qmind-oi\\schemas\\v1"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DATABASE_URL_ADMIN",
    "postgresql+psycopg://admin:password123@localhost:5433/qmind_dev",
)
os.environ.setdefault(
    "DATABASE_URL_APP",
    "postgresql+psycopg://qmind_app:qmind_app_dev@localhost:5433/qmind_dev",
)
os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("STORAGE_BACKEND", "memory")

from app.modules.oi.contract_compat import check_contracts, resolve_oi_schemas_dir  # noqa: E402


def main() -> int:
    schemas_dir = resolve_oi_schemas_dir()
    print(f"OI schemas dir: {schemas_dir}")
    issues = check_contracts(oi_schemas_dir=schemas_dir)
    if not issues:
        print("Core <-> OI contracts v1: compatible")
        return 0
    print("Core <-> OI contract incompatibility:", file=sys.stderr)
    for issue in issues:
        print(f"  - {issue}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
