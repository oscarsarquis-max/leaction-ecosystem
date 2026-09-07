#!/usr/bin/env python3
"""Confirma approve BNCC + ementa da Escola Teste intacta. Sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from db import get_conn
from psycopg2.extras import RealDictCursor

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"

with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS n FROM school_bncc_temas_canonico GROUP BY 1 ORDER BY 1"
        )
        status = [dict(r) for r in cur.fetchall()]
        cur.execute(
            """
            SELECT o.codigo, o.texto, t.tema, t.status
              FROM school_bncc_temas_canonico t
              JOIN bncc_habilidades_oficial o ON o.codigo = t.habilidade_codigo
             WHERE t.habilidade_codigo = %s
               AND t.disciplina_nome = %s
               AND t.curso_ano = %s
            """,
            ("EF06CI04", "Ciências", "6º ano"),
        )
        ef06 = [dict(r) for r in cur.fetchall()]
        cur.execute(
            """
            SELECT d.nome, left(coalesce(d.ementa,''), 80) AS ementa_prefix, length(coalesce(d.ementa,'')) AS ementa_len
              FROM school_disciplinas d
             WHERE d.instituicao_id = %s
             ORDER BY d.nome
            """,
            (INST,),
        )
        ementas = [dict(r) for r in cur.fetchall()]

print(json.dumps({"status": status, "ef06ci04": ef06, "ementas": ementas}, ensure_ascii=False, indent=2))
