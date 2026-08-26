"""Build the factual Execution Intelligence snapshot; contains no OI rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.improvement_cases.execution_intelligence_fact_refs import (
    CORE_EXECUTED_TERMINAL_STATUSES,
    CORE_TERMINAL_ACTION_STATUSES,
    action_fact_refs,
    case_status_ref,
    indicator_fact_refs,
    outcome_direction_ref,
    plan_status_ref,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionActionFacts,
    ExecutionCaseFacts,
    ExecutionFacts,
    ExecutionIntelligenceInput,
    ExecutionPlanFacts,
    MeasurementFacts,
    MeasurementIndicatorFacts,
    MeasurementPlanFacts,
    OutcomeFacts,
)
from app.modules.measurements import service as measurements_service
from app.modules.oi.schemas import SourceRef


def _ref(kind: str, position: int) -> str:
    return f"{kind}:{position}"


def _decimal(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


def _measurement_facts(
    conn: Connection, org_id: UUID, case_id: UUID
) -> tuple[list[MeasurementPlanFacts], list[MeasurementIndicatorFacts], list[str]]:
    plan_rows = conn.execute(
        text(
            """
            SELECT id, status
            FROM action_measurement_plans
            WHERE organization_id = :org AND improvement_case_id = :case_id
            ORDER BY created_at, id
            """
        ),
        {"org": org_id, "case_id": case_id},
    ).all()
    _posture, _target, _substantiation, evaluations = (
        measurements_service.summarize_case_measurements(conn, org_id, case_id)
    )
    plan_refs = {row.id: _ref("measurement-plan", i) for i, row in enumerate(plan_rows, 1)}
    plans = [
        MeasurementPlanFacts(
            plan_ref=plan_refs[row.id],
            status="completed" if row.status == "closed" else row.status,
        )
        for row in plan_rows
    ]
    indicator_plan = {
        row.id: row.measurement_plan_id
        for row in conn.execute(
            text(
                """
                SELECT id, measurement_plan_id
                FROM indicator_definitions
                WHERE organization_id = :org
                  AND measurement_plan_id = ANY(:plan_ids)
                  AND status = 'active'
                ORDER BY code, id
                """
            ),
            {"org": org_id, "plan_ids": list(plan_refs)},
        ).all()
    } if plan_refs else {}
    indicators: list[MeasurementIndicatorFacts] = []
    refs: list[str] = []
    for index, ev in enumerate(
        sorted(
            evaluations,
            key=lambda item: (
                item.indicator_code,
                str(item.indicator_definition_id),
            ),
        ),
        1,
    ):
        indicator_ref = _ref("indicator", index)
        plan_ref = plan_refs[indicator_plan[ev.indicator_definition_id]]
        indicators.append(
            MeasurementIndicatorFacts(
                indicator_ref=indicator_ref,
                plan_ref=plan_ref,
                name=ev.indicator_name,
                unit=(
                    str(ev.unit_label).strip()
                    if ev.unit_label and str(ev.unit_label).strip()
                    else "n/a"
                ),
                direction=ev.direction,
                target_value=_decimal(ev.target_value),
                target_min=_decimal(ev.target_min),
                target_max=_decimal(ev.target_max),
                baseline_value=_decimal(ev.baseline_value),
                baseline_at=_utc(ev.baseline_at),
                latest_value=_decimal(ev.latest_value),
                latest_measured_at=_utc(ev.latest_measured_at),
                measurement_posture=(
                    "overdue"
                    if ev.is_measurement_overdue
                    else "awaiting_baseline"
                    if ev.baseline_status == "missing"
                    else "awaiting_measurement"
                    if ev.latest_value is None
                    else "on_time"
                ),
                target_posture=(
                    "met"
                    if ev.state == "target_met"
                    else "not_met"
                    if ev.state == "target_not_met"
                    else "unknown"
                ),
                baseline_status=ev.baseline_status,
                is_measurement_overdue=ev.is_measurement_overdue,
                next_measurement_due_at=_utc(ev.next_measurement_due_at),
                substantiation=ev.substantiation,
                comparable_reading_count=ev.measurement_count,
            )
        )
        refs.extend(indicator_fact_refs(indicator_ref))
    return plans, indicators, refs


def build_execution_intelligence_input(
    ctx: OrgContext,
    case_id: UUID,
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    captured_at: datetime | None = None,
) -> ExecutionIntelligenceInput:
    """Load the complete case snapshot with a fixed number of batch queries."""
    rid = request_id or str(uuid4())
    when = (captured_at or datetime.now(UTC)).astimezone(UTC)
    with tenant_connection(ctx.organization_id) as conn:
        case = conn.execute(
            text(
                """
                SELECT c.id, c.status, c.problem_statement, c.impact_statement,
                       c.related_process,
                       (SELECT r.id FROM improvement_case_analysis_runs r
                         WHERE r.organization_id = c.organization_id
                           AND r.improvement_case_id = c.id
                         ORDER BY r.created_at DESC LIMIT 1) AS analysis_id
                FROM improvement_cases c
                WHERE c.id = :case_id AND c.organization_id = :org
                """
            ),
            {"case_id": case_id, "org": ctx.organization_id},
        ).first()
        if case is None:
            raise AppError("not_found", "Improvement case not found", status_code=404)

        plan = conn.execute(
            text(
                """
                SELECT id, status, created_at, updated_at
                FROM action_plans
                WHERE organization_id = :org AND improvement_case_id = :case_id
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"org": ctx.organization_id, "case_id": case_id},
        ).first()
        action_rows = []
        if plan is not None:
            action_rows = conn.execute(
                text(
                    """
                    SELECT a.id, a.description, a.status, a.owner_membership_id,
                           a.due_at, a.is_overdue, a.created_at, a.updated_at,
                           s.id AS sprint_id, s.status AS sprint_status,
                           count(DISTINCT ci.id) AS check_in_count,
                           max(ci.reported_at) AS last_check_in_at,
                           count(DISTINCT imp.id) FILTER (WHERE imp.status = 'open')
                             AS active_impediment_count,
                           floor(extract(epoch FROM (
                             now() - min(imp.opened_at) FILTER (WHERE imp.status = 'open')
                           )) / 3600)::integer AS oldest_impediment_hours,
                           count(DISTINCT dep.id) FILTER (WHERE dep.status = 'active')
                             AS open_dependency_count,
                           count(DISTINCT dep.id) FILTER (
                             WHERE dep.status = 'active' AND pred.due_at < now()
                               AND pred.status NOT IN ('done','cancelled','ineffective_closed')
                           ) AS overdue_dependency_count,
                           count(DISTINCT el.id) FILTER (WHERE el.removed_at IS NULL)
                             AS evidence_count,
                           count(DISTINCT el.id) FILTER (
                             WHERE el.removed_at IS NULL AND e.status = 'approved'
                           ) AS approved_evidence_count
                    FROM action_items a
                    LEFT JOIN agile_sprint_cards sc
                      ON sc.action_item_id = a.id AND sc.removed_at IS NULL
                    LEFT JOIN agile_sprints s ON s.id = sc.sprint_id
                    LEFT JOIN action_execution_check_ins ci ON ci.action_item_id = a.id
                    LEFT JOIN action_impediments imp ON imp.action_item_id = a.id
                    LEFT JOIN action_dependencies dep ON dep.dependent_action_item_id = a.id
                    LEFT JOIN action_items pred ON pred.id = dep.predecessor_action_item_id
                    LEFT JOIN evidence_links el
                      ON el.target_type = 'action_item' AND el.target_id = a.id
                    LEFT JOIN evidences e ON e.id = el.evidence_id
                    WHERE a.organization_id = :org AND a.action_plan_id = :plan
                    GROUP BY a.id, s.id, s.status
                    ORDER BY a.created_at, a.id
                    """
                ),
                {"org": ctx.organization_id, "plan": plan.id},
            ).all()

        measurement_plans, indicators, measurement_refs = _measurement_facts(
            conn, ctx.organization_id, case_id
        )
        outcome = conn.execute(
            text(
                """
                SELECT o.result_direction, o.observed_at, o.observation_statement,
                       o.measurement_basis,
                       count(oom.id) AS linked_measurement_count
                FROM improvement_case_outcome_observations o
                LEFT JOIN outcome_observation_measurements oom
                  ON oom.outcome_observation_id = o.id
                WHERE o.organization_id = :org AND o.improvement_case_id = :case_id
                GROUP BY o.id
                ORDER BY o.observed_at DESC, o.created_at DESC LIMIT 1
                """
            ),
            {"org": ctx.organization_id, "case_id": case_id},
        ).first()

    actions: list[ExecutionActionFacts] = []
    action_refs: list[str] = []
    for index, row in enumerate(action_rows, 1):
        action_ref = _ref("action", index)
        action_refs.extend(action_fact_refs(action_ref))
        is_terminal = row.status in CORE_TERMINAL_ACTION_STATUSES
        actions.append(
            ExecutionActionFacts(
                action_ref=action_ref,
                label=" ".join(row.description.split())[:300],
                status=row.status,
                owner_assigned=row.owner_membership_id is not None,
                sprint_ref=_ref("sprint", index) if row.sprint_id else None,
                sprint_status=row.sprint_status,
                created_at=_utc(row.created_at),
                started_at=_utc(row.last_check_in_at),
                due_at=_utc(row.due_at),
                completed_at=_utc(row.updated_at) if is_terminal else None,
                last_check_in_at=_utc(row.last_check_in_at),
                check_in_count=int(row.check_in_count or 0),
                active_impediment_count=int(row.active_impediment_count or 0),
                oldest_active_impediment_hours=row.oldest_impediment_hours,
                open_dependency_count=int(row.open_dependency_count or 0),
                overdue_dependency_count=int(row.overdue_dependency_count or 0),
                evidence_count=int(row.evidence_count or 0),
                approved_evidence_count=int(row.approved_evidence_count or 0),
                is_overdue=bool(row.is_overdue),
                is_terminal=is_terminal,
                claims_execution=row.status in CORE_EXECUTED_TERMINAL_STATUSES,
            )
        )
    fact_refs = [case_status_ref()]
    latest_analysis_ref = "problem-analysis:latest" if case.analysis_id else None
    plan_fact = None
    if plan is not None:
        fact_refs.append(plan_status_ref())
        plan_fact = ExecutionPlanFacts(
            plan_ref="execution-plan",
            status=plan.status,
            window_start=_utc(plan.created_at),
            window_end=_utc(plan.updated_at) if plan.status in {"completed", "cancelled"} else None,
        )
    fact_refs.extend(action_refs)
    fact_refs.extend(measurement_refs)
    outcome_fact = None
    if outcome is not None:
        fact_refs.append(outcome_direction_ref())
        outcome_fact = OutcomeFacts(
            result_direction=outcome.result_direction,
            observed_at=_utc(outcome.observed_at),
            observation_summary=outcome.observation_statement,
            measurement_basis_summary=outcome.measurement_basis,
            linked_measurement_count=int(outcome.linked_measurement_count or 0),
        )
    return ExecutionIntelligenceInput(
        schema_version="1.0",
        core_organization_id=ctx.organization_id,
        improvement_case_id=case_id,
        request_id=rid,
        correlation_id=correlation_id or rid,
        captured_at=when,
        source=SourceRef(system="qmind-core", component="execution-intelligence"),
        case=ExecutionCaseFacts(
            status=case.status,
            problem_statement=case.problem_statement,
            impact_statement=case.impact_statement,
            related_process=case.related_process,
            latest_problem_analysis_ref=latest_analysis_ref,
        ),
        execution=ExecutionFacts(plan=plan_fact, actions=actions),
        measurement=MeasurementFacts(plans=measurement_plans, indicators=indicators),
        outcome=outcome_fact,
        fact_refs=fact_refs,
    )
