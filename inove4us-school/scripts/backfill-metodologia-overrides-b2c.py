#!/usr/bin/env python3
"""Backfill School → B2C dos overrides de metodologia já salvos (sem reescrever o catálogo).

Uso (produção, no host School):
  cd /var/www/inove4us-school
  PYTHONPATH=backend backend/.venv/bin/python scripts/backfill-metodologia-overrides-b2c.py

Por padrão só a Escola Teste. Não imprime o texto das diretrizes.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
if not (ROOT / "backend").exists():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn
from metodologias_api import _row_merged, emit_methodology_override, _LIST_SQL

INST = (os.environ.get("BACKFILL_INSTITUICAO_ID") or "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50").strip()


def main() -> int:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_LIST_SQL, (INST, INST, INST))
            rows = cur.fetchall()
    merged = [_row_merged(r) for r in rows]
    custom = [m for m in merged if m.get("is_customizado")]
    out = []
    for m in custom:
        result = emit_methodology_override(m, INST)
        http = result.get("status_code") if isinstance(result, dict) else None
        out.append(
            {
                "nome": m.get("nome"),
                "codigo": m.get("codigo"),
                "ok": bool((result or {}).get("ok")),
                "http": http,
                "diretriz_len": len(str(m.get("versao_escola") or "")),
            }
        )
    print(json.dumps({"instituicao_id": INST, "n": len(out), "itens": out}, ensure_ascii=False, indent=2))
    failed = [x for x in out if not x["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
