#!/usr/bin/env python3
"""128 — cobertura Radar (antes/depois)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"


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


def main():
    from app import app

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor()
    r = c.get("/api/pedagogico/radar-home")
    body = r.get_json(silent=True) or {}
    cob = body.get("cobertura") or {}
    print(json.dumps({
        "http": r.status_code,
        "periodo": {"inicio": body.get("data_inicio"), "fim": body.get("data_fim")},
        "cobertura": cob,
        "metodologias": body.get("metodologias"),
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
