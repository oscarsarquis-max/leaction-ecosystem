#!/usr/bin/env python3
"""Inspect comunicados/mural Escola Teste — sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"


def rows(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(r) for r in (cur.fetchall() or [])]


def main() -> int:
    out: dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            out["comunicacoes"] = rows(
                cur,
                """
                SELECT e.id, e.titulo, e.tipo, e.publico_alvo, e.status,
                       e.data_hora_inicio, e.data_hora_fim,
                       e.replicado_b2c, e.replicado_b2c_em,
                       u.nome AS unidade_nome, t.nome AS turma_nome,
                       left(e.descricao, 80) AS descricao_preview
                FROM public.school_comunicacoes_eventos e
                LEFT JOIN public.school_unidades u ON u.id = e.unidade_id
                LEFT JOIN public.school_turmas t ON t.id = e.turma_id
                WHERE e.instituicao_id = %s
                ORDER BY e.created_at DESC
                LIMIT 30
                """,
                (INST,),
            )
            out["professores"] = rows(
                cur,
                """
                SELECT id, email_convite, status_vinculo, professor_b2c_id
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s
                ORDER BY email_convite
                """,
                (INST,),
            )
            out["alocacoes"] = rows(
                cur,
                """
                SELECT v.email_convite, v.professor_b2c_id, a.ativo,
                       t.id AS turma_id, t.nome AS turma,
                       d.nome AS disciplina, u.nome AS unidade
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                LEFT JOIN public.school_unidades u ON u.id = t.unidade_id
                WHERE a.instituicao_id = %s
                ORDER BY v.email_convite, t.nome, d.nome
                """,
                (INST,),
            )
            out["turmas"] = rows(
                cur,
                """
                SELECT t.id, t.nome, t.turno, u.nome AS unidade
                FROM public.school_turmas t
                LEFT JOIN public.school_unidades u ON u.id = t.unidade_id
                WHERE t.instituicao_id = %s
                ORDER BY t.nome
                """,
                (INST,),
            )
            out["homolog_aloc"] = rows(
                cur,
                """
                SELECT t.id AS turma_id, t.nome AS turma, d.nome AS disciplina, a.ativo
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                  AND lower(v.email_convite) = %s
                ORDER BY t.nome
                """,
                (INST, HOMOLOG),
            )
            out["gestor_operacional"] = rows(
                cur,
                """
                SELECT g.id, g.email, g.ativo, g.unidade_id,
                       COALESCE(array_agg(p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s
                  AND lower(g.email) = 'operacional@escolateste.edu.br'
                GROUP BY g.id
                """,
                (INST,),
            )
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
