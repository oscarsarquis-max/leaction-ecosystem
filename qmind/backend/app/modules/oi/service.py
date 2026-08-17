"""Organizational intelligence analyze — Core orchestration only (no OI rules)."""

from __future__ import annotations

from app.auth.context import OrgContext
from app.config import get_settings
from app.modules.oi.client import OrganizationalIntelligenceClient
from app.modules.oi.context_builder import build_organization_context_input
from app.modules.oi.schemas import OrganizationalInsights
from app.modules.orgs import service as orgs_service

# Same read policy as GET /organizations/current/profile (analysis of current org).
_ANALYZE_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "reader",
    "action_owner",
    "platform_admin",
)


def analyze_current_organization(
    ctx: OrgContext,
    *,
    client: OrganizationalIntelligenceClient | None = None,
) -> OrganizationalInsights:
    """
    Resolve tenancy → load profile → build OrganizationContextInput → call OI HTTP.

    Does not persist insights. organization_id always from OrgContext.
    """
    orgs_service.require_role(ctx, *_ANALYZE_ROLES)
    profile = orgs_service.get_or_create_organization_profile(ctx)
    settings = get_settings()
    envelope = build_organization_context_input(
        profile,
        core_organization_id=ctx.organization_id,
        environment=settings.environment if settings.environment != "dev" else "local",
    )
    oi_client = client or OrganizationalIntelligenceClient(settings)
    return oi_client.analyze(envelope)
