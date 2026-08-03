"""Assessment use cases — machine: draft → plan → planned (domain-docs-v0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.assessments.schemas import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentPlanResult,
    ScopeItemIn,
)
from app.modules.orgs.service import require_role

_PLAN_ROLES = ("org_admin", "consultant_auditor", "quality_manager")


def _row_to_out(row) -> AssessmentOut:
    return AssessmentOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_model_id=row.assessment_model_id,
        standard_version_id=row.standard_version_id,
        maturity_model_id=row.maturity_model_id,
        type=row.type,
        status=row.status,
        lead_membership_id=row.lead_membership_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _assert_catalog_refs(assessment_model_id: UUID, standard_version_id: UUID) -> None:
    with admin_connection() as conn:
        m = conn.execute(
            text("SELECT id FROM assessment_models WHERE id = :id AND status = 'active'"),
            {"id": assessment_model_id},
        ).first()
        sv = conn.execute(
            text("SELECT id FROM standard_versions WHERE id = :id AND status = 'active'"),
            {"id": standard_version_id},
        ).first()
    if m is None or sv is None:
        raise AppError("invalid_catalog_ref", "Unknown or inactive assessment model/version", status_code=400)


def create_draft(ctx: OrgContext, payload: AssessmentCreate) -> AssessmentOut:
    require_role(ctx, *_PLAN_ROLES)
    _assert_catalog_refs(payload.assessment_model_id, payload.standard_version_id)

    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO assessments (
                  organization_id, assessment_model_id, standard_version_id,
                  maturity_model_id, type, status, lead_membership_id, created_by, updated_by
                ) VALUES (
                  :org, :model, :sv, :maturity, :type, 'draft', :lead, :user, :user
                )
                RETURNING id, organization_id, assessment_model_id, standard_version_id,
                          maturity_model_id, type, status, lead_membership_id,
                          created_at, updated_at
                """
            ),
            {
                "org": ctx.organization_id,
                "model": payload.assessment_model_id,
                "sv": payload.standard_version_id,
                "maturity": payload.maturity_model_id,
                "type": payload.type,
                "lead": ctx.membership_id,
                "user": ctx.principal.user_id,
            },
        ).one()

        conn.execute(
            text(
                """
                INSERT INTO assessment_team_members (
                  organization_id, assessment_id, membership_id, team_role
                ) VALUES (:org, :assess, :mem, 'lead')
                """
            ),
            {"org": ctx.organization_id, "assess": row.id, "mem": ctx.membership_id},
        )

        for item in payload.scope:
            _insert_scope(conn, ctx.organization_id, row.id, item)

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.create",
            resource_type="assessment",
            resource_id=row.id,
            from_status=None,
            to_status="draft",
            metadata={"type": payload.type},
        )
        conn.commit()
        return _row_to_out(row)


def _insert_scope(conn, organization_id: UUID, assessment_id: UUID, item: ScopeItemIn) -> None:
    conn.execute(
        text(
            """
            INSERT INTO assessment_scopes (
              organization_id, assessment_id, org_process_id, requirement_id
            ) VALUES (:org, :assess, :proc, :req)
            """
        ),
        {
            "org": organization_id,
            "assess": assessment_id,
            "proc": item.org_process_id,
            "req": item.requirement_id,
        },
    )


def list_assessments(ctx: OrgContext) -> list[AssessmentOut]:
    require_role(
        ctx,
        "org_admin",
        "consultant_auditor",
        "quality_manager",
        "process_owner",
        "reader",
    )
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_model_id, standard_version_id,
                       maturity_model_id, type, status, lead_membership_id,
                       created_at, updated_at
                FROM assessments
                ORDER BY created_at DESC
                """
            )
        ).all()
    return [_row_to_out(r) for r in rows]


def transition_plan(ctx: OrgContext, assessment_id: UUID) -> AssessmentPlanResult:
    """Event `plan`: draft → planned (001_State_Machines.md)."""
    require_role(ctx, *_PLAN_ROLES)

    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_model_id, standard_version_id,
                       maturity_model_id, type, status, lead_membership_id,
                       created_at, updated_at
                FROM assessments
                WHERE id = :id
                FOR UPDATE
                """
            ),
            {"id": assessment_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"plan requires status draft (current={row.status})",
                status_code=409,
            )

        scope_n = conn.execute(
            text(
                "SELECT count(*) FROM assessment_scopes WHERE assessment_id = :id"
            ),
            {"id": assessment_id},
        ).scalar_one()
        if scope_n < 1:
            raise AppError(
                "plan_guard_scope",
                "plan requires at least one scope item (process or requirement)",
                status_code=422,
            )

        team_n = conn.execute(
            text(
                "SELECT count(*) FROM assessment_team_members WHERE assessment_id = :id"
            ),
            {"id": assessment_id},
        ).scalar_one()
        if team_n < 1 or row.lead_membership_id is None:
            raise AppError(
                "plan_guard_team",
                "plan requires minimum team (lead membership)",
                status_code=422,
            )

        if row.assessment_model_id is None or row.standard_version_id is None:
            raise AppError(
                "plan_guard_model",
                "plan requires assessment model and standard version",
                status_code=422,
            )

        updated = conn.execute(
            text(
                """
                UPDATE assessments
                SET status = 'planned', updated_at = now(), updated_by = :user
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING id, organization_id, assessment_model_id, standard_version_id,
                          maturity_model_id, type, status, lead_membership_id,
                          created_at, updated_at
                """
            ),
            {
                "id": assessment_id,
                "org": ctx.organization_id,
                "user": ctx.principal.user_id,
            },
        ).one()

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.plan",
            resource_type="assessment",
            resource_id=assessment_id,
            from_status="draft",
            to_status="planned",
        )
        conn.commit()

    return AssessmentPlanResult(
        assessment=_row_to_out(updated),
        from_status="draft",
        to_status="planned",
        event="plan",
    )
