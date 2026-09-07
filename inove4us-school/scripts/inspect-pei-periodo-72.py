#!/usr/bin/env python3
"""Inspect PEI periodo_letivo_id for prompt 72 — no secrets."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"


def jsonable(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    return v


def rows(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [{k: jsonable(v) for k, v in dict(r).items()} for r in (cur.fetchall() or [])]


def main() -> int:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            out = {
                "cols": rows(
                    cur,
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'school_pei_alunos'
                      AND column_name IN ('periodo_letivo_id', 'intervencoes_previstas')
                    """,
                ),
                "peis": rows(
                    cur,
                    """
                    SELECT p.id, p.status, p.versao, p.periodo_letivo_id,
                           p.assinado_coordenador, p.assinado_psicopedagogo,
                           p.nome_completo, p.pei_linha_id, p.aluno_id, p.updated_at
                    FROM public.school_pei_alunos p
                    WHERE p.instituicao_id = %s
                      AND (p.id = %s OR p.nome_completo ILIKE %s)
                    ORDER BY p.created_at
                    """,
                    (INST, PEI, "%Lucas Mendes%"),
                ),
                "periodos": rows(
                    cur,
                    """
                    SELECT id, rotulo, data_inicio, data_fim, ativo, status
                    FROM public.school_periodos_letivos
                    WHERE instituicao_id = %s
                    ORDER BY data_inicio
                    """,
                    (INST,),
                ),
            }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
