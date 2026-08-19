"""Create ActionItem from ProblemAnalysis finding (ISOI-004)."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import text

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.actions.schemas import (
    ActionItemOut,
    FindingActionCreate,
    ImprovementCaseActionsOut,
)
from app.modules.actions.service import (
    _ITEM_COLS,
    _PLAN_COLS,
    _READ_ROLES,
    _item_out,
    _plan_out,
)
from app.modules.improvement_cases import service as cases_service
from app.modules.orgs.service import require_role

_FINDING_ACTION_ROLES = ("org_admin", "consultant_auditor", "quality_manager")


def _derive_description(finding: dict) -> str:
    title = str(finding.get("title") or "").strip()
    step = str(finding.get("recommended_next_step") or "").strip()
    rel = str(finding.get("relationship_to_problem") or "").strip()
    impact = str(finding.get("business_impact") or "").strip()
    parts = [p for p in (title, step) if p]
    if rel:
        parts.append(f"Contexto: {rel}")
    if impact:
        parts.append(f"Impacto empresarial: {impact}")
    text_body = "\n\n".join(parts).strip()
    if not text_body:
        raise AppError(
            "finding_incomplete",
            "Finding has no usable recommendation text",
            status_code=422,
        )
    return text_body


def create_action_from_finding(
    ctx: OrgContext,
    case_id: UUID,
    run_id: UUID,
    finding_code: str,
    payload: FindingActionCreate,
) -> ActionItemOut:
    require_role(ctx, *_FINDING_ACTION_ROLES)
    # Also ensure case is readable in org (404 if missing)
    cases_service.get_case(ctx, case_id)

    code = (finding_code or "").strip()
    if not code:
        raise AppError("invalid_finding_code", "finding_code is required", status_code=422)

    with tenant_connection(ctx.organization_id) as conn:
        run = conn.execute(
            text(
                """
                SELECT id, organization_id, improvement_case_id, analysis
                FROM improvement_case_analysis_runs
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": run_id, "org": ctx.organization_id},
        ).first()
        if run is None:
            raise AppError("not_found", "Analysis run not found", status_code=404)
        if run.improvement_case_id != case_id:
            raise AppError("not_found", "Analysis run not found", status_code=404)

        analysis = run.analysis
        if isinstance(analysis, str):
            analysis = json.loads(analysis)
        findings = analysis.get("findings") or []
        finding = next((f for f in findings if f.get("code") == code), None)
        if finding is None:
            raise AppError("not_found", "Finding not found in analysis run", status_code=404)
        if not str(finding.get("recommended_next_step") or "").strip():
            raise AppError(
                "finding_incomplete",
                "Finding has no recommended_next_step",
                status_code=422,
            )

        dup = conn.execute(
            text(
                """
                SELECT id FROM action_items
                WHERE organization_id = :org
                  AND source_analysis_run_id = :run
                  AND source_finding_code = :code
                LIMIT 1
                """
            ),
            {"org": ctx.organization_id, "run": run_id, "code": code},
        ).first()
        if dup is not None:
            raise AppError(
                "finding_action_exists",
                "An action already exists for this finding on this analysis run",
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

        plan = conn.execute(
            text(
                f"""
                SELECT {_PLAN_COLS} FROM action_plans
                WHERE organization_id = :org AND improvement_case_id = :cid
                FOR UPDATE
                """
            ),
            {"org": ctx.organization_id, "cid": case_id},
        ).first()

        if plan is None:
            plan_id = uuid4()
            plan = conn.execute(
                text(
                    f"""
                    INSERT INTO action_plans (
                      id, organization_id, assessment_id, improvement_case_id,
                      status, empty_plan_rationale
                    ) VALUES (
                      :id, :org, NULL, :cid, 'draft', NULL
                    )
                    RETURNING {_PLAN_COLS}
                    """
                ),
                {"id": plan_id, "org": ctx.organization_id, "cid": case_id},
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
                metadata={"improvement_case_id": str(case_id)},
            )
        elif plan.status not in ("draft", "active"):
            raise AppError(
                "plan_not_editable",
                f"Items only on draft|active plans (current={plan.status})",
                status_code=409,
            )

        description = _derive_description(finding)
        item_id = uuid4()
        try:
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO action_items (
                      id, organization_id, action_plan_id, finding_id,
                      source_evolution_suggestion_id, source_analysis_run_id,
                      source_finding_code, action_kind, description,
                      owner_membership_id, due_at, status, efficacy_required
                    ) VALUES (
                      :id, :org, :plan, NULL,
                      NULL, :run, :code, 'improvement', :desc,
                      :owner, :due, 'open', false
                    )
                    RETURNING {_ITEM_COLS}
                    """
                ),
                {
                    "id": item_id,
                    "org": ctx.organization_id,
                    "plan": plan.id,
                    "run": run_id,
                    "code": code,
                    "desc": description,
                    "owner": payload.owner_membership_id,
                    "due": payload.due_at,
                },
            ).one()
        except Exception as exc:
            # Unique index race
            if "uq_action_items_source_run_finding" in str(exc):
                raise AppError(
                    "finding_action_exists",
                    "An action already exists for this finding on this analysis run",
                    status_code=409,
                ) from exc
            raise

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_item.create_from_finding",
            resource_type="action_item",
            resource_id=item_id,
            to_status="open",
            metadata={
                "action_plan_id": str(plan.id),
                "source_analysis_run_id": str(run_id),
                "source_finding_code": code,
            },
        )
        conn.commit()
    return _item_out(row)


def list_case_actions(ctx: OrgContext, case_id: UUID) -> ImprovementCaseActionsOut:
    require_role(ctx, *_READ_ROLES)
    cases_service.get_case(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        plan = conn.execute(
            text(
                f"""
                SELECT {_PLAN_COLS} FROM action_plans
                WHERE organization_id = :org AND improvement_case_id = :cid
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"org": ctx.organization_id, "cid": case_id},
        ).first()
        if plan is None:
            return ImprovementCaseActionsOut(plan=None, items=[])
        rows = conn.execute(
            text(
                f"""
                SELECT {_ITEM_COLS} FROM action_items
                WHERE action_plan_id = :pid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"pid": plan.id, "org": ctx.organization_id},
        ).all()
    return ImprovementCaseActionsOut(
        plan=_plan_out(plan),
        items=[_item_out(r) for r in rows],
    )
