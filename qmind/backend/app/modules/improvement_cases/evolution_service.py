"""Outcome observations + evolution projection (ISOI-005)."""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.improvement_cases import analysis_service
from app.modules.improvement_cases import finding_actions
from app.modules.improvement_cases import service as cases_service
from app.modules.improvement_cases.evolution_schemas import (
    ActionStatusCount,
    ActionSummary,
    AnalysisRunComparison,
    AnalysisSummary,
    ClosureReadiness,
    ImprovementCaseEvolutionOut,
    OutcomeObservationCreate,
    OutcomeObservationOut,
)
from app.modules.improvement_cases.problem_schemas import ImprovementCaseAnalysisRunOut
from app.modules.orgs.service import require_role

_READ_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "reader",
    "action_owner",
    "platform_admin",
)
_WRITE_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "platform_admin",
)

_OBS_COLS = """
    id, organization_id, improvement_case_id, result_direction,
    observation_statement, measurement_basis, observed_at, created_by, created_at
"""

# Terminal / concluded statuses per ActionItem lifecycle (domain-docs).
_COMPLETED_STATUSES = frozenset(
    {"done", "cancelled", "ineffective_closed"}
)


def _obs_out(row) -> OutcomeObservationOut:
    return OutcomeObservationOut(
        id=row.id,
        organization_id=row.organization_id,
        improvement_case_id=row.improvement_case_id,
        result_direction=row.result_direction,
        observation_statement=row.observation_statement,
        measurement_basis=row.measurement_basis,
        observed_at=row.observed_at,
        created_by=row.created_by,
        created_at=row.created_at,
    )


def create_outcome_observation(
    ctx: OrgContext,
    case_id: UUID,
    payload: OutcomeObservationCreate,
) -> OutcomeObservationOut:
    require_role(ctx, *_WRITE_ROLES)
    cases_service.get_case(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                INSERT INTO improvement_case_outcome_observations (
                  organization_id, improvement_case_id, result_direction,
                  observation_statement, measurement_basis, observed_at, created_by
                ) VALUES (
                  :org, :case_id, :direction, :statement, :basis, :observed_at, :author
                )
                RETURNING {_OBS_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "case_id": case_id,
                "direction": payload.result_direction,
                "statement": payload.observation_statement,
                "basis": payload.measurement_basis,
                "observed_at": payload.observed_at,
                "author": ctx.principal.user_id,
            },
        ).one()
        conn.commit()
    return _obs_out(row)


def list_outcome_observations(
    ctx: OrgContext,
    case_id: UUID,
    *,
    limit: int = 50,
) -> list[OutcomeObservationOut]:
    require_role(ctx, *_READ_ROLES)
    cases_service.get_case(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_OBS_COLS}
                FROM improvement_case_outcome_observations
                WHERE improvement_case_id = :case_id AND organization_id = :org
                ORDER BY observed_at DESC, created_at DESC
                LIMIT :lim
                """
            ),
            {"case_id": case_id, "org": ctx.organization_id, "lim": limit},
        ).all()
    return [_obs_out(r) for r in rows]


def _missing_from_analysis(analysis: dict) -> set[str]:
    missing: set[str] = set()
    for hyp in analysis.get("hypotheses") or []:
        for m in hyp.get("missing_information") or []:
            missing.add(str(m))
    for finding in analysis.get("findings") or []:
        for m in finding.get("missing_information") or []:
            missing.add(str(m))
    return missing


def _finding_codes(analysis: dict) -> set[str]:
    return {
        str(f.get("code"))
        for f in (analysis.get("findings") or [])
        if f.get("code")
    }


def _limitations(analysis: dict) -> set[str]:
    return {str(x) for x in (analysis.get("limitations") or []) if str(x).strip()}


def compare_runs(
    previous: ImprovementCaseAnalysisRunOut,
    latest: ImprovementCaseAnalysisRunOut,
) -> AnalysisRunComparison:
    before = previous.analysis.model_dump(mode="json")
    after = latest.analysis.model_dump(mode="json")
    f_before = _finding_codes(before)
    f_after = _finding_codes(after)
    m_before = _missing_from_analysis(before)
    m_after = _missing_from_analysis(after)
    l_before = _limitations(before)
    l_after = _limitations(after)
    return AnalysisRunComparison(
        context_status_before=previous.analysis.context_status,
        context_status_after=latest.analysis.context_status,
        findings_added=sorted(f_after - f_before),
        findings_removed=sorted(f_before - f_after),
        findings_persisting=sorted(f_before & f_after),
        missing_information_added=sorted(m_after - m_before),
        missing_information_removed=sorted(m_before - m_after),
        limitations_added=sorted(l_after - l_before),
        limitations_removed=sorted(l_before - l_after),
    )


def _action_summary(ctx: OrgContext, case_id: UUID) -> ActionSummary:
    bundle = finding_actions.list_case_actions(ctx, case_id)
    items = bundle.items
    counts = Counter(i.status for i in items)
    completed = sum(1 for i in items if i.status in _COMPLETED_STATUSES)
    overdue = sum(1 for i in items if i.is_overdue)
    return ActionSummary(
        total=len(items),
        by_status=[
            ActionStatusCount(status=s, count=c) for s, c in sorted(counts.items())
        ],
        overdue=overdue,
        completed=completed,
        items=items,
        plan=bundle.plan,
    )


def _closure_readiness(
    *,
    latest_run: ImprovementCaseAnalysisRunOut | None,
    action_summary: ActionSummary,
    latest_obs: OutcomeObservationOut | None,
) -> ClosureReadiness:
    if latest_run is None:
        return "insufficient_information"
    if latest_run.is_stale:
        return "insufficient_information"
    if action_summary.total < 1:
        return "insufficient_information"
    if any(i.status not in _COMPLETED_STATUSES for i in action_summary.items):
        return "insufficient_information"
    if latest_obs is None:
        return "insufficient_information"
    if latest_obs.result_direction == "not_yet_measured":
        return "insufficient_information"
    return "ready_for_review"


def get_evolution(ctx: OrgContext, case_id: UUID) -> ImprovementCaseEvolutionOut:
    require_role(ctx, *_READ_ROLES)
    case = cases_service.get_case(ctx, case_id)
    runs = analysis_service.list_analysis_runs(ctx, case_id, limit=50)
    latest = runs[0] if runs else None
    previous = runs[1] if len(runs) > 1 else None
    comparison = (
        compare_runs(previous, latest) if latest and previous else None
    )
    action_summary = _action_summary(ctx, case_id)
    observations = list_outcome_observations(ctx, case_id, limit=50)
    latest_obs = observations[0] if observations else None
    readiness = _closure_readiness(
        latest_run=latest,
        action_summary=action_summary,
        latest_obs=latest_obs,
    )
    return ImprovementCaseEvolutionOut(
        case=case,
        analysis_summary=AnalysisSummary(
            total_runs=len(runs),
            latest_run=latest,
            previous_run=previous,
            comparison=comparison,
        ),
        action_summary=action_summary,
        latest_outcome_observation=latest_obs,
        outcome_observations=observations,
        closure_readiness=readiness,
    )
