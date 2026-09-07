#!/usr/bin/env python3
"""Prompt 72 — declara o período letivo vigente no PEI de Lucas Mendes.

Não altera assinaturas. Caminho de dado (não passa pelo PUT).
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path("/var/www/inove4us-school")
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"
ALUNO = "a65d3132-cbdc-4b8b-9ca4-40cc04f799b9"


def jsonable(v):
    if isinstance(v, (datetime, date, UUID)):
        return str(v)
    return v


def main() -> int:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                ALTER TABLE public.school_pei_alunos
                    ADD COLUMN IF NOT EXISTS periodo_letivo_id UUID
                """
            )
            cur.execute(
                """
                SELECT id, rotulo, data_inicio, data_fim
                FROM public.school_periodos_letivos
                WHERE instituicao_id = %s
                ORDER BY ativo DESC, data_inicio DESC
                LIMIT 1
                """,
                (INST,),
            )
            periodo = cur.fetchone()
            if not periodo:
                raise SystemExit("Nenhum período letivo na Escola Teste.")
            cur.execute(
                """
                UPDATE public.school_pei_alunos
                SET periodo_letivo_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE instituicao_id = %s
                  AND (id = %s OR aluno_id = %s)
                  AND status <> 'arquivado'
                RETURNING id, nome_completo, status, periodo_letivo_id,
                          assinado_coordenador, assinado_psicopedagogo
                """,
                (str(periodo["id"]), INST, PEI, ALUNO),
            )
            updated = cur.fetchall() or []
    out = {
        "periodo": {k: jsonable(v) for k, v in dict(periodo).items()},
        "peis": [{k: jsonable(v) for k, v in dict(r).items()} for r in updated],
    }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
