#!/usr/bin/env python3
"""Importa a Matriz de Referência do ENEM (PDF INEP) para tabelas oficiais.

Não inventa enunciado. Compara o dataset enemwise só como conferência.

Uso:
  python scripts/importar-enem-oficial.py
  python scripts/importar-enem-oficial.py --dry-run
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

from enem_oficial import (  # noqa: E402
    DATASET_VERSAO,
    EXPECTED_HABILIDADES,
    EXPECTED_REDAÇÃO,
    cache_dir,
    compare_enemwise,
    flatten_oficial,
    upsert_oficial,
)
from db import get_conn  # noqa: E402


def apply_ddl(conn) -> None:
    sql = (
        ROOT / "infra" / "db" / "migrations" / "049_school_enem_oficial.sql"
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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = flatten_oficial(ROOT)
    n_hab = len(payload["habilidades"])
    n_comp = len(payload["competencias"])
    n_red = len(payload["redacao"])
    por_area: dict[str, int] = {}
    for r in payload["habilidades"]:
        por_area[r["area_codigo"]] = por_area.get(r["area_codigo"], 0) + 1
    print(
        f"==> oficial habilidades={n_hab} competencias_area={n_comp} "
        f"redacao={n_red} eixos={len(payload['eixos'])} areas={por_area}",
        flush=True,
    )
    if n_hab != EXPECTED_HABILIDADES or n_red != EXPECTED_REDAÇÃO:
        print(
            f"ERRO: esperado {EXPECTED_HABILIDADES} habilidades + "
            f"{EXPECTED_REDAÇÃO} redação; veio {n_hab}+{n_red}",
            file=sys.stderr,
        )
        return 2

    ew = cache_dir(ROOT) / "enemwise-matriz.json"
    if ew.exists():
        cmp = compare_enemwise(payload, ew)
        print(
            f"==> enemwise matched={cmp['matched']}/{n_hab} "
            f"diffs={len(cmp['texto_diferente'])} "
            f"missing={cmp['faltando_no_enemwise']} "
            f"bloom_extra={cmp['enemwise_tem_bloom_nao_oficial']}",
            flush=True,
        )
        (cache_dir(ROOT) / "comparacao-enemwise.json").write_text(
            json.dumps(cmp, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if cmp["texto_diferente"]:
            print("==> diffs (oficial venceu; enemwise não foi gravado):", flush=True)
            for d in cmp["texto_diferente"][:12]:
                print(f"    {d['codigo']}", flush=True)
    else:
        print("==> enemwise ausente — import só do PDF oficial", flush=True)

    out = cache_dir(ROOT) / "matriz-oficial.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"==> gravou {out} versao={DATASET_VERSAO}", flush=True)
    if args.dry_run:
        print("dry-run: não gravou no Postgres")
        return 0

    with get_conn() as conn:
        apply_ddl(conn)
        counts = upsert_oficial(conn, payload)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.enem_habilidades_oficial")
            db_h = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM public.enem_redacao_competencias_oficial")
            db_r = cur.fetchone()[0]
    print(f"==> upsert {counts}; tabela habilidades={db_h} redacao={db_r}")
    if int(db_h) != EXPECTED_HABILIDADES or int(db_r) != EXPECTED_REDAÇÃO:
        print(f"ERRO: tabela {db_h}+{db_r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
