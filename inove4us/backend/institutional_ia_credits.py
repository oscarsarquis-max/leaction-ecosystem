"""Pool de crédito de IA por licença institucional (prompt 98).

Uma concessão por professor×instituição. Re-sync de alocação não duplica.
"""
from __future__ import annotations

import os
from typing import Any

from psycopg2.extras import RealDictCursor

from db import get_conn

# Ponto de partida do piloto (Oscar, 2026-09-08). Override: INOVE_IA_INSTITUTIONAL_POOL.
CREDITO_IA_INSTITUTIONAL_POOL = max(
    0,
    int(os.environ.get("INOVE_IA_INSTITUTIONAL_POOL") or "50"),
)
ORIGEM_LICENSE_POOL = "institutional_license_pool"

_ensured = False


def _as_uuid(value: Any) -> str | None:
    from uuid import UUID

    if value is None or value == "":
        return None
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def ensure_credito_ia_concessoes_table() -> None:
    global _ensured
    if _ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.inove_credito_ia_concessoes (
                    id              BIGSERIAL PRIMARY KEY,
                    id_clie         INTEGER NOT NULL,
                    instituicao_id  UUID NOT NULL,
                    origem          VARCHAR(64) NOT NULL,
                    credits         INTEGER NOT NULL,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (id_clie, instituicao_id, origem)
                )
                """
            )
            cur.execute(
                """
                COMMENT ON TABLE public.inove_credito_ia_concessoes IS
                  'Concessão idempotente de pool de IA por licença institucional (professor×escola).'
                """
            )
    _ensured = True


def grant_institutional_ia_pool(
    id_clie: int,
    instituicao_id: str | None,
    *,
    origem: str = ORIGEM_LICENSE_POOL,
) -> dict[str, Any]:
    """Credita o pool se a instituição existe e o professor ainda não recebeu.

    Idempotente: UNIQUE (id_clie, instituicao_id, origem).
    """
    ensure_credito_ia_concessoes_table()
    inst = _as_uuid(instituicao_id)
    if not inst:
        return {
            "granted": False,
            "idempotent": False,
            "reason": "instituicao_id_missing",
            "credits_added": 0,
        }
    pool = int(CREDITO_IA_INSTITUTIONAL_POOL)
    if pool <= 0:
        return {
            "granted": False,
            "idempotent": False,
            "reason": "pool_disabled",
            "credits_added": 0,
        }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.inove_credito_ia_concessoes
                    (id_clie, instituicao_id, origem, credits)
                VALUES (%s, %s::uuid, %s, %s)
                ON CONFLICT (id_clie, instituicao_id, origem) DO NOTHING
                RETURNING id
                """,
                (int(id_clie), inst, origem, pool),
            )
            inserted = cur.fetchone()
            if not inserted:
                cur.execute(
                    """
                    SELECT creditos_ia
                      FROM public.ctdi_clie
                     WHERE id_clie = %s
                    """,
                    (int(id_clie),),
                )
                row = cur.fetchone() or {}
                return {
                    "granted": False,
                    "idempotent": True,
                    "reason": "already_granted",
                    "credits_added": 0,
                    "creditos_ia": int(row.get("creditos_ia") or 0),
                    "pool": pool,
                    "instituicao_id": inst,
                }

            cur.execute(
                """
                UPDATE public.ctdi_clie
                   SET creditos_ia = creditos_ia + %s
                 WHERE id_clie = %s
                RETURNING creditos_ia
                """,
                (pool, int(id_clie)),
            )
            saldo = cur.fetchone()
            if not saldo:
                cur.execute(
                    """
                    DELETE FROM public.inove_credito_ia_concessoes
                     WHERE id = %s
                    """,
                    (int(inserted["id"]),),
                )
                return {
                    "granted": False,
                    "idempotent": False,
                    "reason": "cliente_not_found",
                    "credits_added": 0,
                }
            novo = int(saldo["creditos_ia"])
    print(
        f"[ia-pool] grant id_clie={id_clie} inst={inst} +{pool} -> saldo={novo}",
        flush=True,
    )
    return {
        "granted": True,
        "idempotent": False,
        "credits_added": pool,
        "creditos_ia": novo,
        "pool": pool,
        "instituicao_id": inst,
        "origem": origem,
    }


def backfill_linked_professors() -> dict[str, Any]:
    """Correção pontual: professores já vinculados sem concessão do pool."""
    ensure_credito_ia_concessoes_table()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, instituicao_b2b_id
                  FROM public.ctdi_clie
                 WHERE instituicao_b2b_id IS NOT NULL
                 ORDER BY id_clie
                """
            )
            rows = [dict(r) for r in (cur.fetchall() or [])]

    granted = 0
    skipped = 0
    results: list[dict[str, Any]] = []
    for row in rows:
        out = grant_institutional_ia_pool(
            int(row["id_clie"]),
            str(row["instituicao_b2b_id"]),
        )
        if out.get("granted"):
            granted += 1
        else:
            skipped += 1
        results.append(
            {
                "id_clie": int(row["id_clie"]),
                "granted": bool(out.get("granted")),
                "idempotent": bool(out.get("idempotent")),
                "credits_added": out.get("credits_added"),
                "creditos_ia": out.get("creditos_ia"),
            }
        )
    return {
        "ok": True,
        "candidates": len(rows),
        "granted": granted,
        "skipped": skipped,
        "pool": int(CREDITO_IA_INSTITUTIONAL_POOL),
        "results": results,
    }


if __name__ == "__main__":
    import json
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "backfill").strip().lower()
    if cmd == "backfill":
        print(json.dumps(backfill_linked_professors(), ensure_ascii=False, indent=2, default=str))
    else:
        raise SystemExit("uso: python institutional_ia_credits.py backfill")
