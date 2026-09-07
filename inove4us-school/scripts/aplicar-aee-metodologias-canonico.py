#!/usr/bin/env python3
"""Após revisão humana: publica o lote AEE × metodologia como canônico servido.

Não edita o catálogo das 39 nem school_aee_matrizes.
Não sobrescreve school_aee_metodologias_org quando o texto da escola é customização real.

Uso (só depois do OK do Oscar):
  python scripts/aplicar-aee-metodologias-canonico.py --approve
  python scripts/aplicar-aee-metodologias-canonico.py --approve --limpar-copias-org
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

from aee_metodologia_adaptacao import (  # noqa: E402
    STATUS_APROVADO,
    eh_copia_identica,
    ensure_canonico_schema,
    passos_to_text,
)
from db import get_conn  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

JSON_LOTE = ROOT / "var" / "aee-adaptacoes-revisao" / "lote.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve", action="store_true", required=True)
    ap.add_argument("--from-json", default=str(JSON_LOTE))
    ap.add_argument(
        "--limpar-copias-org",
        action="store_true",
        help="Apaga linhas de org que são cópia do catálogo (aí herdam o canônico AEE×met).",
    )
    args = ap.parse_args()

    path = Path(args.from_json)
    if not path.exists():
        print(f"Lote não encontrado: {path}", file=sys.stderr)
        return 2
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = [it for it in (payload.get("items") or []) if it.get("status_geracao") == "ok"]
    if not items:
        print("Nenhum item ok no lote.", file=sys.stderr)
        return 2

    tocados_custom = []
    aprovados = 0
    copias_apagadas = 0

    with get_conn() as conn:
        ensure_canonico_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for it in items:
                cur.execute(
                    """
                    INSERT INTO public.school_aee_metodologias_canonico (
                        condicao_categoria, metodologia_codigo, metodologia_nome,
                        passos_adaptados, status, origem, gerado_em,
                        aprovado_em, updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, 'ia_lote_2026-09-06',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (condicao_categoria, metodologia_codigo)
                    DO UPDATE SET
                        metodologia_nome = EXCLUDED.metodologia_nome,
                        passos_adaptados = EXCLUDED.passos_adaptados,
                        status = %s,
                        aprovado_em = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        it["condicao_categoria"],
                        it["metodologia_codigo"],
                        it["metodologia_nome"],
                        it["adaptado"],
                        STATUS_APROVADO,
                        STATUS_APROVADO,
                    ),
                )
                aprovados += 1

            if args.limpar_copias_org:
                cur.execute(
                    """
                    SELECT
                        org.id,
                        org.passos_customizados,
                        c.passos_execucao,
                        m.campos_experiencia_metodologica,
                        m.instituicao_id,
                        m.condicao_categoria,
                        org.metodologia_nome
                    FROM public.school_aee_metodologias_org org
                    JOIN public.school_aee_matrizes m ON m.id = org.aee_matriz_id
                    LEFT JOIN public.school_metodologias_aliases a
                      ON a.alias_norm = LOWER(TRIM(org.metodologia_nome))
                    LEFT JOIN public.school_metodologias_catalogo c
                      ON c.codigo = a.codigo
                    """
                )
                for row in cur.fetchall():
                    cat = passos_to_text(row.get("passos_execucao"))
                    if eh_copia_identica(
                        row.get("passos_customizados") or "",
                        cat,
                        row.get("campos_experiencia_metodologica") or "",
                    ):
                        cur.execute(
                            "DELETE FROM public.school_aee_metodologias_org WHERE id = %s",
                            (str(row["id"]),),
                        )
                        copias_apagadas += 1
                    else:
                        tocados_custom.append(
                            {
                                "instituicao_id": str(row.get("instituicao_id") or ""),
                                "condicao": row.get("condicao_categoria"),
                                "metodologia": row.get("metodologia_nome"),
                            }
                        )

    print(
        json.dumps(
            {
                "aprovados": aprovados,
                "copias_org_apagadas": copias_apagadas,
                "customizacoes_escola_preservadas": len(tocados_custom),
                "customizacoes": tocados_custom,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
