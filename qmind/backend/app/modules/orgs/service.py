from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext, Principal
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.orgs.schemas import (
    MembershipOut,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationOut,
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
