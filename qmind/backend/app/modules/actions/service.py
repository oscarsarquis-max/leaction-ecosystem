"""ActionPlan / ActionItem — domain-docs-v0 §5."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.actions.schemas import (
    ActionItemCreate,
    ActionItemOut,
    ActionItemTransitionResult,
    ActionPlanCreate,
    ActionPlanOut,
    ActionPlanTransitionResult,
    ReasonIn,
)
from app.modules.orgs.service import require_role

_PLAN_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_PLAN_COMPLETE_ROLES = ("org_admin", "quality_manager")
_ITEM_CREATE_ROLES = _PLAN_ROLES
_VALIDATE_ROLES = ("org_admin", "quality_manager", "process_owner")
_EFFICACY_ROLES = ("org_admin", "quality_manager")
_READ_ROLES = _PLAN_ROLES + ("process_owner", "action_owner", "reader")

_PLAN_COLS = """
    id, organization_id, assessment_id, improvement_case_id, status,
    empty_plan_rationale, created_at, updated_at
"""
_ITEM_COLS = """
    id, organization_id, action_plan_id, finding_id, source_evolution_suggestion_id,
    source_analysis_run_id, source_finding_code,
    action_kind, description,
    owner_membership_id, due_at, status, is_overdue, efficacy_required,
    source_finding_withdrawn, validated_by, efficacy_confirmed_by,
    cancel_reason, reject_reason, efficacy_fail_reason,
    created_at, updated_at
"""


def _plan_out(row) -> ActionPlanOut:
    return ActionPlanOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        improvement_case_id=getattr(row, "improvement_case_id", None),
        status=row.status,
        empty_plan_rationale=row.empty_plan_rationale,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _item_out(row) -> ActionItemOut:
    return ActionItemOut(
        id=row.id,
        organization_id=row.organization_id,
        action_plan_id=row.action_plan_id,
        finding_id=row.finding_id,
        source_evolution_suggestion_id=getattr(
            row, "source_evolution_suggestion_id", None
        ),
        source_analysis_run_id=getattr(row, "source_analysis_run_id", None),
        source_finding_code=getattr(row, "source_finding_code", None),
        action_kind=row.action_kind,
        description=row.description,
        owner_membership_id=row.owner_membership_id,
        due_at=row.due_at,
        status=row.status,
        is_overdue=row.is_overdue,
        efficacy_required=row.efficacy_required,
        source_finding_withdrawn=bool(getattr(row, "source_finding_withdrawn", False)),
        validated_by=row.validated_by,
        efficacy_confirmed_by=row.efficacy_confirmed_by,
        cancel_reason=getattr(row, "cancel_reason", None),
        reject_reason=getattr(row, "reject_reason", None),
        efficacy_fail_reason=getattr(row, "efficacy_fail_reason", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_plan(conn: Connection, org_id: UUID, plan_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_PLAN_COLS}
            FROM action_plans
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": plan_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "ActionPlan not found", status_code=404)
    return row


def _lock_item(conn: Connection, org_id: UUID, item_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_ITEM_COLS}
            FROM action_items
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": item_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "ActionItem not found", status_code=404)
    return row


def _assert_owner_or_roles(ctx: OrgContext, owner_id: UUID, *roles: str) -> None:
    if ctx.membership_id == owner_id:
        return
    if set(ctx.roles).intersection(roles):
        return
    raise AppError("forbidden", "Insufficient role for this operation", status_code=403)


def create_plan(ctx: OrgContext, payload: ActionPlanCreate) -> ActionPlanOut:
    require_role(ctx, *_PLAN_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT id, status FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if assess.status not in ("analysis", "actions"):
            raise AppError(
                "assessment_not_ready",
                f"ActionPlan requires assessment analysis|actions (current={assess.status})",
                status_code=409,
            )
        plan_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO action_plans (
                  id, organization_id, assessment_id, improvement_case_id,
                  status, empty_plan_rationale
                ) VALUES (:id, :org, :assess, NULL, 'draft', :rationale)
                RETURNING {_PLAN_COLS}
                """
            ),
            {
                "id": plan_id,
                "org": ctx.organization_id,
                "assess": payload.assessment_id,
                "rationale": (
                    payload.empty_plan_rationale.strip()
                    if payload.empty_plan_rationale
                    else None
                ),
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_plan.create",
            resource_type="action_plan",
            resource_id=plan_id,
            to_status="draft",
        )
        conn.commit()
    return _plan_out(row)


def get_plan(ctx: OrgContext, plan_id: UUID) -> ActionPlanOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        return _plan_out(_lock_plan(conn, ctx.organization_id, plan_id))


def list_plans(
    ctx: OrgContext,
    assessment_id: UUID | None = None,
    improvement_case_id: UUID | None = None,
) -> list[ActionPlanOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        if assessment_id:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {_PLAN_COLS} FROM action_plans
                    WHERE organization_id = :org AND assessment_id = :aid
                    ORDER BY created_at DESC
                    """
                ),
                {"org": ctx.organization_id, "aid": assessment_id},
            ).all()
        elif improvement_case_id:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {_PLAN_COLS} FROM action_plans
                    WHERE organization_id = :org AND improvement_case_id = :cid
                    ORDER BY created_at DESC
                    """
                ),
                {"org": ctx.organization_id, "cid": improvement_case_id},
            ).all()
        else:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {_PLAN_COLS} FROM action_plans
                    WHERE organization_id = :org
                    ORDER BY created_at DESC
                    """
                ),
                {"org": ctx.organization_id},
            ).all()
    return [_plan_out(r) for r in rows]


def activate_plan(ctx: OrgContext, plan_id: UUID) -> ActionPlanTransitionResult:
    require_role(ctx, *_PLAN_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_plan(conn, ctx.organization_id, plan_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"activate requires draft (current={row.status})",
                status_code=409,
            )
        item_n = conn.execute(
            text("SELECT count(*) FROM action_items WHERE action_plan_id = :id"),
            {"id": plan_id},
        ).scalar_one()
        if item_n < 1 and not (row.empty_plan_rationale or "").strip():
            raise AppError(
                "activate_guard",
                "Activate requires ≥1 item or empty_plan_rationale",
                status_code=422,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_plans
                SET status = 'active', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_PLAN_COLS}
                """
            ),
            {"id": plan_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_plan.activate",
            resource_type="action_plan",
            resource_id=plan_id,
            from_status="draft",
            to_status="active",
        )
        conn.commit()
    return ActionPlanTransitionResult(
        plan=_plan_out(updated), from_status="draft", to_status="active", event="activate"
    )


def complete_plan(ctx: OrgContext, plan_id: UUID) -> ActionPlanTransitionResult:
    require_role(ctx, *_PLAN_COMPLETE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_plan(conn, ctx.organization_id, plan_id)
        if row.status != "active":
            raise AppError(
                "invalid_transition",
                f"complete requires active (current={row.status})",
                status_code=409,
            )
        open_n = conn.execute(
            text(
                """
                SELECT count(*) FROM action_items
                WHERE action_plan_id = :id
                  AND status NOT IN ('done', 'cancelled', 'ineffective_closed')
                """
            ),
            {"id": plan_id},
        ).scalar_one()
        if open_n > 0:
            raise AppError(
                "complete_guard",
                "All items must be done|cancelled|ineffective_closed",
                status_code=422,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_plans
                SET status = 'completed', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'active'
                RETURNING {_PLAN_COLS}
                """
            ),
            {"id": plan_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_plan.complete",
            resource_type="action_plan",
            resource_id=plan_id,
            from_status="active",
            to_status="completed",
        )
        conn.commit()
    return ActionPlanTransitionResult(
        plan=_plan_out(updated), from_status="active", to_status="completed", event="complete"
    )


def cancel_plan(ctx: OrgContext, plan_id: UUID) -> ActionPlanTransitionResult:
    require_role(ctx, *_PLAN_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_plan(conn, ctx.organization_id, plan_id)
        if row.status not in ("draft", "active"):
            raise AppError(
                "invalid_transition",
                f"cancel requires draft|active (current={row.status})",
                status_code=409,
            )
        published = 0
        if row.assessment_id is not None:
            published = conn.execute(
                text(
                    """
                    SELECT count(*) FROM reports
                    WHERE assessment_id = :aid
                      AND organization_id = :org
                      AND status = 'published'
                    """
                ),
                {"aid": row.assessment_id, "org": ctx.organization_id},
            ).scalar_one()
        if published > 0:
            raise AppError(
                "plan_cancel_blocked_published_report",
                "Cannot cancel ActionPlan while Assessment has a published Report "
                "(requires formal amendment / supersede)",
                status_code=409,
            )

        # Cancel eligible open items — each audited; does not touch implemented+
        eligible = conn.execute(
            text(
                """
                SELECT id, status FROM action_items
                WHERE action_plan_id = :id
                  AND organization_id = :org
                  AND status IN ('open', 'in_progress')
                FOR UPDATE
                """
            ),
            {"id": plan_id, "org": ctx.organization_id},
        ).all()
        for item in eligible:
            conn.execute(
                text(
                    """
                    UPDATE action_items
                    SET status = 'cancelled',
                        cancel_reason = 'plan_cancelled',
                        updated_at = now()
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": item.id, "org": ctx.organization_id},
            )
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="action_item.cancel",
                resource_type="action_item",
                resource_id=item.id,
                from_status=item.status,
                to_status="cancelled",
                metadata={
                    "reason": "plan_cancelled",
                    "action_plan_id": str(plan_id),
                    "cascaded_from": "action_plan.cancel",
                },
            )

        from_status = row.status
        updated = conn.execute(
            text(
                f"""
                UPDATE action_plans
                SET status = 'cancelled', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = :from_s
                RETURNING {_PLAN_COLS}
                """
            ),
            {"id": plan_id, "org": ctx.organization_id, "from_s": from_status},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_plan.cancel",
            resource_type="action_plan",
            resource_id=plan_id,
            from_status=from_status,
            to_status="cancelled",
            metadata={
                "cancelled_action_item_ids": [str(i.id) for i in eligible],
            },
        )
        conn.commit()
    return ActionPlanTransitionResult(
        plan=_plan_out(updated),
        from_status=from_status,
        to_status="cancelled",
        event="cancel",
    )


def create_item(ctx: OrgContext, plan_id: UUID, payload: ActionItemCreate) -> ActionItemOut:
    require_role(ctx, *_ITEM_CREATE_ROLES)
    efficacy = payload.efficacy_required
    if efficacy is None:
        efficacy = payload.action_kind == "corrective_action"
    with tenant_connection(ctx.organization_id) as conn:
        plan = _lock_plan(conn, ctx.organization_id, plan_id)
        if plan.status not in ("draft", "active"):
            raise AppError(
                "plan_not_editable",
                f"Items only on draft|active plans (current={plan.status})",
                status_code=409,
            )
        owner = conn.execute(
            text(
                """
                SELECT id FROM memberships
                WHERE id = :id AND organization_id = :org AND status = 'active'
                """
            ),
            {"id": payload.owner_membership_id, "org": ctx.organization_id},
        ).first()
        if owner is None:
            raise AppError("not_found", "Owner membership not found", status_code=404)
        if payload.finding_id:
            finding = conn.execute(
                text(
                    """
                    SELECT id, status FROM findings
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": payload.finding_id, "org": ctx.organization_id},
            ).first()
            if finding is None:
                raise AppError("not_found", "Finding not found", status_code=404)
            if finding.status == "discarded":
                raise AppError("finding_discarded", "Cannot link discarded finding", status_code=422)

        if payload.source_evolution_suggestion_id:
            sug = conn.execute(
                text(
                    """
                    SELECT id, status FROM evolution_suggestions
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {
                    "id": payload.source_evolution_suggestion_id,
                    "org": ctx.organization_id,
                },
            ).first()
            if sug is None:
                raise AppError(
                    "not_found", "Evolution suggestion not found", status_code=404
                )
            if sug.status not in ("accepted", "converted_to_action"):
                raise AppError(
                    "suggestion_not_convertible",
                    "Only accepted suggestions can be linked as action origin",
                    status_code=422,
                )
            dup = conn.execute(
                text(
                    """
                    SELECT id FROM action_items
                    WHERE source_evolution_suggestion_id = :sid
                      AND organization_id = :org
                    LIMIT 1
                    """
                ),
                {
                    "sid": payload.source_evolution_suggestion_id,
                    "org": ctx.organization_id,
                },
            ).first()
            if dup is not None:
                raise AppError(
                    "suggestion_already_converted",
                    "This evolution suggestion already has an action item",
                    status_code=409,
                )

        item_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO action_items (
                  id, organization_id, action_plan_id, finding_id,
                  source_evolution_suggestion_id, source_analysis_run_id,
                  source_finding_code, action_kind,
                  description, owner_membership_id, due_at, status, efficacy_required
                ) VALUES (
                  :id, :org, :plan, :fid,
                  :esid, NULL, NULL, :kind,
                  :desc, :owner, :due, 'open', :efficacy
                )
                RETURNING {_ITEM_COLS}
                """
            ),
            {
                "id": item_id,
                "org": ctx.organization_id,
                "plan": plan_id,
                "fid": payload.finding_id,
                "esid": payload.source_evolution_suggestion_id,
                "kind": payload.action_kind,
                "desc": payload.description.strip(),
                "owner": payload.owner_membership_id,
                "due": payload.due_at,
                "efficacy": efficacy,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.create",
            resource_type="action_item",
            resource_id=item_id,
            to_status="open",
            metadata={"action_plan_id": str(plan_id)},
        )
        conn.commit()
    return _item_out(row)


def get_item(ctx: OrgContext, item_id: UUID) -> ActionItemOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        return _item_out(_lock_item(conn, ctx.organization_id, item_id))


def list_items(ctx: OrgContext, plan_id: UUID) -> list[ActionItemOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _lock_plan(conn, ctx.organization_id, plan_id)
        rows = conn.execute(
            text(
                f"""
                SELECT {_ITEM_COLS} FROM action_items
                WHERE action_plan_id = :pid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"pid": plan_id, "org": ctx.organization_id},
        ).all()
    return [_item_out(r) for r in rows]


def start_item(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "open":
            raise AppError(
                "invalid_transition",
                f"start requires open (current={row.status})",
                status_code=409,
            )
        _assert_owner_or_roles(
            ctx, row.owner_membership_id, "org_admin", "quality_manager", "process_owner"
        )
        # action_owner role OR is owner membership
        if ctx.membership_id != row.owner_membership_id and not set(ctx.roles).intersection(
            ("org_admin", "quality_manager", "process_owner", "action_owner")
        ):
            raise AppError("forbidden", "Only owner/process_owner may start", status_code=403)
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'in_progress', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'open'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.start",
            resource_type="action_item",
            resource_id=item_id,
            from_status="open",
            to_status="in_progress",
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="open",
        to_status="in_progress",
        event="start",
    )


def mark_implemented(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "in_progress":
            raise AppError(
                "invalid_transition",
                f"mark_implemented requires in_progress (current={row.status})",
                status_code=409,
            )
        if ctx.membership_id != row.owner_membership_id and not set(ctx.roles).intersection(
            ("org_admin", "quality_manager", "process_owner")
        ):
            raise AppError("forbidden", "Only owner/process_owner may mark implemented", status_code=403)
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'implemented', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_progress'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.mark_implemented",
            resource_type="action_item",
            resource_id=item_id,
            from_status="in_progress",
            to_status="implemented",
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="in_progress",
        to_status="implemented",
        event="mark_implemented",
    )


def validate_item(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    """Validation ≠ execution: owner cannot validate own work (SoD)."""
    require_role(ctx, *_VALIDATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "implemented":
            raise AppError(
                "invalid_transition",
                f"validate requires implemented (current={row.status})",
                status_code=409,
            )
        if ctx.membership_id == row.owner_membership_id:
            raise AppError(
                "sod_violation",
                "Validator must differ from action owner",
                status_code=403,
            )
        to_status = "done" if not row.efficacy_required else "validated"
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = :to_s,
                    validated_by = :validator,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'implemented'
                RETURNING {_ITEM_COLS}
                """
            ),
            {
                "to_s": to_status,
                "validator": ctx.membership_id,
                "id": item_id,
                "org": ctx.organization_id,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.validate",
            resource_type="action_item",
            resource_id=item_id,
            from_status="implemented",
            to_status=to_status,
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="implemented",
        to_status=to_status,
        event="validate",
    )


def reject_implementation(
    ctx: OrgContext, item_id: UUID, payload: ReasonIn
) -> ActionItemTransitionResult:
    require_role(ctx, *_VALIDATE_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "implemented":
            raise AppError(
                "invalid_transition",
                f"reject_implementation requires implemented (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'in_progress',
                    reject_reason = :reason,
                    validated_by = NULL,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'implemented'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"reason": reason, "id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.reject_implementation",
            resource_type="action_item",
            resource_id=item_id,
            from_status="implemented",
            to_status="in_progress",
            metadata={"reason": reason},
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="implemented",
        to_status="in_progress",
        event="reject_implementation",
    )


def confirm_efficacy(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    require_role(ctx, *_EFFICACY_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "validated":
            raise AppError(
                "invalid_transition",
                f"confirm_efficacy requires validated (current={row.status})",
                status_code=409,
            )
        if not row.efficacy_required:
            raise AppError(
                "efficacy_not_required",
                "confirm_efficacy requires efficacy_required=true "
                "(use validate→done when efficacy is not required)",
                status_code=422,
            )
        if ctx.membership_id == row.owner_membership_id:
            raise AppError(
                "sod_violation",
                "Efficacy confirmer must differ from action owner",
                status_code=403,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'done',
                    efficacy_confirmed_by = :who,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'validated'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"who": ctx.membership_id, "id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.confirm_efficacy",
            resource_type="action_item",
            resource_id=item_id,
            from_status="validated",
            to_status="done",
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="validated",
        to_status="done",
        event="confirm_efficacy",
    )


def fail_efficacy(ctx: OrgContext, item_id: UUID, payload: ReasonIn) -> ActionItemTransitionResult:
    require_role(ctx, *_EFFICACY_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "validated":
            raise AppError(
                "invalid_transition",
                f"fail_efficacy requires validated (current={row.status})",
                status_code=409,
            )
        if not row.efficacy_required:
            raise AppError(
                "efficacy_not_required",
                "fail_efficacy requires efficacy_required=true",
                status_code=422,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'ineffective',
                    efficacy_fail_reason = :reason,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'validated'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"reason": reason, "id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.fail_efficacy",
            resource_type="action_item",
            resource_id=item_id,
            from_status="validated",
            to_status="ineffective",
            metadata={"reason": reason},
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="validated",
        to_status="ineffective",
        event="fail_efficacy",
    )


def reopen_item(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "ineffective":
            raise AppError(
                "invalid_transition",
                f"reopen requires ineffective (current={row.status})",
                status_code=409,
            )
        if ctx.membership_id != row.owner_membership_id and not set(ctx.roles).intersection(
            ("org_admin", "quality_manager")
        ):
            raise AppError("forbidden", "Only owner/QM/admin may reopen", status_code=403)
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'in_progress',
                    validated_by = NULL,
                    efficacy_confirmed_by = NULL,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'ineffective'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.reopen",
            resource_type="action_item",
            resource_id=item_id,
            from_status="ineffective",
            to_status="in_progress",
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="ineffective",
        to_status="in_progress",
        event="reopen",
    )


def close_ineffective(ctx: OrgContext, item_id: UUID) -> ActionItemTransitionResult:
    require_role(ctx, *_EFFICACY_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status != "ineffective":
            raise AppError(
                "invalid_transition",
                f"close_ineffective requires ineffective (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'ineffective_closed', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'ineffective'
                RETURNING {_ITEM_COLS}
                """
            ),
            {"id": item_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.close_ineffective",
            resource_type="action_item",
            resource_id=item_id,
            from_status="ineffective",
            to_status="ineffective_closed",
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status="ineffective",
        to_status="ineffective_closed",
        event="close_ineffective",
    )


def cancel_item(ctx: OrgContext, item_id: UUID, payload: ReasonIn) -> ActionItemTransitionResult:
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_item(conn, ctx.organization_id, item_id)
        if row.status not in ("open", "in_progress"):
            raise AppError(
                "invalid_transition",
                f"cancel requires open|in_progress (current={row.status})",
                status_code=409,
            )
        is_owner = ctx.membership_id == row.owner_membership_id
        if row.status == "open" and is_owner:
            pass
        elif set(ctx.roles).intersection(("org_admin", "quality_manager", "consultant_auditor")):
            pass
        else:
            raise AppError("forbidden", "Insufficient role to cancel item", status_code=403)
        from_status = row.status
        updated = conn.execute(
            text(
                f"""
                UPDATE action_items
                SET status = 'cancelled',
                    cancel_reason = :reason,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = :from_s
                RETURNING {_ITEM_COLS}
                """
            ),
            {
                "reason": reason,
                "id": item_id,
                "org": ctx.organization_id,
                "from_s": from_status,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.cancel",
            resource_type="action_item",
            resource_id=item_id,
            from_status=from_status,
            to_status="cancelled",
            metadata={"reason": reason},
        )
        conn.commit()
    return ActionItemTransitionResult(
        item=_item_out(updated),
        from_status=from_status,
        to_status="cancelled",
        event="cancel",
    )
