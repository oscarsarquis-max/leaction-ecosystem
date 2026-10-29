#!/usr/bin/env python3
"""121 — apaga desafios/eventos/avisos de teste no RDS B2C via ECS."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boto3

from _ecs_repor_credito import run_python, service_network

CODE = r'''
import json
from psycopg2.extras import RealDictCursor
from db import get_conn
MARKER = "[TESTE VARREDURA 121]"
like = "%" + MARKER + "%"
empty = ["00000000-0000-0000-0000-000000000000"]
out = {}
with get_conn() as conn:
    conn.autocommit = False
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id::text AS id, titulo FROM public.inove_desafios WHERE titulo ILIKE %s", (like,))
        out["desafios_antes"] = [dict(r) for r in cur.fetchall() or []]
        ids = [d["id"] for d in out["desafios_antes"]]
        cur.execute(
            "SELECT id_evento, titulo, desafio_id::text AS desafio_id, status FROM public.inove_agenda_eventos WHERE titulo ILIKE %s OR (desafio_id IS NOT NULL AND desafio_id::text = ANY(%s))",
            (like, ids or empty),
        )
        out["eventos_antes"] = [dict(r) for r in cur.fetchall() or []]
        cur.execute(
            "SELECT id::text AS id, tipo, professor_b2c_id, left(texto,120) AS texto FROM public.inove_avisos_mesa WHERE texto ILIKE %s OR COALESCE(meta_json::text,'') ILIKE %s",
            (like, like),
        )
        out["avisos_antes"] = [dict(r) for r in cur.fetchall() or []]
        if ids:
            cur.execute("DELETE FROM public.inove_desafio_colaboradores WHERE desafio_id::text = ANY(%s)", (ids,))
            out["colabs_deleted"] = cur.rowcount
            cur.execute("DELETE FROM public.inove_kanban_cards WHERE desafio_id::text = ANY(%s) OR titulo ILIKE %s", (ids, like))
            out["cards_deleted"] = cur.rowcount
            cur.execute("DELETE FROM public.inove_agenda_eventos WHERE desafio_id::text = ANY(%s) OR titulo ILIKE %s", (ids, like))
            out["eventos_deleted"] = cur.rowcount
            cur.execute("DELETE FROM public.inove_desafios WHERE id::text = ANY(%s)", (ids,))
            out["desafios_deleted"] = cur.rowcount
        cur.execute(
            "DELETE FROM public.inove_avisos_mesa WHERE texto ILIKE %s OR COALESCE(meta_json::text,'') ILIKE %s",
            (like, like),
        )
        out["avisos_deleted"] = cur.rowcount
        cur.execute("SELECT id::text AS id, titulo FROM public.inove_desafios WHERE titulo ILIKE %s", (like,))
        out["desafios_depois"] = [dict(r) for r in cur.fetchall() or []]
        cur.execute("SELECT COUNT(*)::int AS n FROM public.inove_agenda_eventos WHERE titulo ILIKE %s", (like,))
        out["eventos_depois"] = int((cur.fetchone() or {}).get("n") or 0)
        cur.execute(
            "SELECT COUNT(*)::int AS n FROM public.inove_avisos_mesa WHERE texto ILIKE %s OR COALESCE(meta_json::text,'') ILIKE %s",
            (like, like),
        )
        out["avisos_depois"] = int((cur.fetchone() or {}).get("n") or 0)
        cur.execute("SELECT creditos_ia FROM public.ctdi_clie WHERE id_clie = 21")
        out["creditos_21"] = int((cur.fetchone() or {}).get("creditos_ia") or 0)
    conn.commit()
print(json.dumps(out, default=str, ensure_ascii=False))
'''


def main() -> int:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("taskdef", td, file=sys.stderr)
    run_python(ecs, td, network, CODE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
