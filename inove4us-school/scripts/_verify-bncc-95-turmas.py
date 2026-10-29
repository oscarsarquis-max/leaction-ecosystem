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

with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT p.id, p.conteudo_resumo, t.nome AS turma, t.serie_ano,
                   p.mesa_payload_json->>'habilidade_codigo' AS first,
                   p.mesa_payload_json->'habilidade_codigos' AS codes
              FROM public.school_planos_aula_espelhados p
              JOIN public.school_turmas t ON t.id = p.turma_id
            WHERE p.conteudo_resumo ILIKE %s
                OR p.conteudo_resumo ILIKE %s
             ORDER BY p.updated_at DESC
             LIMIT 8
            """,
            ("%Cobertura 95%", "%Frações no cotidiano%"),
        )
        rows = [dict(r) for r in cur.fetchall()]
print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
