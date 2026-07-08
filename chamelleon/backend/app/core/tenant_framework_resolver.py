"""Resolve o framework ativo de um tenant (TenantFramework + fallbacks)."""

from __future__ import annotations

import logging
import uuid

from app.core.rbac.constants import ROLE_LED
from app.database.models import Framework, TenantFramework, TenantUser, db
from app.infrastructure.web_search import normalize_sector_name

logger = logging.getLogger(__name__)


def _active_framework_link(tenant_id: uuid.UUID) -> TenantFramework | None:
    return (
        TenantFramework.query.filter_by(tenant_id=tenant_id, status="active")
        .order_by(TenantFramework.started_at.desc())
        .first()
    )


def _framework_from_link(link: TenantFramework | None) -> Framework | None:
    if not link:
        return None
    framework = db.session.get(Framework, link.framework_id)
    if framework and framework.is_active:
        return framework
    return None


def _ensure_tenant_framework_link(tenant_id: uuid.UUID, framework_id: str) -> Framework | None:
    framework = db.session.get(Framework, framework_id)
    if not framework or not framework.is_active:
        return None

    existing = _active_framework_link(tenant_id)
    if existing and existing.framework_id == framework_id:
        return framework

    if existing:
        existing.status = "inactive"

    db.session.add(
        TenantFramework(
            tenant_id=tenant_id,
            framework_id=framework_id,
            status="active",
        )
    )
    db.session.commit()
    logger.info("Tenant %s vinculado ao framework %s.", tenant_id, framework_id)
    return framework


def resolve_framework_for_tenant(tenant_id: uuid.UUID) -> Framework | None:
    """Retorna framework ativo do tenant; tenta re-vincular se o catálogo foi republicado."""
    framework = _framework_from_link(_active_framework_link(tenant_id))
    if framework:
        return framework

    stale_link = _active_framework_link(tenant_id)
    if stale_link:
        stale_link.status = "inactive"
        db.session.commit()

    active_frameworks = Framework.query.filter_by(is_active=True).order_by(Framework.name).all()
    if not active_frameworks:
        from app.core.bootstrap import ensure_published_framework

        ensure_published_framework()
        active_frameworks = Framework.query.filter_by(is_active=True).order_by(Framework.name).all()
    if not active_frameworks:
        return None

    if len(active_frameworks) == 1:
        return _ensure_tenant_framework_link(tenant_id, active_frameworks[0].id)

    has_lead = (
        TenantUser.query.filter_by(tenant_id=tenant_id, role=ROLE_LED).first() is not None
    )
    if not has_lead:
        return None

    for candidate in active_frameworks:
        if candidate.industry:
            return _ensure_tenant_framework_link(tenant_id, candidate.id)

    return _ensure_tenant_framework_link(tenant_id, active_frameworks[0].id)


def relink_orphan_lead_tenants(framework_id: str, sector: str) -> int:
    """Re-vincula leads sem framework ativo após publicação de um novo catálogo setorial."""
    framework = db.session.get(Framework, framework_id)
    if not framework or not framework.is_active:
        return 0

    sector_norm = normalize_sector_name(sector)
    framework_sector = normalize_sector_name(framework.industry or "")
    if framework_sector and framework_sector != sector_norm:
        return 0

    linked = 0
    seen_tenants: set[uuid.UUID] = set()

    for membership in TenantUser.query.filter_by(role=ROLE_LED).all():
        tenant_id = membership.tenant_id
        if tenant_id in seen_tenants:
            continue
        seen_tenants.add(tenant_id)

        if _framework_from_link(_active_framework_link(tenant_id)):
            continue

        _ensure_tenant_framework_link(tenant_id, framework_id)
        linked += 1

    return linked
