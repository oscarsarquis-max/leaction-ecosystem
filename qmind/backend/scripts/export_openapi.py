"""Export deterministic openapi.json from the live FastAPI app.

Usage:
  cd qmind/backend
  $env:PYTHONPATH = (Get-Location).Path
  .\\.venv\\Scripts\\python.exe scripts\\export_openapi.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Deterministic export settings (no prod secrets required).
os.environ.setdefault(
    "DATABASE_URL_ADMIN",
    "postgresql+psycopg://admin:password123@localhost:5433/qmind",
)
os.environ.setdefault(
    "DATABASE_URL_APP",
    "postgresql+psycopg://qmind_app:qmind_app_dev@localhost:5433/qmind",
)
os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("STORAGE_BACKEND", "memory")

from app.main import app  # noqa: E402
from app.openapi_contract import dump_openapi_json  # noqa: E402

OUT = ROOT / "openapi" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Clear cache so export always rebuilds from current routes.
    app.openapi_schema = None
    text = dump_openapi_json(app)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
