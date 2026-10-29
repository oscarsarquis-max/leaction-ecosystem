"""Montagem do guia público + contagens seguras (somente PANNE_ENV=demo)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import RuntimeSessionLocal
from app.modules.demo_guide.content import FALLBACK_COUNTS, static_guide_body
from app.modules.identity_organization.tenant_context import apply_tenant_context
from app.seed.ids import seed_uuid

logger = logging.getLogger(__name__)

# Metadados fixos da demo (sem aceitar organization_id do cliente).
# IDs internos só para escopo RLS; nunca serializados na resposta.
_ORG_META: tuple[tuple[str, str, str], ...] = (
    ("panne-demonstracao", "Panne Demonstração", "principal"),
    ("padaria-horizonte-demo", "Padaria Horizonte Demo", "isolamento"),
)

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
    except Exception as exc:
        logger.warning("demo-guide count falhou: %s", type(exc).__name__)
        return None


def _org_id(slug: str) -> UUID:
    return seed_uuid("org", slug)


def _live_counts(session: Session) -> dict[str, Any]:
    orgs: list[dict[str, Any]] = []
    for slug, display_name, role in _ORG_META:
        oid = _org_id(slug)
        # Escopo por tenant (sem desligar RLS — runtime não tem BYPASSRLS).
        apply_tenant_context(session, organization_id=oid, user_id=None)
        counts: dict[str, int | None] = {}
        for key, sql in _COUNT_SQL.items():
            counts[key] = _scalar(session, sql, {"oid": oid})
        counts["perfis_disponiveis"] = 7 if slug == "panne-demonstracao" else None
        orgs.append(
            {
                "slug": slug,
                "display_name": display_name,
                "role": role,
                "counts": counts,
            }
        )

    totals: dict[str, int | None] = {}
    for key in list(_COUNT_SQL) + ["perfis_disponiveis"]:
        vals = [o["counts"].get(key) for o in orgs]
        if key == "perfis_disponiveis":
            totals[key] = 7
        elif any(v is None for v in vals):
            known = [v for v in vals if isinstance(v, int)]
            totals[key] = sum(known) if known and len(known) == len(vals) else None
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
            known = [v for v in live["totals"].values() if isinstance(v, int)]
            if known:
                counts = live
                counts_ok = True
            head = _alembic_head(session)
            session.commit()
        except Exception as exc:
            logger.warning(
                "demo-guide live counts indisponíveis; usando fallback (%s)",
                type(exc).__name__,
            )
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
