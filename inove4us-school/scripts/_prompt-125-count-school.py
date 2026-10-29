#!/usr/bin/env python3
"""125 — contagem prévia (somente leitura) Escola Teste em produção School."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"

KEEP_TABLES = [
    "school_instituicoes",
    "school_gestores",
    "school_gestor_perfis",
    "school_homologadores",
    "school_unidades",
    "school_unidade_equipe",
    "school_periodos_letivos",
    "school_cursos",
    "school_disciplinas",
    "school_curso_disciplinas",
    "school_curriculo",
    "school_metodologias_catalogo",
    "school_metodologias_org",
    "school_metodologia_config",
    "school_metodologias_aliases",
    "school_aee_matrizes",
    "school_aee_metodologias_canonico",
    "school_aee_metodologias_org",
    "school_pei_diretriz_base",
    "school_pei_campo_experiencia",
    "school_pei_matriz_documental",
    "school_bncc_temas_canonico",
    "bncc_habilidades_oficial",
    "school_licencas",
    "school_editor_pedagogico",
    "school_feedback_features",
    "school_calendario_letivo",
    "school_roteiro_respostas",
    "school_homologacao_sessoes",
    "school_homologacao_eventos",
    "school_hub_eventos_processados",
    "school_provisionamento_email",
]

DELETE_TABLES = [
    "school_planejamento_escolar",
    "school_comunicacoes_eventos",
    "school_avisos_mesa",
    "school_curadoria_metodologias",
    "school_curadoria_pei",
    "school_planos_aula_espelhados",
    "school_pei_aluno_documental",
    "school_pei_alunos",
    "school_alocacoes_docentes",
    "school_professor_turma",
    "school_professor_disciplina_habilitacao",
    "school_professor_recursos",
    "school_professor_avaliacoes",
    "school_professores_vinculo",
    "school_alunos",
    "school_turmas",
]


def _q(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(r) for r in (cur.fetchall() or [])]


def _one(cur, sql, params=None):
    rows = _q(cur, sql, params)
    return rows[0] if rows else {}


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'public' AND table_name = %s
        """,
        (name,),
    )
    return cur.fetchone() is not None


def _cols(cur, name: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = %s
        """,
        (name,),
    )
    return {r["column_name"] for r in (cur.fetchall() or [])}


def _count_for(cur, table: str) -> dict:
    if not _table_exists(cur, table):
        return {"table": table, "exists": False, "n": None}
    cols = _cols(cur, table)
    if "instituicao_id" in cols:
        n = _one(
            cur,
            f"SELECT COUNT(*)::int AS n FROM public.{table} WHERE instituicao_id = %s",
            (INST,),
        )["n"]
        n_other = _one(
            cur,
            f"SELECT COUNT(*)::int AS n FROM public.{table} WHERE instituicao_id IS DISTINCT FROM %s",
            (INST,),
        )["n"]
        return {
            "table": table,
            "exists": True,
            "filter": "instituicao_id",
            "n": int(n),
            "n_other_inst": int(n_other),
        }
    if table == "school_gestor_perfis":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_gestor_perfis p
              JOIN public.school_gestores g ON g.id = p.gestor_id
             WHERE g.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "gestor.instituicao_id", "n": int(n)}
    if table == "school_unidade_equipe":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_unidade_equipe e
              JOIN public.school_unidades u ON u.id = e.unidade_id
             WHERE u.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "unidade.instituicao_id", "n": int(n)}
    if table == "school_cursos":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_cursos c
              JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
             WHERE p.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "periodo.instituicao_id", "n": int(n)}
    if table == "school_curso_disciplinas":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_curso_disciplinas cd
              JOIN public.school_cursos c ON c.id = cd.curso_id
              JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
             WHERE p.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "curso→periodo.instituicao_id", "n": int(n)}
    if table == "school_professor_turma":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_professor_turma pt
              JOIN public.school_professores_vinculo v ON v.id = pt.professor_vinculo_id
             WHERE v.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        n_other = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_professor_turma pt
              JOIN public.school_professores_vinculo v ON v.id = pt.professor_vinculo_id
             WHERE v.instituicao_id IS DISTINCT FROM %s
            """,
            (INST,),
        )["n"]
        return {
            "table": table,
            "exists": True,
            "filter": "vinculo.instituicao_id",
            "n": int(n),
            "n_other_inst": int(n_other),
        }
    if table == "school_aee_metodologias_org":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_aee_metodologias_org o
              JOIN public.school_aee_matrizes m ON m.id = o.aee_matriz_id
             WHERE m.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "matriz.instituicao_id", "n": int(n)}
    if table == "school_pei_campo_experiencia":
        n = _one(
            cur,
            """
            SELECT COUNT(*)::int AS n
              FROM public.school_pei_campo_experiencia c
              JOIN public.school_pei_diretriz_base d ON d.id = c.pei_diretriz_base_id
             WHERE d.instituicao_id = %s
            """,
            (INST,),
        )["n"]
        return {"table": table, "exists": True, "filter": "diretriz.instituicao_id", "n": int(n)}
    if table in ("school_metodologias_catalogo", "school_aee_metodologias_canonico", "bncc_habilidades_oficial"):
        n = _one(cur, f"SELECT COUNT(*)::int AS n FROM public.{table}")["n"]
        return {"table": table, "exists": True, "filter": "global", "n": int(n)}
    if table == "school_bncc_temas_canonico":
        n = _one(cur, "SELECT COUNT(*)::int AS n FROM public.school_bncc_temas_canonico")["n"]
        by_status = _q(
            cur,
            """
            SELECT status, COUNT(*)::int AS n
              FROM public.school_bncc_temas_canonico
             GROUP BY status ORDER BY status
            """,
        )
        return {
            "table": table,
            "exists": True,
            "filter": "global (curado, sem instituicao_id)",
            "n": int(n),
            "by_status": by_status,
        }
    n = _one(cur, f"SELECT COUNT(*)::int AS n FROM public.{table}")["n"]
    return {"table": table, "exists": True, "filter": "unscoped_total", "n": int(n), "note": "sem instituicao_id"}


def _fingerprint(cur, table: str) -> dict | None:
    if not _table_exists(cur, table):
        return None
    cols = _cols(cur, table)
    pk = "id"
    if pk not in cols:
        return {"table": table, "n": _count_for(cur, table).get("n")}
    if "instituicao_id" in cols:
        cur.execute(
            f"SELECT id::text AS id FROM public.{table} WHERE instituicao_id = %s ORDER BY id::text",
            (INST,),
        )
    elif table == "school_metodologias_catalogo":
        cur.execute("SELECT id::text AS id FROM public.school_metodologias_catalogo ORDER BY id::text")
    elif table == "school_aee_metodologias_canonico":
        cur.execute("SELECT id::text AS id FROM public.school_aee_metodologias_canonico ORDER BY id::text")
    elif table == "bncc_habilidades_oficial":
        cur.execute("SELECT codigo::text AS id FROM public.bncc_habilidades_oficial ORDER BY codigo")
    elif table == "school_bncc_temas_canonico":
        cur.execute("SELECT id::text AS id FROM public.school_bncc_temas_canonico ORDER BY id::text")
    elif table == "school_aee_metodologias_org":
        cur.execute(
            """
            SELECT o.id::text AS id
              FROM public.school_aee_metodologias_org o
              JOIN public.school_aee_matrizes m ON m.id = o.aee_matriz_id
             WHERE m.instituicao_id = %s
             ORDER BY o.id::text
            """,
            (INST,),
        )
    else:
        return {"table": table, "skipped": True}
    ids = [r["id"] for r in (cur.fetchall() or [])]
    blob = ",".join(ids).encode("utf-8")
    return {"table": table, "n": len(ids), "sha256": hashlib.sha256(blob).hexdigest()}


def main() -> int:
    out: dict = {"prompt": 125, "mode": "count_readonly", "instituicao_id": INST}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            out["instituicao"] = _q(
                cur,
                """
                SELECT id::text, razao_social, dominio_email, status, licencas_contratadas
                  FROM public.school_instituicoes WHERE id = %s
                """,
                (INST,),
            )
            out["outras_instituicoes"] = _q(
                cur,
                """
                SELECT id::text, razao_social, dominio_email
                  FROM public.school_instituicoes
                 WHERE id IS DISTINCT FROM %s
                 ORDER BY razao_social
                """,
                (INST,),
            )
            out["gestores"] = _q(
                cur,
                """
                SELECT g.email, g.nome, g.cargo, g.ativo,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                  FROM public.school_gestores g
                  LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                 WHERE g.instituicao_id = %s
                 GROUP BY g.id
                 ORDER BY g.email
                """,
                (INST,),
            )
            out["vinculos"] = _q(
                cur,
                """
                SELECT id::text, email_convite, status_vinculo, professor_b2c_id
                  FROM public.school_professores_vinculo
                 WHERE instituicao_id = %s
                 ORDER BY email_convite
                """,
                (INST,),
            )
            out["aee_matrizes"] = _q(
                cur,
                """
                SELECT condicao_categoria, status, versao
                  FROM public.school_aee_matrizes
                 WHERE instituicao_id = %s
                 ORDER BY condicao_categoria, versao
                """,
                (INST,),
            )
            out["aee_ativo"] = _one(
                cur,
                """
                SELECT COUNT(*)::int AS n
                  FROM public.school_aee_matrizes
                 WHERE instituicao_id = %s AND status = 'ativo'
                """,
                (INST,),
            )
            out["adaptacao_canonica"] = _one(
                cur,
                """
                SELECT COUNT(*)::int AS n
                  FROM public.school_aee_metodologias_canonico
                 WHERE origem = 'adaptacao_canonica' OR origem IS NOT NULL
                """,
            )
            if _table_exists(cur, "school_aee_metodologias_canonico"):
                out["aee_canonico_by_status"] = _q(
                    cur,
                    """
                    SELECT origem, status, COUNT(*)::int AS n
                      FROM public.school_aee_metodologias_canonico
                     GROUP BY origem, status
                     ORDER BY origem, status
                    """,
                )
            out["metodologias_catalogo_n"] = _one(
                cur, "SELECT COUNT(*)::int AS n FROM public.school_metodologias_catalogo WHERE ativo IS NOT FALSE"
            )
            if _table_exists(cur, "school_metodologias_org"):
                out["metodologias_org_custom"] = _q(
                    cur,
                    """
                    SELECT cat.nome
                      FROM public.school_metodologias_org org
                      JOIN public.school_metodologias_catalogo cat
                        ON cat.id = org.metodologia_id_canonica
                     WHERE org.instituicao_id = %s
                       AND NULLIF(trim(coalesce(org.passos_customizados,'')),'') IS NOT NULL
                     ORDER BY cat.nome
                    """,
                    (INST,),
                )
            if _table_exists(cur, "school_calendario_letivo"):
                out["calendario_por_tipo"] = _q(
                    cur,
                    """
                    SELECT tipo, COUNT(*)::int AS n
                      FROM public.school_calendario_letivo
                     WHERE instituicao_id = %s
                     GROUP BY tipo ORDER BY tipo
                    """,
                    (INST,),
                )
            out["keep"] = [_count_for(cur, t) for t in KEEP_TABLES]
            out["delete"] = [_count_for(cur, t) for t in DELETE_TABLES]

            cur.execute(
                """
                SELECT table_name FROM information_schema.columns
                 WHERE table_schema = 'public' AND column_name = 'instituicao_id'
                   AND table_name LIKE 'school_%%'
                 ORDER BY table_name
                """
            )
            all_inst = [r["table_name"] for r in (cur.fetchall() or [])]
            classified = {t["table"] for t in out["keep"] + out["delete"]}
            out["unclassified_with_instituicao_id"] = []
            for t in all_inst:
                if t not in classified:
                    out["unclassified_with_instituicao_id"].append(_count_for(cur, t))

            keep_fp_tables = [
                "school_instituicoes",
                "school_gestores",
                "school_periodos_letivos",
                "school_cursos",
                "school_disciplinas",
                "school_curso_disciplinas",
                "school_metodologias_catalogo",
                "school_metodologias_org",
                "school_metodologia_config",
                "school_aee_matrizes",
                "school_aee_metodologias_canonico",
                "school_aee_metodologias_org",
                "school_bncc_temas_canonico",
                "bncc_habilidades_oficial",
            ]
            out["keep_fingerprints"] = [_fingerprint(cur, t) for t in keep_fp_tables]

    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
