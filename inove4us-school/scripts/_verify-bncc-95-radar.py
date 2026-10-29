#!/usr/bin/env python3
import json, sys
from datetime import date
from pathlib import Path
ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from db import get_conn
from psycopg2.extras import RealDictCursor
from radar_home import fetch_radar_home

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        payload = fetch_radar_home(
            cur,
            instituicao_id=INST,
            data_inicio=date(2026, 9, 7),
            data_fim=date(2026, 9, 13),
        )
        cur.execute(
            """
            SELECT p.semana_referencia, p.conteudo_resumo,
                   p.mesa_payload_json->>'habilidade_codigo' AS first,
                   p.mesa_payload_json->'habilidade_codigos' AS codes
              FROM public.school_planos_aula_espelhados p
             WHERE p.conteudo_resumo ILIKE %s
             ORDER BY p.updated_at DESC
             LIMIT 3
            """,
            ("%Cobertura 95%",),
        )
        prova = [dict(r) for r in cur.fetchall()]
mat = [i for i in (payload.get("cobertura") or {}).get("itens") or [] if "matem" in (i.get("disciplina_nome") or "").casefold()]
print(json.dumps({"semana_prova": prova, "cobertura_matematica": mat, "cobertura_todas": payload.get("cobertura")}, ensure_ascii=False, indent=2, default=str))
