#!/usr/bin/env python3
"""116 — auditoria 8 condições × 39 metodologias (79/81) antes de ativar."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from aee_canonico import AEE_CANONICO, CONDICOES_ORDEM  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"


def main() -> int:
    out: dict = {"condicoes_canon": CONDICOES_ORDEM, "n_canon": len(CONDICOES_ORDEM)}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_metodologias_catalogo
                WHERE ativo = TRUE AND origem = 'padrao'
                """
            )
            out["catalogo_39"] = int((cur.fetchone() or {}).get("n") or 0)
            cur.execute(
                """
                SELECT condicao_categoria, status::text AS status,
                       COUNT(*)::int AS n
                FROM public.school_aee_metodologias_canonico
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            )
            out["canonico"] = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT condicao_categoria, COUNT(*)::int AS n
                FROM public.school_aee_metodologias_canonico
                WHERE status = 'aprovado'
                GROUP BY 1
                ORDER BY 1
                """
            )
            aprovados = {r["condicao_categoria"]: int(r["n"]) for r in cur.fetchall() or []}
            out["aprovados_por_condicao"] = aprovados
            out["total_aprovados"] = sum(aprovados.values())
            cur.execute(
                """
                SELECT m.id, m.condicao_categoria, m.versao, m.status::text AS status,
                       m.assinado_coordenador, m.assinado_psicopedagogo,
                       length(trim(m.texto_escola)) AS n_texto,
                       (trim(m.texto_escola) = trim(%s)) AS dummy
                FROM public.school_aee_matrizes m
                WHERE m.instituicao_id = %s
                ORDER BY m.condicao_categoria, m.versao DESC
                """,
                ("x", INST),
            )
            # redo without dummy
            cur.execute(
                """
                SELECT id, condicao_categoria, versao, status::text AS status,
                       assinado_coordenador, assinado_psicopedagogo,
                       left(texto_escola, 90) AS texto_preview,
                       texto_escola
                FROM public.school_aee_matrizes
                WHERE instituicao_id = %s
                ORDER BY condicao_categoria, versao DESC
                """,
                (INST,),
            )
            matrizes = []
            for r in cur.fetchall() or []:
                cond = r["condicao_categoria"]
                canon = (AEE_CANONICO.get(cond) or {}).get("descricao_base_canonica") or ""
                texto = r["texto_escola"] or ""
                matrizes.append(
                    {
                        "id": str(r["id"]),
                        "condicao": cond,
                        "versao": r["versao"],
                        "status": r["status"],
                        "coord": bool(r["assinado_coordenador"]),
                        "psico": bool(r["assinado_psicopedagogo"]),
                        "texto_igual_canon": texto.strip() == canon.strip(),
                        "texto_preview": (r["texto_preview"] or "")[:90],
                    }
                )
            out["matrizes"] = matrizes
            cur.execute(
                """
                SELECT m.condicao_categoria, m.status::text AS status,
                       COUNT(org.id)::int AS org_n,
                       COUNT(*) FILTER (WHERE length(trim(org.passos_customizados)) > 0)::int AS org_nonempty
                FROM public.school_aee_matrizes m
                LEFT JOIN public.school_aee_metodologias_org org ON org.aee_matriz_id = m.id
                WHERE m.instituicao_id = %s
                GROUP BY 1, 2, m.versao, m.id
                ORDER BY 1, m.versao DESC
                """,
                (INST,),
            )
            # simpler org by condition of latest matriz
            cur.execute(
                """
                SELECT m.condicao_categoria,
                       COUNT(org.id)::int AS org_n,
                       COUNT(*) FILTER (WHERE length(trim(org.passos_customizados)) > 0)::int AS org_nonempty
                FROM public.school_aee_matrizes m
                LEFT JOIN public.school_aee_metodologias_org org ON org.aee_matriz_id = m.id
                WHERE m.instituicao_id = %s
                GROUP BY 1
                ORDER BY 1
                """,
                (INST,),
            )
            out["org_por_condicao"] = [dict(r) for r in cur.fetchall() or []]

    # amostra TEA: um passo adaptado vs catálogo
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT can.condicao_categoria, can.metodologia_codigo, can.status,
                       left(can.passos_adaptados, 180) AS adapt_preview,
                       left(c.nome, 40) AS metodologia
                FROM public.school_aee_metodologias_canonico can
                JOIN public.school_metodologias_catalogo c ON c.codigo = can.metodologia_codigo
                WHERE can.condicao_categoria = 'TEA' AND can.status = 'aprovado'
                ORDER BY c.nome
                LIMIT 2
                """
            )
            out["amostra_tea"] = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT can.condicao_categoria, can.metodologia_codigo,
                       left(can.passos_adaptados, 120) AS adapt,
                       left(%s, 80) AS unused
                FROM public.school_aee_metodologias_canonico can
                WHERE can.status = 'aprovado'
                  AND can.passos_adaptados IS NOT NULL
                  AND length(trim(can.passos_adaptados)) > 40
                LIMIT 1
                """,
                ("x",),
            )

    resumo = []
    for nome in CONDICOES_ORDEM:
        rows = [m for m in matrizes if m["condicao"] == nome]
        ativa = next((m for m in rows if m["status"] == "ativo"), None)
        top = rows[0] if rows else None
        resumo.append(
            {
                "condicao": nome,
                "n_matrizes": len(rows),
                "status_atual": (ativa or top or {}).get("status") if rows else "sem_matriz",
                "ativa": bool(ativa),
                "aprovados_81": aprovados.get(nome, 0),
                "texto_atual_igual_canon": (ativa or top or {}).get("texto_igual_canon") if rows else None,
            }
        )
    out["resumo"] = resumo
    out["lote_312_ok"] = out["total_aprovados"] == 8 * out["catalogo_39"] and all(
        aprovados.get(n, 0) == out["catalogo_39"] for n in CONDICOES_ORDEM
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
