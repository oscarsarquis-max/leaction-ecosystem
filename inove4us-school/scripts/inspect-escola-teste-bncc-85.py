#!/usr/bin/env python3
"""Lista cursos/disciplinas/turmas da Escola Teste — sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"


def main() -> int:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT c.nome AS curso, c.nivel, t.nome AS turma, t.serie_ano
                FROM public.school_cursos c
                JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                LEFT JOIN public.school_turmas t ON t.curso_id = c.id
                WHERE p.instituicao_id = %s
                ORDER BY c.nome, t.nome
                """,
                (INST,),
            )
            cursos = [dict(r) for r in cur.fetchall()]
            cur.execute(
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
            discs = [dict(r) for r in cur.fetchall()]
    print(json.dumps({"cursos_turmas": cursos, "disciplinas": discs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
