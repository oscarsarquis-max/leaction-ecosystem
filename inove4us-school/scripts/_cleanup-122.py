#!/usr/bin/env python3
"""122 — limpa curadoria, planos e avisos de teste no School."""
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
MARKER = "[TESTE VARREDURA 122]"
STATE = Path("/tmp/scan-122-state.json")


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    like = "%" + MARKER + "%"
    origens = [x for x in (st.get("d1"), st.get("d2"), st.get("d3")) if x]
    out = {"origens": origens}
    with get_conn() as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS id, status_analise
                FROM public.school_curadoria_metodologias
                WHERE instituicao_id = %s AND sugestao_professor_json::text ILIKE %s
                """,
                (INST, like),
            )
            out["curadoria_antes"] = [dict(r) for r in cur.fetchall() or []]
            ids_c = [r["id"] for r in out["curadoria_antes"]]
            if ids_c:
                cur.execute(
                    "DELETE FROM public.school_curadoria_metodologias WHERE id::text = ANY(%s)",
                    (ids_c,),
                )
                out["curadoria_deleted"] = cur.rowcount
            cur.execute(
                """
                SELECT id::text AS id, origem_plano_b2c_id::text AS origem
                FROM public.school_planos_aula_espelhados
                WHERE instituicao_id = %s
                  AND (
                    (origem_plano_b2c_id IS NOT NULL AND origem_plano_b2c_id::text = ANY(%s))
                    OR COALESCE(conteudo_resumo, '') ILIKE %s
                    OR COALESCE(mesa_payload_json::text, '') ILIKE %s
                  )
                """,
                (INST, origens or ["00000000-0000-0000-0000-000000000000"], like, like),
            )
            planos = [dict(r) for r in cur.fetchall() or []]
            out["planos_antes"] = planos
            pids = [p["id"] for p in planos]
            if pids:
                cur.execute(
                    "DELETE FROM public.school_planos_aula_espelhados WHERE id::text = ANY(%s)",
                    (pids,),
                )
                out["planos_deleted"] = cur.rowcount
            cur.execute(
                """
                SELECT id::text AS id FROM public.school_avisos_mesa
                WHERE instituicao_id = %s AND texto ILIKE %s
                """,
                (INST, like),
            )
            avisos = [dict(r) for r in cur.fetchall() or []]
            out["avisos_antes"] = avisos
            aids = [a["id"] for a in avisos]
            if aids:
                cur.execute(
                    "DELETE FROM public.school_avisos_mesa WHERE id::text = ANY(%s)",
                    (aids,),
                )
                out["avisos_deleted"] = cur.rowcount
            cur.execute(
                "SELECT count(*)::int AS n FROM public.school_curadoria_metodologias WHERE instituicao_id = %s AND sugestao_professor_json::text ILIKE %s",
                (INST, like),
            )
            out["curadoria_depois"] = int((cur.fetchone() or {}).get("n") or 0)
            cur.execute(
                "SELECT count(*)::int AS n FROM public.school_avisos_mesa WHERE instituicao_id = %s AND texto ILIKE %s",
                (INST, like),
            )
            out["avisos_depois"] = int((cur.fetchone() or {}).get("n") or 0)
        conn.commit()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
