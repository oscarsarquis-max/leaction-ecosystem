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

def main():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT disciplina_nome, curso_ano, count(*)::int AS n
                  FROM public.school_bncc_temas_canonico
                 WHERE status = 'aprovado'
                 GROUP BY 1, 2
                 ORDER BY 1, 2
                """
            )
            print(json.dumps([dict(r) for r in cur.fetchall()], ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
