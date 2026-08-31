"""Montagem do guia público + contagens seguras (somente PANNE_ENV=demo)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import RuntimeSessionLocal
from app.modules.demo_guide.content import FALLBACK_COUNTS, static_guide_body

logger = logging.getLogger(__name__)

_ORG_SLUGS = ("panne-demonstracao", "padaria-horizonte-demo")

_COUNT_SQL = {
    "produtos": "SELECT count(*)::int FROM technical_product WHERE organization_id = :oid",
    "produtos_ativos": (
        "SELECT count(*)::int FROM technical_product "
        "WHERE organization_id = :oid AND status = 'active'"
    ),
    "produtos_inativos": (
        "SELECT count(*)::int FROM technical_product "
        "WHERE organization_id = :oid AND status = 'inactive'"
    ),
    "ingredientes": "SELECT count(*)::int FROM ingredient WHERE organization_id = :oid",
    "receitas": "SELECT count(*)::int FROM formulation WHERE organization_id = :oid",
    "planos": "SELECT count(*)::int FROM production_plan WHERE organization_id = :oid",
    "ordens": "SELECT count(*)::int FROM production_order WHERE organization_id = :oid",
    "fornecedores": "SELECT count(*)::int FROM supplier WHERE organization_id = :oid",
    "lotes": "SELECT count(*)::int FROM inventory_lot WHERE organization_id = :oid",
    "saldos": "SELECT count(*)::int FROM inventory_balance WHERE organization_id = :oid",
    "movimentos": "SELECT count(*)::int FROM inventory_movement WHERE organization_id = :oid",
    "entradas_fiscais": (
        "SELECT count(*)::int FROM fiscal_inbound_document WHERE organization_id = :oid"
    ),
}


def _scalar(session: Session, sql: str, params: dict[str, Any]) -> int | None:
    try:
        return int(session.execute(text(sql), params).scalar_one())
    except Exception:
        logger.warning("demo-guide count falhou sql=%s", sql.split()[3] if sql else "?")
        return None


def _live_counts(session: Session) -> dict[str, Any] | None:
    # Leitura agregada só na demo; sem organization_id do cliente.
    session.execute(text("SELECT set_config('row_security', 'off', true)"))
    orgs: list[dict[str, Any]] = []
    for slug in _ORG_SLUGS:
        row = session.execute(
            text(
                "SELECT id, display_name, slug FROM organization WHERE slug = :slug LIMIT 1"
            ),
            {"slug": slug},
        ).mappings().first()
        if not row:
            orgs.append(
                {
                    "slug": slug,
                    "display_name": slug,
                    "role": "principal" if slug.startswith("panne") else "isolamento",
                    "counts": {k: None for k in _COUNT_SQL},
                }
            )
            continue
        oid = row["id"]
        counts: dict[str, int | None] = {}
        for key, sql in _COUNT_SQL.items():
            counts[key] = _scalar(session, sql, {"oid": oid})
        counts["perfis_disponiveis"] = 7 if slug == "panne-demonstracao" else None
        orgs.append(
            {
                "slug": str(row["slug"]),
                "display_name": str(row["display_name"] or row["slug"]),
                "role": "principal" if slug == "panne-demonstracao" else "isolamento",
                "counts": counts,
            }
        )

    totals: dict[str, int | None] = {}
    for key in list(_COUNT_SQL) + ["perfis_disponiveis"]:
        vals = [o["counts"].get(key) for o in orgs]
        if any(v is None for v in vals) and key != "perfis_disponiveis":
            # Se alguma org falhou nessa métrica, total fica Não informado.
            known = [v for v in vals if isinstance(v, int)]
            totals[key] = sum(known) if known and len(known) == len(vals) else None
        elif key == "perfis_disponiveis":
            totals[key] = 7
        else:
            totals[key] = sum(int(v) for v in vals if isinstance(v, int))

    return {
        "source": "live",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": None,
        "organizations": orgs,
        "totals": totals,
    }


def _alembic_head(session: Session) -> str | None:
    try:
        session.execute(text("SELECT set_config('row_security', 'off', true)"))
        ver = session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        return str(ver) if ver else None
    except Exception:
        return None


def resolve_demo_guide() -> dict[str, Any] | None:
    """
    Retorna o guia somente em PANNE_ENV=demo.
    Em outros ambientes o caller deve responder 404.
    """
    settings = get_settings()
    if settings.env != "demo":
        return None

    body = static_guide_body()
    counts = dict(FALLBACK_COUNTS)
    head: str | None = None
    counts_ok = False

    if RuntimeSessionLocal is not None:
        session = RuntimeSessionLocal()
        try:
            live = _live_counts(session)
            if live:
                counts = live
                counts_ok = True
            head = _alembic_head(session)
            session.commit()
        except Exception:
            logger.warning("demo-guide live counts indisponíveis; usando fallback")
            session.rollback()
        finally:
            session.close()

    body["counts"] = counts
    body["counts_available"] = counts_ok
    body["generated_at"] = datetime.now(timezone.utc).isoformat()
    body["version"] = {
        **body.get("version", {}),
        "api_version": settings.versao,
        "environment": settings.env,
        "migration_head_human": (
            f"Base na revisão {head}" if head else "Revisão de base não informada"
        ),
        "migration_head_detail": head,
        "demo_anchor_date": settings.demo_anchor_date or "2026-08-24",
    }
    body["source"] = "live" if counts_ok else "fallback"
    return body
