#!/usr/bin/env python3
"""117 — probe read-only B2C RDS via ECS: pending, concessoes, alocacoes espelho."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boto3

from _ecs_repor_credito import run_python, service_network

CODE = r"""
import json
from psycopg2.extras import RealDictCursor
from db import get_conn
AID = '0f81b03b-d9c8-45c7-8d86-efc4c091dfd9'
out = {}
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'UPDATE public.inove_alocacoes_escola SET ativo = FALSE, updated_at = CURRENT_TIMESTAMP '
            'WHERE school_alocacao_id = %s::uuid RETURNING id, turma_nome, ativo',
            (AID,),
        )
        out['deactivated'] = [dict(r) for r in cur.fetchall() or []]
        cur.execute(
            'SELECT id, turma_nome, school_alocacao_id::text, ativo FROM public.inove_alocacoes_escola '
            'WHERE id_clie = 21 ORDER BY id'
        )
        out['alocacoes_21'] = [dict(r) for r in cur.fetchall() or []]
        cur.execute(
            'SELECT COUNT(*)::int AS n FROM public.inove_credito_ia_concessoes WHERE id_clie = 21'
        )
        out['concessoes_21'] = int((cur.fetchone() or {}).get('n') or 0)
        cur.execute('SELECT creditos_ia FROM public.ctdi_clie WHERE id_clie = 21')
        out['creditos_21'] = int((cur.fetchone() or {}).get('creditos_ia') or 0)
print(json.dumps(out, default=str, ensure_ascii=False))
"""


def main() -> int:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("taskdef", td, file=sys.stderr)
    run_python(ecs, td, network, CODE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
