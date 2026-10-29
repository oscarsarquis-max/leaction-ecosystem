#!/usr/bin/env python3
"""127 — inspecionar espelho de aula + curadoria no School."""
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


def main():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, origem_plano_b2c_id::text, tipo_aula, status,
                       metodologia_catalogo_id::text, left(coalesce(conteudo_resumo,''), 80) AS resumo,
                       desafio_grupo_id::text, turma_id::text, created_at,
                       mesa_payload_json->>'has_teacher_adaptations' AS has_adapt,
                       left(coalesce(mesa_payload_json->>'teacher_adaptation_text',''), 120) AS adapt
                  FROM public.school_planos_aula_espelhados
                 WHERE instituicao_id = %s
                 ORDER BY created_at DESC
                 LIMIT 15
                """,
                (INST,),
            )
            planos = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT count(*) AS n FROM public.school_curadoria_metodologias
                 WHERE instituicao_id = %s
                """,
                (INST,),
            )
            n_c = cur.fetchone()["n"]
            cur.execute(
                """
                SELECT count(*) AS n FROM public.school_avisos_mesa
                 WHERE instituicao_id = %s AND ativo
                """,
                (INST,),
            )
            n_a = cur.fetchone()["n"]
    print(json.dumps({"planos": planos, "n_curadoria": n_c, "n_avisos": n_a}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
