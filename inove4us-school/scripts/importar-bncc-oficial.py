#!/usr/bin/env python3
"""Importa a BNCC oficial (bncc-dev/bncc-dados) para bncc_habilidades_oficial.

Não inventa código nem enunciado. Reimportar se a fonte externa mudar.

Uso:
  python scripts/importar-bncc-oficial.py
  python scripts/importar-bncc-oficial.py --from-cache
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from bncc_oficial import (  # noqa: E402
    DATASET_VERSAO,
    EXPECTED_TOTAL,
    FONTE_REPO,
    cache_dir,
    download_dataset,
    flatten_dataset,
    upsert_oficial,
)
from db import get_conn  # noqa: E402


def apply_ddl(conn) -> None:
    sql = (
        ROOT / "infra" / "db" / "migrations" / "044_school_bncc_oficial.sql"
    ).read_text(encoding="utf-8")
    old = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.autocommit = old


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data_dir = cache_dir(ROOT)
    if not args.from_cache or not (data_dir / "ensino-fundamental.json").exists():
        print(f"==> baixando {FONTE_REPO} ({DATASET_VERSAO})", flush=True)
        data_dir = download_dataset(ROOT)
    else:
        print(f"==> cache {data_dir}", flush=True)

    rows = flatten_dataset(data_dir)
    etapas: dict[str, int] = {}
    for r in rows:
        etapas[r["etapa"]] = etapas.get(r["etapa"], 0) + 1
    print(f"==> flatten {len(rows)} (esperado {EXPECTED_TOTAL}) etapas={etapas}", flush=True)
    if len(rows) != EXPECTED_TOTAL:
        print(f"ERRO: contagem {len(rows)} != {EXPECTED_TOTAL}", file=sys.stderr)
        return 2
    if args.dry_run:
        (data_dir / "flatten-count.json").write_text(
            json.dumps({"total": len(rows), "etapas": etapas, "versao": DATASET_VERSAO}, indent=2),
            encoding="utf-8",
        )
        print("dry-run: não gravou no Postgres")
        return 0

    with get_conn() as conn:
        apply_ddl(conn)
        n = upsert_oficial(conn, rows)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.bncc_habilidades_oficial")
            db_n = cur.fetchone()[0]
    print(f"==> upsert {n}; tabela={db_n} versao={DATASET_VERSAO}")
    if int(db_n) != EXPECTED_TOTAL:
        print(f"ERRO: tabela {db_n} != {EXPECTED_TOTAL}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
