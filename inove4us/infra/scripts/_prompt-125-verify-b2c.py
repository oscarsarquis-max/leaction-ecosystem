#!/usr/bin/env python3
"""125 — verificação final B2C (somente leitura)."""
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
I='3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50'
def n(c,s,p=None):
    c.execute(s,p or ()); return int((c.fetchone() or {}).get('n') or 0)
def q(c,s,p=None):
    c.execute(s,p or ()); return [dict(r) for r in (c.fetchall() or [])]
out={}
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as c:
        out['homolog']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier,instituicao_b2b_id::text inst FROM ctdi_clie WHERE id_clie=21")
        out['suiany']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier,instituicao_b2b_id::text inst FROM ctdi_clie WHERE id_clie=22")
        out['aloc']=n(c,'SELECT COUNT(*) n FROM inove_alocacoes_escola WHERE school_instituicao_id=%s::uuid',(I,))
        out['com']=n(c,'SELECT COUNT(*) n FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid',(I,))
        out['avisos']=n(c,'SELECT COUNT(*) n FROM inove_avisos_mesa WHERE instituicao_b2b_id=%s::uuid',(I,))
        out['pei_ind']=n(c,'SELECT COUNT(*) n FROM inove_pei_overrides_individual WHERE instituicao_b2b_id=%s::uuid',(I,))
        out['pei_base']=q(c,'SELECT condicao,is_active,versao FROM inove_pei_overrides_base WHERE instituicao_b2b_id=%s::uuid ORDER BY condicao',(I,))
        out['met']=q(c,'SELECT metodologia_nome,is_active FROM inove_metodologia_overrides WHERE instituicao_b2b_id=%s::uuid ORDER BY metodologia_nome',(I,))
        out['inst_m']=n(c,'SELECT COUNT(*) n FROM inove_instituicoes WHERE school_instituicao_id=%s::uuid',(I,))
        out['pend']=n(c,"SELECT COUNT(*) n FROM inove_school_pending WHERE payload::text ILIKE %s OR COALESCE(school_key,'') ILIKE %s",('%'+I+'%','%'+I+'%'))
        out['aulas21']=n(c,'SELECT COUNT(*) n FROM inove_aulas_simples WHERE id_clie=ANY(%s)',([21,22],))
        out['concessoes']=n(c,'SELECT COUNT(*) n FROM inove_credito_ia_concessoes WHERE instituicao_id=%s::uuid',(I,))
print(json.dumps(out,default=str,ensure_ascii=False))
"""


def main() -> int:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    run_python(ecs, td, network, CODE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
