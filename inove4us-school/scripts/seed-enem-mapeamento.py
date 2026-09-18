#!/usr/bin/env python3
"""150 — grava o mapeamento genérico disciplina → ENEM (sem escola)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from enem_catalogo import linhas_alias, linhas_mapeamento  # noqa: E402
from enem_oficial import DATASET_VERSAO  # noqa: E402
from db import get_conn  # noqa: E402


def apply_ddl(conn) -> None:
    sql = (ROOT / "infra" / "db" / "migrations" / "051_school_enem_mapeamento.sql").read_text(
        encoding="utf-8"
    )
    old = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.autocommit = old


def seed(cur) -> None:
    cur.execute("DELETE FROM public.enem_disciplina_alias")
    cur.execute("DELETE FROM public.enem_disciplina_mapeamento")
    for row in linhas_mapeamento():
        cur.execute(
            """
            INSERT INTO public.enem_disciplina_mapeamento (
                disciplina_canonica, area_codigo, competencia_numero,
                nuance, dataset_versao
            ) VALUES (%(disciplina_canonica)s, %(area_codigo)s, %(competencia_numero)s,
                      %(nuance)s, %(dataset_versao)s)
            """,
            {**row, "dataset_versao": DATASET_VERSAO},
        )
    for row in linhas_alias():
        cur.execute(
            """
            INSERT INTO public.enem_disciplina_alias (alias_norm, disciplina_canonica)
            VALUES (%(alias_norm)s, %(disciplina_canonica)s)
            """,
            row,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    maps = linhas_mapeamento()
    aliases = linhas_alias()
    print(
        json.dumps(
            {
                "mapeamentos": len(maps),
                "aliases": len(aliases),
                "disciplinas": sorted({r["disciplina_canonica"] for r in maps}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.dry_run:
        return 0
    with get_conn() as conn:
        apply_ddl(conn)
        with conn.cursor() as cur:
            seed(cur)
            cur.execute("SELECT COUNT(*) FROM public.enem_disciplina_mapeamento")
            n_m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM public.enem_disciplina_alias")
            n_a = cur.fetchone()[0]
    print(f"==> gravou mapeamento={n_m} alias={n_a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
