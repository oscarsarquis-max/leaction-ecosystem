#!/usr/bin/env python3
"""Importa bundle(s) JSON de framework(s)."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.services.framework_bundle_service import import_framework_bundle, load_framework_bundle_file


def _load_bundle(path: str) -> dict:
    return load_framework_bundle_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa bundles de frameworks Chamelleon")
    parser.add_argument("paths", nargs="+", help="Arquivos .json ou .json.gz")
    parser.add_argument("--keep-existing", action="store_true", help="Falha se framework ja existir")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        for path in args.paths:
            bundle = _load_bundle(path)
            result = import_framework_bundle(bundle, replace=not args.keep_existing)
            print(f"[+] {result['framework_id']} importado ({result['counts'].get('assessment_items', '?')} questoes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
