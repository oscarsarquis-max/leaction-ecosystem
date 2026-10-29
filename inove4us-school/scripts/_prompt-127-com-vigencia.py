#!/usr/bin/env python3
"""Estender vigência da reunião pedagógica (hoje + próxima semana)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
OPER = "operacional@escolateste.edu.br"
CID = "b510e855-e129-402d-abc0-a3ead64c7391"
TZ = ZoneInfo("America/Sao_Paulo")


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

    now = datetime.now(TZ)
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor()
    r = c.patch(
        f"/api/secretaria/comunicacoes/{CID}",
        json={
            "data_hora_inicio": now.replace(hour=8, minute=0, second=0, microsecond=0).isoformat(),
            "data_hora_fim": (now + timedelta(days=8)).replace(hour=18, minute=0, second=0, microsecond=0).isoformat(),
        },
    )
    print(json.dumps({"http": r.status_code, "body": r.get_json(silent=True)}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
