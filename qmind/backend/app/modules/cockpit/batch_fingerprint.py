"""Set-based Execution Intelligence fingerprint assembler for the cockpit."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.modules.agile.schemas import CHECK_IN_STALE_WINDOW_HOURS
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
from app.modules.improvement_cases.fingerprint import (
    fingerprint_execution_intelligence_input,
)
from app.modules.measurements import service as measurements_service
from app.modules.oi.schemas import SourceRef

DEFAULT_CHUNK_SIZE = 100


def _ref(kind: str, position: int) -> str:
    return f"{kind}:{position}"


def _decimal(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


def _chunks(ids: list[UUID], size: int) -> list[list[UUID]]:
    if size < 1:
        raise ValueError("chunk size must be >= 1")
    return [ids[i : i + size] for i in range(0, len(ids), size)] or [[]]


def _assemble_case_input(
    *,
    org_id: UUID,
    case_id: UUID,
    case_row,
    plan_row,
    action_rows: list,
    measurement_plan_rows: list,
    indicator_plan: dict[UUID, UUID],
    evaluations: list,
    outcome_row,
    captured_at: datetime,
) -> ExecutionIntelligenceInput:
    rid = str(uuid4())
    when = captured_at.astimezone(UTC)

    plan_refs = {
        row.id: _ref("measurement-plan", i)
        for i, row in enumerate(measurement_plan_rows, 1)
    }
    plans = [
        MeasurementPlanFacts(
            plan_ref=plan_refs[row.id],
            status="completed" if row.status == "closed" else row.status,
        )
        for row in measurement_plan_rows
    ]
    indicators: list[MeasurementIndicatorFacts] = []
    measurement_refs: list[str] = []
    for index, (row, facts, ev) in enumerate(
        sorted(
            evaluations,
            key=lambda item: (item[1].code, str(item[0].id)),
        ),
        1,
    ):
        indicator_ref = _ref("indicator", index)
        plan_ref = plan_refs[indicator_plan[row.id]]
        indicators.append(
            MeasurementIndicatorFacts(
                indicator_ref=indicator_ref,
                plan_ref=plan_ref,
                name=facts.name,
                unit=(
                    str(facts.unit_label).strip()
                    if facts.unit_label and str(facts.unit_label).strip()
                    else "n/a"
                ),
                direction=facts.direction,
                target_value=_decimal(facts.target_value),
                target_min=_decimal(facts.target_min),
                target_max=_decimal(facts.target_max),
                baseline_value=_decimal(facts.baseline_value),
                baseline_at=_utc(facts.baseline_at),
                latest_value=_decimal(facts.latest_value),
                latest_measured_at=_utc(facts.latest_measured_at),
                measurement_posture=(
                    "overdue"
                    if ev.is_measurement_overdue
                    else "awaiting_baseline"
                    if ev.baseline_status == "missing"
                    else "awaiting_measurement"
                    if facts.latest_value is None
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
                comparable_reading_count=facts.measurement_count,
            )
        )
        measurement_refs.extend(indicator_fact_refs(indicator_ref))

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
    latest_analysis_ref = "problem-analysis:latest" if case_row.analysis_id else None
    plan_fact = None
    if plan_row is not None:
        fact_refs.append(plan_status_ref())
        plan_fact = ExecutionPlanFacts(
            plan_ref="execution-plan",
            status=plan_row.status,
            window_start=_utc(plan_row.created_at),
            window_end=(
                _utc(plan_row.updated_at)
                if plan_row.status in {"completed", "cancelled"}
                else None
            ),
        )
    fact_refs.extend(action_refs)
    fact_refs.extend(measurement_refs)
    outcome_fact = None
    if outcome_row is not None:
        fact_refs.append(outcome_direction_ref())
        outcome_fact = OutcomeFacts(
            result_direction=outcome_row.result_direction,
            observed_at=_utc(outcome_row.observed_at),
            observation_summary=outcome_row.observation_statement,
            measurement_basis_summary=outcome_row.measurement_basis,
            linked_measurement_count=int(outcome_row.linked_measurement_count or 0),
        )
    return ExecutionIntelligenceInput(
        schema_version="1.0",
        core_organization_id=org_id,
        improvement_case_id=case_id,
        request_id=rid,
        correlation_id=rid,
        captured_at=when,
        source=SourceRef(system="qmind-core", component="execution-intelligence"),
        case=ExecutionCaseFacts(
            status=case_row.status,
            problem_statement=case_row.problem_statement,
            impact_statement=case_row.impact_statement,
            related_process=case_row.related_process,
            latest_problem_analysis_ref=latest_analysis_ref,
        ),
        execution=ExecutionFacts(plan=plan_fact, actions=actions),
        measurement=MeasurementFacts(plans=plans, indicators=indicators),
        outcome=outcome_fact,
        fact_refs=fact_refs,
    )


def _load_chunk(
    conn: Connection,
    org_id: UUID,
    case_ids: list[UUID],
    *,
    captured_at: datetime,
) -> dict[UUID, tuple[ExecutionIntelligenceInput, str]]:
    if not case_ids:
        return {}

    case_rows = conn.execute(
        text(
            """
            SELECT c.id, c.status, c.problem_statement, c.impact_statement,
                   c.related_process, c.updated_at,
                   (
                     SELECT r.id FROM improvement_case_analysis_runs r
                     WHERE r.organization_id = c.organization_id
                       AND r.improvement_case_id = c.id
                     ORDER BY r.created_at DESC LIMIT 1
                   ) AS analysis_id
            FROM improvement_cases c
            WHERE c.organization_id = :org AND c.id = ANY(:ids)
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    cases = {row.id: row for row in case_rows}

    plan_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (improvement_case_id)
                   id, improvement_case_id, status, created_at, updated_at
            FROM action_plans
            WHERE organization_id = :org AND improvement_case_id = ANY(:ids)
            ORDER BY improvement_case_id, created_at DESC, id DESC
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    plans_by_case = {row.improvement_case_id: row for row in plan_rows}
    plan_ids = [row.id for row in plan_rows]

    actions_by_plan: dict[UUID, list] = {pid: [] for pid in plan_ids}
    if plan_ids:
        action_rows = conn.execute(
            text(
                """
                SELECT a.id, a.action_plan_id, a.description, a.status,
                       a.owner_membership_id, a.due_at, a.is_overdue,
                       a.created_at, a.updated_at,
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
                WHERE a.organization_id = :org AND a.action_plan_id = ANY(:plans)
                GROUP BY a.id, s.id, s.status
                ORDER BY a.action_plan_id, a.created_at, a.id
                """
            ),
            {"org": org_id, "plans": plan_ids},
        ).all()
        for row in action_rows:
            actions_by_plan.setdefault(row.action_plan_id, []).append(row)

    mplan_rows = conn.execute(
        text(
            """
            SELECT id, improvement_case_id, status, created_at
            FROM action_measurement_plans
            WHERE organization_id = :org AND improvement_case_id = ANY(:ids)
            ORDER BY improvement_case_id, created_at, id
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    mplans_by_case: dict[UUID, list] = {cid: [] for cid in case_ids}
    for row in mplan_rows:
        mplans_by_case.setdefault(row.improvement_case_id, []).append(row)
    mplan_ids = [row.id for row in mplan_rows]

    indicator_plan: dict[UUID, UUID] = {}
    if mplan_ids:
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
            {"org": org_id, "plan_ids": mplan_ids},
        ).all():
            indicator_plan[row.id] = row.measurement_plan_id

    # Match single-case builder: measurement clock is "now", not captured_at
    # (captured_at is envelope-only and excluded from the fingerprint).
    triples = (
        measurements_service._evaluate(
            conn,
            org_id,
            where="AND p.improvement_case_id = ANY(:ids)",
            params={"ids": case_ids},
        )
        if case_ids
        else []
    )
    mplan_to_case = {row.id: row.improvement_case_id for row in mplan_rows}
    evals_by_case: dict[UUID, list] = {cid: [] for cid in case_ids}
    for row, facts, ev in triples:
        plan_id = indicator_plan.get(row.id)
        case_id = mplan_to_case.get(plan_id) if plan_id is not None else None
        if case_id is not None:
            evals_by_case.setdefault(case_id, []).append((row, facts, ev))

    outcome_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (o.improvement_case_id)
                   o.improvement_case_id, o.result_direction, o.observed_at,
                   o.observation_statement, o.measurement_basis,
                   (
                     SELECT count(*) FROM outcome_observation_measurements oom
                     WHERE oom.outcome_observation_id = o.id
                   ) AS linked_measurement_count
            FROM improvement_case_outcome_observations o
            WHERE o.organization_id = :org AND o.improvement_case_id = ANY(:ids)
            ORDER BY o.improvement_case_id, o.observed_at DESC, o.created_at DESC
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    outcomes = {row.improvement_case_id: row for row in outcome_rows}

    out: dict[UUID, tuple[ExecutionIntelligenceInput, str]] = {}
    for case_id in case_ids:
        case_row = cases.get(case_id)
        if case_row is None:
            continue
        plan_row = plans_by_case.get(case_id)
        action_rows = (
            actions_by_plan.get(plan_row.id, []) if plan_row is not None else []
        )
        snapshot = _assemble_case_input(
            org_id=org_id,
            case_id=case_id,
            case_row=case_row,
            plan_row=plan_row,
            action_rows=action_rows,
            measurement_plan_rows=mplans_by_case.get(case_id, []),
            indicator_plan=indicator_plan,
            evaluations=evals_by_case.get(case_id, []),
            outcome_row=outcomes.get(case_id),
            captured_at=captured_at,
        )
        out[case_id] = (snapshot, fingerprint_execution_intelligence_input(snapshot))
    return out


def batch_fingerprints(
    conn: Connection,
    org_id: UUID,
    case_ids: list[UUID],
    *,
    captured_at: datetime | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[UUID, tuple[ExecutionIntelligenceInput, str]]:
    """Load many cases with set-based SQL; match single-case builder fingerprints."""
    when = (captured_at or datetime.now(UTC)).astimezone(UTC)
    merged: dict[UUID, tuple[ExecutionIntelligenceInput, str]] = {}
    for chunk in _chunks(list(case_ids), chunk_size):
        if not chunk:
            continue
        merged.update(_load_chunk(conn, org_id, chunk, captured_at=when))
    return merged


def case_action_aggregates(
    snapshot: ExecutionIntelligenceInput,
    *,
    as_of: datetime,
) -> dict:
    """Derive cockpit counters from an assembled EI snapshot."""
    actions = snapshot.execution.actions
    completed = sum(1 for a in actions if a.is_terminal)
    overdue = sum(1 for a in actions if a.is_overdue and not a.is_terminal)
    impediments = sum(a.active_impediment_count for a in actions)
    open_deps = sum(a.open_dependency_count for a in actions)
    overdue_deps = sum(a.overdue_dependency_count for a in actions)
    claims = [a for a in actions if a.claims_execution]
    claims_without = sum(1 for a in claims if a.approved_evidence_count < 1)
    stale_cut = as_of.astimezone(UTC).timestamp() - (CHECK_IN_STALE_WINDOW_HOURS * 3600)
    stale_check_ins = 0
    for a in actions:
        if a.is_terminal:
            continue
        last = a.last_check_in_at
        if last is None or last.astimezone(UTC).timestamp() < stale_cut:
            stale_check_ins += 1
    due_dates = [a.due_at for a in actions if a.due_at and not a.is_terminal]
    last_activity = None
    for a in actions:
        for ts in (a.last_check_in_at, a.completed_at, a.created_at):
            if ts is not None and (last_activity is None or ts > last_activity):
                last_activity = ts
    if snapshot.outcome is not None:
        if last_activity is None or snapshot.outcome.observed_at > last_activity:
            last_activity = snapshot.outcome.observed_at

    indicators = snapshot.measurement.indicators
    if not indicators:
        m_posture, t_posture, subst = "not_planned", "unknown", "none"
    else:
        posture_rank = (
            "awaiting_baseline",
            "overdue",
            "awaiting_measurement",
            "on_time",
        )
        seen = {i.measurement_posture for i in indicators}
        m_posture = next((p for p in posture_rank if p in seen), "on_time")
        met = any(i.target_posture == "met" for i in indicators)
        not_met = any(i.target_posture == "not_met" for i in indicators)
        if met and not_met:
            t_posture = "mixed"
        elif met:
            t_posture = "met"
        elif not_met:
            t_posture = "not_met"
        else:
            t_posture = "unknown"
        levels = {i.substantiation for i in indicators}
        if "none" in levels:
            subst = "none"
        elif "partial" in levels:
            subst = "partial"
        else:
            subst = "verified"

    return {
        "action_count": len(actions),
        "completed_action_count": completed,
        "overdue_action_count": overdue,
        "active_impediment_count": impediments,
        "open_dependency_count": open_deps,
        "overdue_dependency_count": overdue_deps,
        "claims_execution_count": len(claims),
        "claims_without_approved_evidence": claims_without,
        "stale_check_in_count": stale_check_ins,
        "has_stale_check_in": stale_check_ins > 0,
        "oldest_due_at": min(due_dates) if due_dates else None,
        "last_activity_at": last_activity,
        "measurement_posture": m_posture,
        "target_posture": t_posture,
        "substantiation": subst,
        "overdue_indicator_count": sum(
            1 for i in indicators if i.is_measurement_overdue
        ),
        "indicator_count": len(indicators),
        "has_outcome": snapshot.outcome is not None,
        "outcome_direction": (
            snapshot.outcome.result_direction if snapshot.outcome else None
        ),
        "outcome_observed_at": (
            snapshot.outcome.observed_at if snapshot.outcome else None
        ),
        "has_active_execution": any(not a.is_terminal for a in actions),
        "all_actions_terminal": bool(actions) and all(a.is_terminal for a in actions),
    }
