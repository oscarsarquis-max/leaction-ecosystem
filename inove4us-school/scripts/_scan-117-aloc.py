#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from psycopg2.extras import RealDictCursor
from db import get_conn
INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT a.id, v.email_convite, a.notificado_b2c, a.ativo,
                   t.nome AS turma, d.nome AS disciplina
            FROM public.school_alocacoes_docentes a
            JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
            LEFT JOIN public.school_turmas t ON t.id = a.turma_id
            JOIN public.school_disciplinas d ON d.id = a.disciplina_id
            WHERE a.instituicao_id = %s
              AND lower(v.email_convite) = 'homologador@leaction.com.br'
            ORDER BY a.created_at
            """,
            (INST,),
        )
        rows = [dict(r) for r in cur.fetchall() or []]
print(json.dumps(rows, default=str, ensure_ascii=False, indent=2))
