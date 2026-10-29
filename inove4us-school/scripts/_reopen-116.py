#!/usr/bin/env python3
"""116 — freeze Lucas, 312, PUT AEE ativo=409, reopen após limpeza."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from aee_canonico import CONDICOES_ORDEM  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
LUCAS_PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"
TDAH_V1 = "9dd3321c-5fb2-4483-8421-f10626da5891"
MARKER = "[TESTE VARREDURA 116]"
TEA_ATIVA = "6c46f3f1-c72f-4a29-97e0-afa9622978ed"


def gestor():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                       i.razao_social AS instituicao_nome,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s AND lower(g.email) = %s
                GROUP BY g.id, i.razao_social
                """,
                (INST, HOMOLOG),
            )
            row = cur.fetchone()
            return {
                "id": str(row["id"]),
                "instituicao_id": str(row["instituicao_id"]),
                "instituicao_nome": row.get("instituicao_nome"),
                "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
                "nome": row["nome"],
                "email": row["email"],
                "cargo": row["cargo"],
                "zonas": list(row["zonas"] or []),
            }


def client():
    from app import app

    user = gestor()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c


def main() -> int:
    c = client()
    out = {}
    lucas = c.get(f"/api/pei/alunos/{LUCAS_PEI}").get_json(silent=True) or {}
    out["lucas_freeze"] = {
        "http": 200 if lucas.get("id") else 0,
        "aee_matriz_id": lucas.get("aee_matriz_id"),
        "aee_versao": lucas.get("aee_versao"),
        "status": lucas.get("status"),
        "valido": lucas.get("valido"),
        "fixo_v1": lucas.get("aee_matriz_id") == TDAH_V1,
    }
    put_ativo = c.put(
        f"/api/aee/matriz/{TEA_ATIVA}",
        json={"texto_escola": "nao deve gravar"},
    )
    out["edit_aee_ativo"] = {
        "http": put_ativo.status_code,
        "error": (put_ativo.get_json(silent=True) or {}).get("error"),
    }
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT condicao_categoria, COUNT(*)::int AS n
                FROM public.school_aee_metodologias_canonico
                WHERE status = 'aprovado'
                GROUP BY 1
                """
            )
            por = {r["condicao_categoria"]: int(r["n"]) for r in cur.fetchall() or []}
            out["lote_81"] = {
                "por_condicao": por,
                "total": sum(por.values()),
                "lote_312_ok": sum(por.values()) == 312
                and all(por.get(x) == 39 for x in CONDICOES_ORDEM),
            }
            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_aee_metodologias_org
                """
            )
            out["org_custom_n"] = int((cur.fetchone() or {}).get("n") or 0)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def reopen():
    c = client()
    out = {"oito": []}
    for cond in CONDICOES_ORDEM:
        b = c.get("/api/aee/matriz", query_string={"condicao": cond}).get_json(silent=True) or {}
        a = b.get("ativa") or {}
        out["oito"].append(
            {
                "condicao": cond,
                "ativa": a.get("status"),
                "versao": a.get("versao"),
                "id": a.get("id"),
            }
        )
    leftover = c.get("/api/pei/alunos").get_json(silent=True) or []
    if isinstance(leftover, dict):
        leftover = leftover.get("items") or leftover.get("alunos") or []
    out["pei_marker"] = [
        p.get("nome_completo") for p in leftover if MARKER in (p.get("nome_completo") or "")
    ]
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int AS n FROM public.school_alunos
                WHERE instituicao_id = %s AND nome LIKE %s
                """,
                (INST, f"%{MARKER}%"),
            )
            out["alunos_marker"] = int((cur.fetchone() or {}).get("n") or 0)
    out["todas_ativas"] = all(x.get("ativa") == "ativo" for x in out["oito"])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["todas_ativas"] and not out["pei_marker"] and out["alunos_marker"] == 0 else 1


if __name__ == "__main__":
    phase = (sys.argv[1] if len(sys.argv) > 1 else "pre").strip()
    if phase == "reopen":
        raise SystemExit(reopen())
    raise SystemExit(main())
