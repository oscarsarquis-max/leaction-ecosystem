#!/usr/bin/env python3
"""Inspect Escola Teste in production — no secrets."""
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
HOMOLOG_EMAIL = "homologador@leaction.com.br"


def rows(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(r) for r in (cur.fetchall() or [])]


def main() -> int:
    out: dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            out["instituicao"] = rows(
                cur,
                """
                SELECT id, razao_social, dominio_email, status, licencas_contratadas
                FROM public.school_instituicoes WHERE id = %s
                """,
                (INST,),
            )
            out["homologador"] = rows(
                cur,
                """
                SELECT g.id, g.nome, g.email, g.cargo, g.ativo,
                       COALESCE(array_agg(p.zona ORDER BY p.zona)
                         FILTER (WHERE p.ativo), '{}') AS zonas_ativas
                FROM public.school_gestores g
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s AND lower(g.email) = %s
                GROUP BY g.id
                """,
                (INST, HOMOLOG_EMAIL),
            )
            out["homologadores_tabela"] = rows(
                cur,
                """
                SELECT id, email, nome, funcao, escopo_dados, ativo
                FROM public.school_homologadores
                WHERE instituicao_id = %s
                ORDER BY email
                """,
                (INST,),
            )
            out["gestores"] = rows(
                cur,
                """
                SELECT g.email, g.nome, g.cargo, g.ativo,
                       COALESCE(array_agg(p.zona ORDER BY p.zona)
                         FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s
                GROUP BY g.id
                ORDER BY g.email
                """,
                (INST,),
            )
            out["unidades"] = rows(
                cur,
                """
                SELECT id, nome, endereco, logradouro, numero, bairro, cep,
                       cidade, uf, telefone, email_institucional, ativo
                FROM public.school_unidades WHERE instituicao_id = %s
                """,
                (INST,),
            )
            out["equipe"] = rows(
                cur,
                """
                SELECT e.papel, e.nome, e.email, e.area_coordenacao, e.ativo
                FROM public.school_unidade_equipe e
                JOIN public.school_unidades u ON u.id = e.unidade_id
                WHERE u.instituicao_id = %s
                """,
                (INST,),
            )
            out["periodos"] = rows(
                cur,
                """
                SELECT id, rotulo, ano_letivo, status, em_curso, ativo
                FROM public.school_periodos_letivos WHERE instituicao_id = %s
                """,
                (INST,),
            )
            out["cursos"] = rows(
                cur,
                """
                SELECT c.id, c.nome, c.nivel, c.turma_turno, c.periodo_letivo_id
                FROM public.school_cursos c
                JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE p.instituicao_id = %s
                """,
                (INST,),
            )
            out["turmas"] = rows(
                cur,
                """
                SELECT id, nome, serie_ano, turno, curso_id, periodo_letivo_id
                FROM public.school_turmas WHERE instituicao_id = %s
                ORDER BY nome
                """,
                (INST,),
            )
            out["disciplinas"] = rows(
                cur,
                """
                SELECT id, nome FROM public.school_disciplinas
                WHERE instituicao_id = %s ORDER BY nome
                """,
                (INST,),
            )
            out["curso_disciplinas"] = rows(
                cur,
                """
                SELECT c.nome AS curso, d.nome AS disciplina
                FROM public.school_curso_disciplinas cd
                JOIN public.school_cursos c ON c.id = cd.curso_id
                JOIN public.school_disciplinas d ON d.id = cd.disciplina_id
                JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE p.instituicao_id = %s
                ORDER BY c.nome, d.nome
                """,
                (INST,),
            )
            out["alunos_count_por_turma"] = rows(
                cur,
                """
                SELECT t.nome AS turma, COUNT(a.id) AS n
                FROM public.school_turmas t
                LEFT JOIN public.school_alunos a ON a.turma_id = t.id AND a.ativo IS NOT FALSE
                WHERE t.instituicao_id = %s
                GROUP BY t.nome ORDER BY t.nome
                """,
                (INST,),
            )
            out["alunos"] = rows(
                cur,
                """
                SELECT a.id, a.nome, a.matricula, t.nome AS turma
                FROM public.school_alunos a
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                ORDER BY t.nome, a.nome
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
                SELECT v.email_convite, d.nome AS disciplina, t.nome AS turma,
                       a.notificado_b2c
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                ORDER BY v.email_convite, d.nome
                """,
                (INST,),
            )
            out["pei"] = rows(
                cur,
                """
                SELECT p.id, p.nome_completo, p.matricula, p.aluno_id,
                       p.assinado_coordenador, p.assinado_psicopedagogo,
                       m.condicao_categoria, m.status AS matriz_status,
                       m.assinado_coordenador AS matriz_coord,
                       m.assinado_psicopedagogo AS matriz_psico
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.instituicao_id = %s
                """,
                (INST,),
            )
            out["matrizes_aee"] = rows(
                cur,
                """
                SELECT id, condicao_categoria, status, versao,
                       assinado_coordenador, assinado_psicopedagogo
                FROM public.school_aee_matrizes WHERE instituicao_id = %s
                """,
                (INST,),
            )
            out["avisos"] = rows(
                cur,
                """
                SELECT id, texto, ativo, replicado_b2c
                FROM public.school_avisos_mesa WHERE instituicao_id = %s
                """,
                (INST,),
            )
            out["metodologias_custom"] = rows(
                cur,
                """
                SELECT cat.nome AS metodologia_nome,
                       (NULLIF(trim(coalesce(org.passos_customizados,'')),'') IS NOT NULL) AS tem_passos
                FROM public.school_metodologias_org org
                JOIN public.school_metodologias_catalogo cat
                  ON cat.id = org.metodologia_id_canonica
                WHERE org.instituicao_id = %s
                  AND NULLIF(trim(coalesce(org.passos_customizados,'')),'') IS NOT NULL
                ORDER BY cat.nome
                """,
                (INST,),
            )

    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
