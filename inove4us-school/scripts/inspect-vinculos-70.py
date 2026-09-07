#!/usr/bin/env python3
"""Inspect Escola Teste vinculos (no secrets)."""
from __future__ import annotations

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

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"


def main() -> None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.email, g.nome,
                       array_agg(gz.zona ORDER BY gz.zona) AS zonas
                  FROM public.school_gestores g
                  LEFT JOIN public.school_gestor_zonas gz ON gz.gestor_id = g.id
                 WHERE g.instituicao_id = %s AND lower(g.email) = %s
                 GROUP BY g.id
                """,
                (INST, HOMOLOG),
            )
            print("HOMOLOG", dict(cur.fetchone() or {}))
            cur.execute(
                """
                SELECT v.id, v.email_convite, v.status_vinculo, v.professor_b2c_id
                  FROM public.school_professores_vinculo v
                 WHERE v.instituicao_id = %s
                 ORDER BY v.email_convite
                """,
                (INST,),
            )
            print("VINCULOS")
            for r in cur.fetchall():
                print(dict(r))
            cur.execute(
                """
                SELECT a.id, t.nome AS turma, d.nome AS disc, v.email_convite
                  FROM public.school_alocacoes a
                  JOIN public.school_turmas t ON t.id = a.turma_id
                  JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                  JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                 WHERE v.instituicao_id = %s AND lower(v.email_convite) = %s
                """,
                (INST, HOMOLOG),
            )
            print("ALOC_HOMOLOG")
            for r in cur.fetchall():
                print(dict(r))


if __name__ == "__main__":
    main()
