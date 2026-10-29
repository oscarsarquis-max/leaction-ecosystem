#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from db import get_conn
from psycopg2.extras import RealDictCursor
from radar_home import _row_aula

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT p.id, left(p.conteudo_resumo, 80) AS resumo,
                   p.mesa_payload_json->>'habilidade_codigo' AS first,
                   p.mesa_payload_json->'habilidade_codigos' AS codes
              FROM public.school_planos_aula_espelhados p
             WHERE p.instituicao_id = %s
               AND (
                    p.conteudo_resumo ILIKE %s
                 OR p.mesa_payload_json::text ILIKE %s
               )
             ORDER BY p.updated_at DESC NULLS LAST
             LIMIT 8
            """,
            (INST, "%Fra%", "%EF06MA07%"),
        )
        rows = [dict(r) for r in cur.fetchall()]
print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
