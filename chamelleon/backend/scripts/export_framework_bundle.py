#!/usr/bin/env python3
"""Exporta framework(s) para JSON (bundle completo)."""

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
from app.services.framework_bundle_service import export_framework_bundle

DEFAULT_FRAMEWORKS = ("telecomunicacoes-v1", "construcao-civil-v1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta bundles de frameworks Chamelleon")
    parser.add_argument(
        "framework_ids",
        nargs="*",
        default=list(DEFAULT_FRAMEWORKS),
        help="IDs dos frameworks (padrao: telecom + construcao civil)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "infra", "data", "bundles"),
    )
    parser.add_argument("--gzip", action="store_true", help="Salva .json.gz")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    app = create_app()
    with app.app_context():
        for framework_id in args.framework_ids:
            bundle = export_framework_bundle(framework_id)
            filename = f"{framework_id}.json"
            path = os.path.join(args.output_dir, filename)
            payload = json.dumps(bundle, ensure_ascii=False, indent=2)
            if args.gzip:
                path = f"{path}.gz"
                with gzip.open(path, "wt", encoding="utf-8") as handle:
                    handle.write(payload)
            else:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(payload)
            print(f"[+] {framework_id} -> {path} ({bundle['counts']['assessment_items']} questoes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
