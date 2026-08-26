"""Refresh committed OI public schema snapshots used by the Core compatibility check.

Copies from sibling qmind-oi (or QMIND_OI_SCHEMAS_DIR) into backend/contracts/oi/v1/.

Does not import qmind_oi — file copy only.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "contracts" / "oi" / "v1"
FILES = (
    "organization-context-input.schema.json",
    "organizational-insights.schema.json",
    "problem-context-input.schema.json",
    "problem-analysis.schema.json",
    "execution-intelligence-input.schema.json",
    "execution-intelligence-result.schema.json",
)


def main() -> int:
    env = os.environ.get("QMIND_OI_SCHEMAS_DIR", "").strip()
    if env:
        source = Path(env)
    else:
        source = ROOT.parent.parent / "qmind-oi" / "schemas" / "v1"
    if not source.is_dir():
        print(f"Source schemas dir not found: {source}", file=sys.stderr)
        return 1
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = source / name
        if not src.is_file():
            print(f"Missing {src}", file=sys.stderr)
            return 1
        dest = TARGET / name
        shutil.copyfile(src, dest)
        print(f"Synced {src} -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
