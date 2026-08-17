"""Organizational intelligence analyze — Core orchestration only (no OI rules)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.config import get_settings
from app.db import tenant_connection
from app.errors import AppError
from app.modules.oi.client import OrganizationalIntelligenceClient
from app.modules.oi.context_builder import build_organization_context_input
from app.modules.oi.schemas import (
    OrganizationIntelligenceRunOut,
    OrganizationalInsights,
    dump_jsonable,
)
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

_RUN_COLUMNS = """
    id, organization_id, schema_version, request_id, correlation_id,
    generated_at, insights, created_at
"""


def _row_to_run(row) -> OrganizationIntelligenceRunOut:
    envelope = row.insights
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    return OrganizationIntelligenceRunOut(
        id=row.id,
        organization_id=row.organization_id,
        schema_version=row.schema_version,
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        generated_at=row.generated_at,
        insights=OrganizationalInsights.model_validate(envelope),
        created_at=row.created_at,
    )


def persist_intelligence_run(
    ctx: OrgContext,
    envelope: OrganizationalInsights,
) -> OrganizationIntelligenceRunOut:
    """
    Store a successful OI envelope for the OrgContext tenant.

    organization_id always from OrgContext — never from the envelope alone.
    """
    payload = dump_jsonable(envelope)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                INSERT INTO organization_intelligence_runs (
                  organization_id, schema_version, request_id, correlation_id,
                  generated_at, insights
                )
                VALUES (
                  :org, :schema_version, :request_id, :correlation_id,
                  :generated_at, CAST(:insights AS jsonb)
                )
                RETURNING {_RUN_COLUMNS}
                """
            ),
            {
                "org": ctx.organization_id,
                "schema_version": envelope.schema_version,
                "request_id": envelope.request_id,
                "correlation_id": envelope.correlation_id,
                "generated_at": envelope.generated_at,
                "insights": json.dumps(payload),
            },
        ).one()
        conn.commit()
    return _row_to_run(row)


def list_intelligence_runs(
    ctx: OrgContext,
    *,
    limit: int = 50,
) -> list[OrganizationIntelligenceRunOut]:
    orgs_service.require_role(ctx, *_ANALYZE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_RUN_COLUMNS}
                FROM organization_intelligence_runs
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).all()
    return [_row_to_run(r) for r in rows]


def get_intelligence_run(
    ctx: OrgContext,
    run_id: UUID,
) -> OrganizationIntelligenceRunOut:
    orgs_service.require_role(ctx, *_ANALYZE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_RUN_COLUMNS}
                FROM organization_intelligence_runs
                WHERE id = :id
                """
            ),
            {"id": run_id},
        ).first()
    if row is None:
        raise AppError("not_found", "Intelligence run not found", status_code=404)
    return _row_to_run(row)


def analyze_current_organization(
    ctx: OrgContext,
    *,
    client: OrganizationalIntelligenceClient | None = None,
) -> OrganizationalInsights:
    """
    Resolve tenancy → load profile → build OrganizationContextInput → call OI HTTP
    → persist successful envelope → return the same OrganizationalInsights.
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
    result = oi_client.analyze(envelope)
    persist_intelligence_run(ctx, result)
    return result
