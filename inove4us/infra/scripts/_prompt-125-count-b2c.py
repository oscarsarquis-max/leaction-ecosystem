#!/usr/bin/env python3
"""125 — contagem prévia B2C via ECS (código compacto, limite 8k override)."""
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
H='homologador@leaction.com.br'
def q(c,s,p=None):
    c.execute(s,p or ()); return [dict(r) for r in (c.fetchall() or [])]
def n(c,s,p=None):
    c.execute(s,p or ()); r=c.fetchone(); return int((r or {}).get('n') or 0)
out={'prompt':125,'mode':'count'}
with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as c:
        out['homolog']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier,instituicao_b2b_id::text inst FROM ctdi_clie WHERE LOWER(TRIM(mail_clie))=%s",(H,))
        out['clie_inst']=q(c,"SELECT id_clie,mail_clie,creditos_ia,plan_tier FROM ctdi_clie WHERE instituicao_b2b_id=%s::uuid",(I,))
        out['aloc']=q(c,"SELECT id,id_clie,ativo,turma_nome,disciplina_nome FROM inove_alocacoes_escola WHERE school_instituicao_id=%s::uuid ORDER BY id",(I,))
        ids=sorted({int(r['id_clie']) for r in out['aloc']}|{int(r['id_clie']) for r in out['clie_inst']}|{int(r['id_clie']) for r in out['homolog']})
        out['ids']=ids
        out['concessoes']=q(c,"SELECT id,id_clie,origem,credits FROM inove_credito_ia_concessoes WHERE instituicao_id=%s::uuid",(I,))
        out['pending_n']=n(c,"SELECT COUNT(*) n FROM inove_school_pending WHERE payload::text ILIKE %s OR COALESCE(school_key,'') ILIKE %s",('%'+I+'%','%'+I+'%'))
        out['com_n']=n(c,"SELECT COUNT(*) n FROM inove_comunicados_escola WHERE instituicao_escola_id=%s::uuid",(I,))
        out['com_dest_n']=n(c,"SELECT COUNT(*) n FROM inove_comunicados_escola_destinatarios d JOIN inove_comunicados_escola x ON x.id=d.comunicado_id WHERE x.instituicao_escola_id=%s::uuid",(I,))
        out['avisos_n']=n(c,"SELECT COUNT(*) n FROM inove_avisos_mesa WHERE instituicao_b2b_id=%s::uuid",(I,))
        out['pei_base']=q(c,"SELECT condicao,is_active,versao FROM inove_pei_overrides_base WHERE instituicao_b2b_id=%s::uuid ORDER BY condicao",(I,))
        out['pei_ind_n']=n(c,"SELECT COUNT(*) n FROM inove_pei_overrides_individual WHERE instituicao_b2b_id=%s::uuid",(I,))
        out['met_ov_n']=n(c,"SELECT COUNT(*) n FROM inove_metodologia_overrides WHERE instituicao_b2b_id=%s::uuid",(I,))
        out['met_ov']=q(c,"SELECT metodologia_nome,is_active FROM inove_metodologia_overrides WHERE instituicao_b2b_id=%s::uuid ORDER BY metodologia_nome",(I,))
        out['inst_m']=q(c,"SELECT id,id_clie,nome,ativo FROM inove_instituicoes WHERE school_instituicao_id=%s::uuid",(I,))
        iids=[int(r['id']) for r in out['inst_m']]
        out['per_n']=n(c,"SELECT COUNT(*) n FROM inove_periodos_letivos WHERE instituicao_id=ANY(%s) AND COALESCE(origem_school,FALSE)",(iids,)) if iids else 0
        out['cur_n']=n(c,"SELECT COUNT(*) n FROM inove_cursos c JOIN inove_periodos_letivos p ON p.id=c.periodo_letivo_id WHERE p.instituicao_id=ANY(%s) AND COALESCE(c.origem_school,FALSE)",(iids,)) if iids else 0
        out['dis_n']=n(c,"SELECT COUNT(*) n FROM inove_disciplinas d JOIN inove_cursos c ON c.id=d.curso_id JOIN inove_periodos_letivos p ON p.id=c.periodo_letivo_id WHERE p.instituicao_id=ANY(%s) AND COALESCE(d.origem_school,FALSE)",(iids,)) if iids else 0
        out['tur_n']=n(c,"SELECT COUNT(*) n FROM inove_turmas t JOIN inove_cursos c ON c.id=t.curso_id JOIN inove_periodos_letivos p ON p.id=c.periodo_letivo_id WHERE p.instituicao_id=ANY(%s) AND COALESCE(t.origem_school,FALSE)",(iids,)) if iids else 0
        if ids:
            out['aula_orig']=q(c,"SELECT origem,COUNT(*)::int n FROM inove_aulas_simples WHERE id_clie=ANY(%s) GROUP BY origem",(ids,))
            out['aula_esc']=n(c,"SELECT COUNT(*) n FROM inove_aulas_simples WHERE id_clie=ANY(%s) AND origem='planejamento_escola'",(ids,))
            out['aula_tot']=n(c,"SELECT COUNT(*) n FROM inove_aulas_simples WHERE id_clie=ANY(%s)",(ids,))
            out['ag_orig']=q(c,"SELECT origem,COUNT(*)::int n FROM inove_agenda_eventos WHERE id_clie=ANY(%s) GROUP BY origem",(ids,))
            out['ag_esc']=n(c,"SELECT COUNT(*) n FROM inove_agenda_eventos WHERE id_clie=ANY(%s) AND origem=ANY(%s)",(ids,['planejamento_escola','alocacao_escola','comunicado_escola']))
            out['des_n']=n(c,"SELECT COUNT(*) n FROM inove_desafios WHERE id_clie=ANY(%s)",(ids,))
            out['kan_n']=n(c,"SELECT COUNT(*) n FROM inove_kanban_cards WHERE id_clie=ANY(%s)",(ids,))
            out['kan_pei']=n(c,"SELECT COUNT(*) n FROM inove_kanban_cards WHERE id_clie=ANY(%s) AND perfil_inclusao IS NOT NULL",(ids,))
            out['imp_esc']=n(c,"SELECT COUNT(*) n FROM inove_importacoes_lote WHERE id_clie=ANY(%s) AND canal='escola'",(ids,))
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
