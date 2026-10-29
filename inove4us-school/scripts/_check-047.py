#!/usr/bin/env python3
"""Prompt 114 — confirma migration 047 + ids de disciplina (sem senhas)."""
from __future__ import annotations

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
HOMOLOG = "homologador@leaction.com.br"


def main() -> int:
    out: dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT filename, applied_at FROM school_schema_migrations WHERE filename LIKE '047%' ORDER BY filename"
            )
            out["migrations"] = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'school_comunicacoes_eventos'
                  AND column_name IN ('disciplina_id', 'data_hora_inicio', 'data_hora_fim')
                ORDER BY column_name
                """
            )
            out["columns"] = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT d.id, d.nome
                FROM public.school_disciplinas d
                WHERE d.instituicao_id = %s AND d.ativo IS NOT FALSE
                ORDER BY d.nome
                """,
                (INST,),
            )
            out["disciplinas"] = [{"id": str(r["id"]), "nome": r["nome"]} for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT t.id AS turma_id, t.nome AS turma, d.id AS disciplina_id, d.nome AS disciplina, a.ativo
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                  AND lower(v.email_convite) = %s
                ORDER BY t.nome, d.nome
                """,
                (INST, HOMOLOG),
            )
            out["homolog_aloc"] = [
                {
                    "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
                    "turma": r["turma"],
                    "disciplina_id": str(r["disciplina_id"]),
                    "disciplina": r["disciplina"],
                    "ativo": r["ativo"],
                }
                for r in cur.fetchall() or []
            ]
            cur.execute(
                """
                SELECT id, titulo, status, publico_alvo
                FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s
                  AND (titulo LIKE '%%[TESTE VARREDURA 113]%%' OR titulo LIKE '%%[TESTE VARREDURA 114]%%')
                ORDER BY created_at DESC
                """,
                (INST,),
            )
            out["residuos_school"] = [
                {"id": str(r["id"]), "titulo": r["titulo"], "status": r["status"], "publico": r["publico_alvo"]}
                for r in cur.fetchall() or []
            ]
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
