#!/usr/bin/env python3
"""128 — curso_ano do catálogo BNCC Matemática."""
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


def main():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT curso_ano, count(*)::int AS n
                  FROM public.school_bncc_temas_canonico
                 WHERE status = 'aprovado'
                   AND lower(disciplina_nome) = 'matemática'
                 GROUP BY curso_ano
                 ORDER BY curso_ano
                """
            )
            anos = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT habilidade_codigo, tema, curso_ano, left(coalesce(o.texto,''), 140) AS texto
                  FROM public.school_bncc_temas_canonico t
                  JOIN public.bncc_habilidades_oficial o ON o.codigo = t.habilidade_codigo
                 WHERE t.status = 'aprovado'
                   AND lower(t.disciplina_nome) = 'matemática'
                   AND t.curso_ano ILIKE '%9%'
                 ORDER BY t.habilidade_codigo
                 LIMIT 8
                """
            )
            n9 = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT habilidade_codigo, tema, curso_ano, left(coalesce(o.texto,''), 140) AS texto
                  FROM public.school_bncc_temas_canonico t
                  JOIN public.bncc_habilidades_oficial o ON o.codigo = t.habilidade_codigo
                 WHERE t.status = 'aprovado'
                   AND lower(t.disciplina_nome) = 'matemática'
                   AND t.curso_ano ILIKE '%1%série%'
                 ORDER BY t.habilidade_codigo
                 LIMIT 8
                """
            )
            n1 = [dict(r) for r in cur.fetchall()]
    print(json.dumps({"anos": anos, "ano9": n9, "serie1": n1}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
