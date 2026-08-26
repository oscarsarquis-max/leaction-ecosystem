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
from app.modules.improvement_cases import execution_intelligence_service
from app.modules.improvement_cases import service as cases_service
from app.modules.improvement_cases.evolution_schemas import (
    ActionStatusCount,
    ActionSummary,
    AnalysisRunComparison,
    AnalysisSummary,
    ClosureReadiness,
    ImprovementCaseEvolutionOut,
    MeasurementSummary,
    OutcomeObservationCreate,
    OutcomeObservationOut,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceSummary,
)
from app.modules.improvement_cases.problem_schemas import ImprovementCaseAnalysisRunOut
from app.modules.measurements import service as measurements_service
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


def _obs_out(row, measurement_ids: list[UUID] | None = None) -> OutcomeObservationOut:
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
        measurement_record_ids=measurement_ids or [],
    )


def _measurement_ids_by_observation(
    conn, org_id: UUID, observation_ids: list[UUID]
) -> dict[UUID, list[UUID]]:
    if not observation_ids:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT outcome_observation_id, measurement_record_id
            FROM outcome_observation_measurements
            WHERE organization_id = :org AND outcome_observation_id = ANY(:ids)
            ORDER BY created_at
            """
        ),
        {"org": org_id, "ids": observation_ids},
    ).all()
    out: dict[UUID, list[UUID]] = {}
    for r in rows:
        out.setdefault(r.outcome_observation_id, []).append(r.measurement_record_id)
    return out


def create_outcome_observation(
    ctx: OrgContext,
    case_id: UUID,
    payload: OutcomeObservationCreate,
) -> OutcomeObservationOut:
    require_role(ctx, *_WRITE_ROLES)
    cases_service.get_case(ctx, case_id)
    requested = list(dict.fromkeys(payload.measurement_record_ids))
    with tenant_connection(ctx.organization_id) as conn:
        if requested:
            valid = measurements_service.measurement_ids_for_case(
                conn, ctx.organization_id, case_id, requested
            )
            unknown = [m for m in requested if m not in valid]
            if unknown:
                raise AppError(
                    "measurement_case_mismatch",
                    "Estas medições não pertencem a este caso de melhoria: "
                    + ", ".join(str(m) for m in unknown),
                    status_code=422,
                )
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
        for measurement_id in requested:
            conn.execute(
                text(
                    """
                    INSERT INTO outcome_observation_measurements (
                      organization_id, outcome_observation_id,
                      measurement_record_id, created_by
                    ) VALUES (:org, :oid, :mid, :uid)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "oid": row.id,
                    "mid": measurement_id,
                    "uid": ctx.principal.user_id,
                },
            )
        conn.commit()
    return _obs_out(row, requested)


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
        by_obs = _measurement_ids_by_observation(
            conn, ctx.organization_id, [r.id for r in rows]
        )
    return [_obs_out(r, by_obs.get(r.id, [])) for r in rows]


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


# A planned-but-unproven measurement is missing information. `not_planned` is
# deliberately absent: a case that never planned measurement is judged by the
# other gates, exactly as it was before measurement existed.
def _closure_readiness(
    *,
    latest_run: ImprovementCaseAnalysisRunOut | None,
    action_summary: ActionSummary,
    latest_obs: OutcomeObservationOut | None,
    measurement_posture: str,
) -> tuple[ClosureReadiness, str]:
    """Thin adapter — policy lives in ``evaluate_closure_readiness``."""
    from app.modules.improvement_cases.closure_readiness import evaluate_closure_readiness

    return evaluate_closure_readiness(
        has_problem_analysis=latest_run is not None,
        problem_analysis_is_stale=bool(latest_run is not None and latest_run.is_stale),
        action_count=action_summary.total,
        has_incomplete_actions=any(
            i.status not in _COMPLETED_STATUSES for i in action_summary.items
        ),
        has_outcome=latest_obs is not None,
        outcome_direction=latest_obs.result_direction if latest_obs else None,
        measurement_posture=measurement_posture,
    )


def _measurement_summary(ctx: OrgContext, case_id: UUID) -> MeasurementSummary:
    with tenant_connection(ctx.organization_id) as conn:
        posture, targets, substantiation, evaluations = (
            measurements_service.summarize_case_measurements(
                conn, ctx.organization_id, case_id
            )
        )
    return MeasurementSummary(
        measurement_posture=posture,
        target_posture=targets,
        substantiation=substantiation,
        indicator_count=len(evaluations),
        overdue_indicator_count=sum(
            1 for e in evaluations if e.is_measurement_overdue
        ),
        evaluations=evaluations,
    )


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
    measurement_summary = _measurement_summary(ctx, case_id)
    readiness, reason = _closure_readiness(
        latest_run=latest,
        action_summary=action_summary,
        latest_obs=latest_obs,
        measurement_posture=measurement_summary.measurement_posture,
    )
    ei_runs = execution_intelligence_service.list_runs(ctx, case_id, limit=1)
    ei = None
    if ei_runs:
        run = ei_runs[0]
        ei = ExecutionIntelligenceSummary(
            run_id=run.id,
            generated_at=run.generated_at,
            interpretability_status=run.result.interpretability_status,
            execution_posture=run.result.execution_posture,
            interpretation_summary=run.result.interpretation_summary,
            signal_count=len(run.result.signals),
            is_stale=run.is_stale,
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
        measurement_summary=measurement_summary,
        latest_outcome_observation=latest_obs,
        outcome_observations=observations,
        closure_readiness=readiness,
        closure_readiness_reason=reason,
        execution_intelligence=ei,
    )
