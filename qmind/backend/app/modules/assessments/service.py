"""Assessment operational slice — domain-docs-v0 state machine §2."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.assessments.schemas import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentTransitionResult,
    ScopeItemIn,
    ScopeOut,
    TeamMemberIn,
    TeamMemberOut,
)
from app.modules.orgs.service import require_role

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")
_CANCEL_ROLES = ("org_admin", "quality_manager", "consultant_auditor")
_SCOPE_EDITABLE = frozenset({"draft"})
_TEAM_EDITABLE = frozenset({"draft"})


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
        started_at=getattr(row, "started_at", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_assessment(conn: Connection, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, organization_id, assessment_model_id, standard_version_id,
                   maturity_model_id, type, status, lead_membership_id, started_at,
                   created_at, updated_at
            FROM assessments
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": assessment_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Assessment not found", status_code=404)
    return row


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


def _count_approved_findings(conn: Connection, assessment_id: UUID) -> int:
    return conn.execute(
        text(
            """
            SELECT count(*) FROM findings
            WHERE assessment_id = :id AND status = 'approved'
            """
        ),
        {"id": assessment_id},
    ).scalar_one()


def _count_approved_evidence(conn: Connection, assessment_id: UUID) -> int:
    return conn.execute(
        text(
            """
            SELECT count(*) FROM evidences
            WHERE assessment_id = :id AND status = 'approved'
            """
        ),
        {"id": assessment_id},
    ).scalar_one()


def _count_completed_interviews(conn: Connection, assessment_id: UUID) -> int:
    return conn.execute(
        text(
            """
            SELECT count(*) FROM interviews
            WHERE assessment_id = :id AND status = 'completed'
            """
        ),
        {"id": assessment_id},
    ).scalar_one()


def _require_editable(status: str, allowed: frozenset[str], what: str) -> None:
    if status not in allowed:
        raise AppError(
            "mutation_blocked",
            f"{what} mutations only allowed in status {sorted(allowed)} (current={status})",
            status_code=409,
        )


def create_draft(ctx: OrgContext, payload: AssessmentCreate) -> AssessmentOut:
    require_role(ctx, *_MUTATE_ROLES)
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
                          maturity_model_id, type, status, lead_membership_id, started_at,
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
            _insert_scope(conn, ctx, row.id, item)

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.create",
            resource_type="assessment",
            resource_id=row.id,
            to_status="draft",
            metadata={"type": payload.type},
        )
        conn.commit()
        return _row_to_out(row)


def _insert_scope(conn: Connection, ctx: OrgContext, assessment_id: UUID, item: ScopeItemIn) -> UUID:
    row = conn.execute(
        text(
            """
            INSERT INTO assessment_scopes (
              organization_id, assessment_id, org_process_id, requirement_id
            ) VALUES (:org, :assess, :proc, :req)
            RETURNING id
            """
        ),
        {
            "org": ctx.organization_id,
            "assess": assessment_id,
            "proc": item.org_process_id,
            "req": item.requirement_id,
        },
    ).one()
    return row.id


def list_assessments(ctx: OrgContext) -> list[AssessmentOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_model_id, standard_version_id,
                       maturity_model_id, type, status, lead_membership_id, started_at,
                       created_at, updated_at
                FROM assessments
                ORDER BY created_at DESC
                """
            )
        ).all()
    return [_row_to_out(r) for r in rows]


def get_assessment(ctx: OrgContext, assessment_id: UUID) -> AssessmentOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_assessment(conn, ctx.organization_id, assessment_id)
    return _row_to_out(row)


# --- Scope CRUD (draft only) ---


def list_scopes(ctx: OrgContext, assessment_id: UUID) -> list[ScopeOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _lock_assessment(conn, ctx.organization_id, assessment_id)
        rows = conn.execute(
            text(
                """
                SELECT id, assessment_id, org_process_id, requirement_id, created_at
                FROM assessment_scopes
                WHERE assessment_id = :id
                ORDER BY created_at
                """
            ),
            {"id": assessment_id},
        ).all()
    return [
        ScopeOut(
            id=r.id,
            assessment_id=r.assessment_id,
            org_process_id=r.org_process_id,
            requirement_id=r.requirement_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


def add_scope(ctx: OrgContext, assessment_id: UUID, item: ScopeItemIn) -> ScopeOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _require_editable(assess.status, _SCOPE_EDITABLE, "Scope")
        scope_id = _insert_scope(conn, ctx, assessment_id, item)
        row = conn.execute(
            text(
                """
                SELECT id, assessment_id, org_process_id, requirement_id, created_at
                FROM assessment_scopes WHERE id = :id
                """
            ),
            {"id": scope_id},
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.scope.add",
            resource_type="assessment_scope",
            resource_id=scope_id,
            metadata={
                "assessment_id": str(assessment_id),
                "org_process_id": str(item.org_process_id) if item.org_process_id else None,
                "requirement_id": str(item.requirement_id) if item.requirement_id else None,
            },
        )
        conn.commit()
    return ScopeOut(
        id=row.id,
        assessment_id=row.assessment_id,
        org_process_id=row.org_process_id,
        requirement_id=row.requirement_id,
        created_at=row.created_at,
    )


def delete_scope(ctx: OrgContext, assessment_id: UUID, scope_id: UUID) -> None:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _require_editable(assess.status, _SCOPE_EDITABLE, "Scope")
        deleted = conn.execute(
            text(
                """
                DELETE FROM assessment_scopes
                WHERE id = :sid AND assessment_id = :aid AND organization_id = :org
                RETURNING id
                """
            ),
            {"sid": scope_id, "aid": assessment_id, "org": ctx.organization_id},
        ).first()
        if deleted is None:
            raise AppError("not_found", "Scope item not found", status_code=404)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.scope.delete",
            resource_type="assessment_scope",
            resource_id=scope_id,
            metadata={"assessment_id": str(assessment_id)},
        )
        conn.commit()


# --- Team members (draft only) ---


def list_team(ctx: OrgContext, assessment_id: UUID) -> list[TeamMemberOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _lock_assessment(conn, ctx.organization_id, assessment_id)
        rows = conn.execute(
            text(
                """
                SELECT id, assessment_id, membership_id, team_role, created_at
                FROM assessment_team_members
                WHERE assessment_id = :id
                ORDER BY created_at
                """
            ),
            {"id": assessment_id},
        ).all()
    return [
        TeamMemberOut(
            id=r.id,
            assessment_id=r.assessment_id,
            membership_id=r.membership_id,
            team_role=r.team_role,
            created_at=r.created_at,
        )
        for r in rows
    ]


def add_team_member(ctx: OrgContext, assessment_id: UUID, payload: TeamMemberIn) -> TeamMemberOut:
    require_role(ctx, *_MUTATE_ROLES)
    with admin_connection() as admin:
        mem = admin.execute(
            text(
                """
                SELECT id FROM memberships
                WHERE id = :mid AND organization_id = :org AND status = 'active'
                """
            ),
            {"mid": payload.membership_id, "org": ctx.organization_id},
        ).first()
    if mem is None:
        raise AppError("invalid_membership", "Membership not active in this organization", status_code=400)

    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _require_editable(assess.status, _TEAM_EDITABLE, "Team")
        try:
            row = conn.execute(
                text(
                    """
                    INSERT INTO assessment_team_members (
                      organization_id, assessment_id, membership_id, team_role
                    ) VALUES (:org, :assess, :mem, :role)
                    RETURNING id, assessment_id, membership_id, team_role, created_at
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "assess": assessment_id,
                    "mem": payload.membership_id,
                    "role": payload.team_role,
                },
            ).one()
        except Exception as exc:
            raise AppError(
                "team_conflict",
                "Membership already on the assessment team",
                status_code=409,
            ) from exc
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.team.add",
            resource_type="assessment_team_member",
            resource_id=row.id,
            metadata={
                "assessment_id": str(assessment_id),
                "membership_id": str(payload.membership_id),
            },
        )
        conn.commit()
    return TeamMemberOut(
        id=row.id,
        assessment_id=row.assessment_id,
        membership_id=row.membership_id,
        team_role=row.team_role,
        created_at=row.created_at,
    )


def remove_team_member(ctx: OrgContext, assessment_id: UUID, member_row_id: UUID) -> None:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _require_editable(assess.status, _TEAM_EDITABLE, "Team")
        row = conn.execute(
            text(
                """
                SELECT id, membership_id FROM assessment_team_members
                WHERE id = :id AND assessment_id = :aid AND organization_id = :org
                """
            ),
            {"id": member_row_id, "aid": assessment_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Team member not found", status_code=404)
        if assess.lead_membership_id == row.membership_id:
            raise AppError(
                "cannot_remove_lead",
                "Cannot remove the assessment lead from the team",
                status_code=422,
            )
        conn.execute(
            text("DELETE FROM assessment_team_members WHERE id = :id"),
            {"id": member_row_id},
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="assessment.team.remove",
            resource_type="assessment_team_member",
            resource_id=member_row_id,
            metadata={"assessment_id": str(assessment_id)},
        )
        conn.commit()


# --- Transitions ---


def _set_status(
    conn: Connection,
    ctx: OrgContext,
    assessment_id: UUID,
    from_status: str,
    to_status: str,
    event: str,
    *,
    set_started: bool = False,
) -> AssessmentOut:
    sql = """
        UPDATE assessments
        SET status = :to_s, updated_at = now(), updated_by = :user
    """
    if set_started:
        sql += ", started_at = COALESCE(started_at, now())"
    sql += """
        WHERE id = :id AND organization_id = :org AND status = :from_s
        RETURNING id, organization_id, assessment_model_id, standard_version_id,
                  maturity_model_id, type, status, lead_membership_id, started_at,
                  created_at, updated_at
    """
    updated = conn.execute(
        text(sql),
        {
            "to_s": to_status,
            "user": ctx.principal.user_id,
            "id": assessment_id,
            "org": ctx.organization_id,
            "from_s": from_status,
        },
    ).first()
    if updated is None:
        raise AppError("invalid_transition", "Transition race or invalid state", status_code=409)
    write_audit(
        conn,
        organization_id=ctx.organization_id,
        actor_type="user",
        actor_user_id=ctx.principal.user_id,
        actor_membership_id=ctx.membership_id,
        action=f"assessment.{event}",
        resource_type="assessment",
        resource_id=assessment_id,
        from_status=from_status,
        to_status=to_status,
    )
    return _row_to_out(updated)


def transition_plan(ctx: OrgContext, assessment_id: UUID) -> AssessmentTransitionResult:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_assessment(conn, ctx.organization_id, assessment_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"plan requires status draft (current={row.status})",
                status_code=409,
            )
        scope_n = conn.execute(
            text("SELECT count(*) FROM assessment_scopes WHERE assessment_id = :id"),
            {"id": assessment_id},
        ).scalar_one()
        if scope_n < 1:
            raise AppError(
                "plan_guard_scope",
                "plan requires at least one scope item (process or requirement)",
                status_code=422,
            )
        team_n = conn.execute(
            text("SELECT count(*) FROM assessment_team_members WHERE assessment_id = :id"),
            {"id": assessment_id},
        ).scalar_one()
        if team_n < 1 or row.lead_membership_id is None:
            raise AppError(
                "plan_guard_team",
                "plan requires minimum team (lead membership)",
                status_code=422,
            )
        updated = _set_status(conn, ctx, assessment_id, "draft", "planned", "plan")
        conn.commit()
    return AssessmentTransitionResult(
        assessment=updated, from_status="draft", to_status="planned", event="plan"
    )


def transition_start(ctx: OrgContext, assessment_id: UUID) -> AssessmentTransitionResult:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_assessment(conn, ctx.organization_id, assessment_id)
        if row.status != "planned":
            raise AppError(
                "invalid_transition",
                f"start requires status planned (current={row.status})",
                status_code=409,
            )
        updated = _set_status(
            conn, ctx, assessment_id, "planned", "in_progress", "start", set_started=True
        )
        conn.commit()
    return AssessmentTransitionResult(
        assessment=updated, from_status="planned", to_status="in_progress", event="start"
    )


def transition_reopen_draft(ctx: OrgContext, assessment_id: UUID) -> AssessmentTransitionResult:
    require_role(ctx, *_CANCEL_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_assessment(conn, ctx.organization_id, assessment_id)
        if row.status != "planned":
            raise AppError(
                "invalid_transition",
                f"reopen_draft requires status planned (current={row.status})",
                status_code=409,
            )
        if _count_approved_evidence(conn, assessment_id) > 0:
            raise AppError(
                "reopen_guard_evidence",
                "reopen_draft blocked: approved evidence exists",
                status_code=422,
            )
        if _count_completed_interviews(conn, assessment_id) > 0:
            raise AppError(
                "reopen_guard_interview",
                "reopen_draft blocked: completed interview exists",
                status_code=422,
            )
        updated = _set_status(conn, ctx, assessment_id, "planned", "draft", "reopen_draft")
        conn.commit()
    return AssessmentTransitionResult(
        assessment=updated, from_status="planned", to_status="draft", event="reopen_draft"
    )


def transition_cancel(ctx: OrgContext, assessment_id: UUID) -> AssessmentTransitionResult:
    require_role(ctx, *_CANCEL_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_assessment(conn, ctx.organization_id, assessment_id)
        if row.status not in ("draft", "planned", "in_progress"):
            raise AppError(
                "invalid_transition",
                f"cancel not allowed from status {row.status}",
                status_code=409,
            )
        if row.status in ("draft", "in_progress") and _count_approved_findings(conn, assessment_id) > 0:
            raise AppError(
                "cancel_guard_findings",
                "cancel blocked: approved findings exist",
                status_code=422,
            )
        from_status = row.status
        updated = _set_status(conn, ctx, assessment_id, from_status, "cancelled", "cancel")
        conn.commit()
    return AssessmentTransitionResult(
        assessment=updated, from_status=from_status, to_status="cancelled", event="cancel"
    )
