from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext, Principal
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.orgs.schemas import (
    MembershipOut,
    OrgMemberOut,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationOut,
    OrganizationProfileOut,
    OrganizationProfilePatch,
)

_PROFILE_COLUMNS = """
    organization_id, trade_name, legal_name, summary, industry,
    business_model, employee_range, unit_count, certification_status,
    quality_structure, created_at, updated_at
"""


def _row_to_profile(row) -> OrganizationProfileOut:
    return OrganizationProfileOut(
        organization_id=row.organization_id,
        trade_name=row.trade_name or "",
        legal_name=row.legal_name or "",
        summary=row.summary or "",
        industry=row.industry or "",
        business_model=row.business_model or "",
        employee_range=row.employee_range or "",
        unit_count=row.unit_count,
        certification_status=row.certification_status or "unknown",
        quality_structure=row.quality_structure or "unknown",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_organization(principal: Principal, payload: OrganizationCreate) -> OrganizationDetailOut:
    with admin_connection() as conn:
        org = conn.execute(
            text(
                """
                INSERT INTO organizations (name, status, timezone)
                VALUES (:name, 'active', :tz)
                RETURNING id, name, status, timezone, created_at
                """
            ),
            {"name": payload.name.strip(), "tz": payload.timezone},
        ).one()
        mem = conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['org_admin']::text[], 'active')
                RETURNING id, organization_id, roles, status
                """
            ),
            {"org": org.id, "user": principal.user_id},
        ).one()
        conn.commit()

    return OrganizationDetailOut(
        organization=OrganizationOut(
            id=org.id,
            name=org.name,
            status=org.status,
            timezone=org.timezone,
            created_at=org.created_at,
        ),
        membership=MembershipOut(
            id=mem.id,
            organization_id=mem.organization_id,
            organization_name=org.name,
            roles=list(mem.roles),
            status=mem.status,
        ),
    )


def list_my_memberships(principal: Principal) -> list[MembershipOut]:
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT m.id, m.organization_id, o.name AS organization_name,
                       m.roles, m.status
                FROM memberships m
                JOIN organizations o ON o.id = m.organization_id
                WHERE m.user_id = :user
                  AND m.status = 'active'
                ORDER BY o.name
                """
            ),
            {"user": principal.user_id},
        ).all()
    return [
        MembershipOut(
            id=r.id,
            organization_id=r.organization_id,
            organization_name=r.organization_name,
            roles=list(r.roles),
            status=r.status,
        )
        for r in rows
    ]


def list_current_org_members(ctx: OrgContext) -> list[OrgMemberOut]:
    """Membros ativos da org atual — para equipe sem digitar UUID."""
    require_role(ctx, "org_admin", "consultant_auditor", "quality_manager", "process_owner", "reader")
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT m.id AS membership_id, u.email, u.display_name, m.roles, m.status
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.organization_id = :org
                  AND m.status = 'active'
                ORDER BY coalesce(u.display_name, u.email)
                """
            ),
            {"org": ctx.organization_id},
        ).all()
    return [
        OrgMemberOut(
            membership_id=r.membership_id,
            email=r.email,
            display_name=r.display_name,
            roles=list(r.roles),
            status=r.status,
        )
        for r in rows
    ]


def get_current_organization(ctx: OrgContext) -> OrganizationOut:
    """Read via qmind_app + RLS to prove tenant path."""
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name, status, timezone, created_at
                FROM organizations
                WHERE id = :id
                """
            ),
            {"id": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Organization not found", status_code=404)
    return OrganizationOut(
        id=row.id,
        name=row.name,
        status=row.status,
        timezone=row.timezone,
        created_at=row.created_at,
    )


def require_role(ctx: OrgContext, *allowed: str) -> None:
    if not set(ctx.roles).intersection(allowed):
        raise AppError("forbidden", "Insufficient role for this operation", status_code=403)


def get_or_create_organization_profile(ctx: OrgContext) -> OrganizationProfileOut:
    """Master data 1:1 — creates empty defaults on first GET (audit-plan style)."""
    require_role(
        ctx,
        "org_admin",
        "consultant_auditor",
        "quality_manager",
        "process_owner",
        "reader",
        "action_owner",
        "platform_admin",
    )
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_PROFILE_COLUMNS}
                FROM organization_profiles
                WHERE organization_id = :org
                """
            ),
            {"org": ctx.organization_id},
        ).first()
        if row is None:
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO organization_profiles (organization_id)
                    VALUES (:org)
                    ON CONFLICT (organization_id) DO UPDATE
                      SET updated_at = organization_profiles.updated_at
                    RETURNING {_PROFILE_COLUMNS}
                    """
                ),
                {"org": ctx.organization_id},
            ).one()
            conn.commit()
    return _row_to_profile(row)


def patch_organization_profile(
    ctx: OrgContext, payload: OrganizationProfilePatch
) -> OrganizationProfileOut:
    """Partial upsert for current org only — organization_id is never client-supplied."""
    require_role(ctx, "org_admin", "consultant_auditor", "quality_manager", "platform_admin")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return get_or_create_organization_profile(ctx)

    # Ensure row exists, then apply only provided fields.
    get_or_create_organization_profile(ctx)

    sets = [f"{col} = :{col}" for col in data]
    sets.append("updated_at = now()")
    params = {"org": ctx.organization_id, **data}
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE organization_profiles
                SET {", ".join(sets)}
                WHERE organization_id = :org
                RETURNING {_PROFILE_COLUMNS}
                """
            ),
            params,
        ).first()
        if row is None:
            raise AppError("not_found", "Organization profile not found", status_code=404)
        conn.commit()
    return _row_to_profile(row)
