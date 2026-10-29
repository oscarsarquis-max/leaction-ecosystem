#!/usr/bin/env python3
"""127 — move 9º Ano A para Ensino Fundamental II e aloca Matemática."""
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
OPER = "operacional@escolateste.edu.br"
TURMA = "9a8ceaac-c0f7-4f1a-92ac-861fc0d6650f"
CURSO = "948af05c-2c31-4bfe-b50f-9d1e8ebdfd3c"
MAT = "bb098373-f714-4f0f-93b5-c92f74c0cbe4"
VIN = "36f3737c-1664-4b0a-bcbb-be1d846a88a5"
UNID = "2310c29c-3d0f-443f-86e6-e18eb6145a49"
PER = "68a38cc9-b975-4411-815e-b1fcef171c3d"


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
                (INST, OPER),
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
    r1 = c.put(f"/api/secretaria/turmas/{TURMA}", json={"curso_id": CURSO, "serie_ano": "9º ano"})
    r2 = c.post(
        "/api/secretaria/alocacoes",
        json={
            "unidade_id": UNID,
            "periodo_id": PER,
            "disciplina_id": MAT,
            "professor_id": VIN,
            "turma_id": TURMA,
        },
    )
    print(json.dumps({"turma": {"http": r1.status_code, "body": r1.get_json(silent=True)}, "aloc": {"http": r2.status_code, "body": r2.get_json(silent=True)}}, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
