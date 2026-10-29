#!/usr/bin/env python3
"""125 — wipe transacional B2C (Escola Teste) via ECS. Não toca overrides de metodologia/AEE base."""
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
IDS=[21,22]
def n(c,s,p=None):
    c.execute(s,p or ()); return int((c.fetchone() or {}).get('n') or 0)
def q(c,s,p=None):
    c.execute(s,p or ()); return [dict(r) for r in (c.fetchall() or [])]
out={'prompt':125,'mode':'wipe'}
with get_conn() as conn:
    conn.autocommit=False
    with conn.cursor(cursor_factory=RealDictCursor) as c:
        out['keep_before']={
            'met':n(c,'SELECT COUNT(*) n FROM inove_metodologia_overrides WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'pei_base':n(c,'SELECT COUNT(*) n FROM inove_pei_overrides_base WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'inst_m':n(c,'SELECT COUNT(*) n FROM inove_instituicoes WHERE school_instituicao_id=%s::uuid',(I,)),
        }
        if out['keep_before']['met']!=4 or out['keep_before']['pei_base']!=8:
            conn.rollback(); out['ok']=False; out['reason']='keep_before_mismatch'; print(json.dumps(out,default=str)); raise SystemExit
        cons=q(c,'SELECT id,id_clie,credits FROM inove_credito_ia_concessoes WHERE instituicao_id=%s::uuid',(I,))
        adj=[]
        for r in cons:
            c.execute('UPDATE ctdi_clie SET creditos_ia=GREATEST(0,COALESCE(creditos_ia,0)-%s) WHERE id_clie=%s RETURNING id_clie,mail_clie,creditos_ia',(int(r['credits']),int(r['id_clie'])))
            adj.append(dict(c.fetchone() or {}))
        out['credito_ajuste']=adj
        c.execute('DELETE FROM inove_credito_ia_concessoes WHERE instituicao_id=%s::uuid',(I,))
        out['del_concessoes']=c.rowcount
        c.execute('UPDATE ctdi_clie SET instituicao_b2b_id=NULL WHERE instituicao_b2b_id=%s::uuid RETURNING id_clie,mail_clie,creditos_ia,plan_tier',(I,))
        out['clie_clear']=[dict(r) for r in (c.fetchall() or [])]
        c.execute('DELETE FROM inove_comunicados_escola_destinatarios d USING inove_comunicados_escola x WHERE d.comunicado_id=x.id AND x.instituicao_escola_id=%s::uuid',(I,))
        out['del_com_dest']=c.rowcount
        c.execute("UPDATE inove_agenda_eventos SET comunicado_escola_id=NULL WHERE origem='comunicado_escola' AND comunicado_escola_id IN (SELECT id FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid)",(I,))
        c.execute('DELETE FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid',(I,))
        out['del_com']=c.rowcount
        c.execute('DELETE FROM inove_avisos_mesa WHERE instituicao_b2b_id=%s::uuid',(I,))
        out['del_avisos']=c.rowcount
        c.execute('DELETE FROM inove_pei_overrides_individual WHERE instituicao_b2b_id=%s::uuid',(I,))
        out['del_pei_ind']=c.rowcount
        c.execute('DELETE FROM inove_school_pending WHERE payload::text ILIKE %s OR COALESCE(school_key,\'\') ILIKE %s',('%'+I+'%','%'+I+'%'))
        out['del_pending']=c.rowcount
        c.execute('DELETE FROM inove_alocacoes_escola WHERE school_instituicao_id=%s::uuid',(I,))
        out['del_aloc']=c.rowcount
        c.execute('DELETE FROM inove_kanban_cards WHERE id_clie=ANY(%s)',(IDS,))
        out['del_kan']=c.rowcount
        c.execute('DELETE FROM inove_aulas_simples WHERE id_clie=ANY(%s)',(IDS,))
        out['del_aulas']=c.rowcount
        c.execute('DELETE FROM inove_agenda_eventos WHERE id_clie=ANY(%s)',(IDS,))
        out['del_agenda']=c.rowcount
        c.execute('DELETE FROM inove_desafios WHERE id_clie=ANY(%s)',(IDS,))
        out['del_des']=c.rowcount
        iids=[r['id'] for r in q(c,'SELECT id FROM inove_instituicoes WHERE school_instituicao_id=%s::uuid',(I,))]
        if iids:
            c.execute('DELETE FROM inove_turmas t USING inove_cursos cu, inove_periodos_letivos p WHERE t.curso_id=cu.id AND cu.periodo_letivo_id=p.id AND p.instituicao_id=ANY(%s) AND COALESCE(t.origem_school,FALSE)',(iids,))
            out['del_turmas_mirror']=c.rowcount
        else:
            out['del_turmas_mirror']=0
        out['keep_after']={
            'met':n(c,'SELECT COUNT(*) n FROM inove_metodologia_overrides WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'pei_base':n(c,'SELECT COUNT(*) n FROM inove_pei_overrides_base WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'inst_m':n(c,'SELECT COUNT(*) n FROM inove_instituicoes WHERE school_instituicao_id=%s::uuid',(I,)),
        }
        out['zero']={
            'aloc':n(c,'SELECT COUNT(*) n FROM inove_alocacoes_escola WHERE school_instituicao_id=%s::uuid',(I,)),
            'com':n(c,'SELECT COUNT(*) n FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid',(I,)),
            'avisos':n(c,'SELECT COUNT(*) n FROM inove_avisos_mesa WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'pei_ind':n(c,'SELECT COUNT(*) n FROM inove_pei_overrides_individual WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'concessoes':n(c,'SELECT COUNT(*) n FROM inove_credito_ia_concessoes WHERE instituicao_id=%s::uuid',(I,)),
            'clie_inst':n(c,'SELECT COUNT(*) n FROM ctdi_clie WHERE instituicao_b2b_id=%s::uuid',(I,)),
            'aulas':n(c,'SELECT COUNT(*) n FROM inove_aulas_simples WHERE id_clie=ANY(%s)',(IDS,)),
            'agenda':n(c,'SELECT COUNT(*) n FROM inove_agenda_eventos WHERE id_clie=ANY(%s)',(IDS,)),
            'des':n(c,'SELECT COUNT(*) n FROM inove_desafios WHERE id_clie=ANY(%s)',(IDS,)),
            'kan':n(c,'SELECT COUNT(*) n FROM inove_kanban_cards WHERE id_clie=ANY(%s)',(IDS,)),
        }
        out['homolog']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier,instituicao_b2b_id::text inst FROM ctdi_clie WHERE id_clie=21")
        out['suiany']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier,instituicao_b2b_id::text inst FROM ctdi_clie WHERE id_clie=22")
        if out['keep_after']!=out['keep_before'] or any(v!=0 for v in out['zero'].values()):
            conn.rollback(); out['ok']=False; out['reason']='verify_failed'; print(json.dumps(out,default=str)); raise SystemExit
        conn.commit(); out['ok']=True
print(json.dumps(out,default=str,ensure_ascii=False))
"""


def main() -> int:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("override_bytes", len(CODE), file=sys.stderr)
    if len(CODE) > 7800:
        raise SystemExit(f"CODE too large: {len(CODE)}")
    run_python(ecs, td, network, CODE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
