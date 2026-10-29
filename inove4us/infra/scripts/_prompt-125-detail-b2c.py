#!/usr/bin/env python3
"""125 — detalhe aulas/desafios/agenda dos id_clie 21/22 (somente leitura)."""
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
ids=[21,22]
I='3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50'
def q(c,s,p=None):
    c.execute(s,p or ()); return [dict(r) for r in (c.fetchall() or [])]
out={}
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as c:
        out['aulas']=q(c,"SELECT id,id_clie,origem,turma_nome,left(tema_aula,80) tema,data_planejada,id_evento_agenda FROM inove_aulas_simples WHERE id_clie=ANY(%s) ORDER BY id",(ids,))
        out['agenda']=q(c,"SELECT id_evento,id_clie,origem,tipo,turma,left(titulo,80) titulo,comunicado_escola_id::text com FROM inove_agenda_eventos WHERE id_clie=ANY(%s) ORDER BY id_evento",(ids,))
        out['des']=q(c,"SELECT id::text,id_clie,left(coalesce(titulo,''),80) titulo FROM inove_desafios WHERE id_clie=ANY(%s)",(ids,))
        out['kan']=q(c,"SELECT id,id_clie,id_evento,desafio_id::text,left(titulo,80) titulo,perfil_inclusao FROM inove_kanban_cards WHERE id_clie=ANY(%s)",(ids,))
        out['pend']=q(c,"SELECT id,email,event_type,left(coalesce(school_key,''),60) k FROM inove_school_pending WHERE payload::text ILIKE %s OR COALESCE(school_key,'') ILIKE %s ORDER BY id",( '%'+I+'%','%'+I+'%'))
        out['coms']=q(c,"SELECT id::text,tipo,status,left(titulo,80) titulo FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid ORDER BY titulo",(I,))
print(json.dumps(out,default=str,ensure_ascii=False))
"""


def main() -> int:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("override_bytes", len(CODE), file=sys.stderr)
    run_python(ecs, td, network, CODE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
