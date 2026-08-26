"""Cockpit read-model service — projection only; never calls QMind OI."""

from __future__ import annotations

import base64
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.cockpit.batch_fingerprint import (
    DEFAULT_CHUNK_SIZE,
    batch_fingerprints,
    case_action_aggregates,
)
from app.modules.cockpit.priority import (
    CasePrioritySnapshot,
    compute_priority,
    priority_band_label,
    sort_key_for_case,
)
from app.modules.cockpit.schemas import (
    PRIORITY_BAND_LABELS,
    PROBLEM_LABEL_MAX,
    ActivityWindowDays,
    CaseTotalsOut,
    CockpitActivityItemOut,
    CockpitActivityPageOut,
    CockpitCaseItemOut,
    CockpitCasesPageOut,
    CockpitCoverage,
    CockpitPriorityBand,
    CockpitScopeOut,
    CockpitSummaryOut,
    EvidenceTotalsOut,
    ExecutionTotalsOut,
    IntelligenceCoverageOut,
    IntelligenceFreshness,
    LabeledCount,
    MeasurementTotalsOut,
    SignalCountOut,
)
from app.modules.improvement_cases.closure_readiness import evaluate_closure_readiness
from app.modules.improvement_cases.evolution_service import _READ_ROLES
from app.modules.improvement_cases.fingerprint import fingerprint_problem_context_input
from app.modules.improvement_cases.problem_context_builder import build_problem_context_input
from app.modules.orgs import service as orgs_service
from app.modules.orgs.service import require_role

FRESHNESS_LABELS = {
    "current": "Atual",
    "stale": "Desatualizada",
    "never_analyzed": "Nunca analisada",
}
ACTIVITY_LABELS = {
    "check_in_recorded": "Check-in registrado",
    "impediment_opened": "Impedimento aberto",
    "impediment_resolved": "Impedimento resolvido",
    "measurement_recorded": "Medição registrada",
    "measurement_corrected": "Medição corrigida",
    "outcome_observed": "Resultado observado",
    "execution_intelligence_run": "Análise de execução gerada",
    "case_status_changed": "Status do caso alterado",
    "action_status_changed": "Status da ação alterado",
}


def _as_of() -> datetime:
    return datetime.now(UTC)


def _truncate(text_value: str | None, limit: int = PROBLEM_LABEL_MAX) -> str:
    raw = " ".join((text_value or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "…"


def _encode_cursor(org_id: UUID, payload: dict[str, Any]) -> str:
    body = {"org_id": str(org_id), **payload}
    raw = json.dumps(body, separators=(",", ":"), default=str).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(org_id: UUID, cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AppError("invalid_cursor", "Invalid pagination cursor", status_code=422) from exc
    cursor_org = data.get("org_id")
    if cursor_org != str(org_id):
        raise AppError(
            "cursor_org_mismatch",
            "Cursor does not belong to the current organization",
            status_code=403,
        )
    return data


def _labeled(counter: Counter[str], labels: dict[str, str], unit: str) -> list[LabeledCount]:
    return [
        LabeledCount(code=code, label=labels.get(code, code), count=count, unit=unit)
        for code, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _load_latest_ei_runs(conn, org_id: UUID, case_ids: list[UUID]) -> dict[UUID, Any]:
    if not case_ids:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (improvement_case_id)
                   id, improvement_case_id, generated_at, mechanism_version,
                   input_fingerprint, result
            FROM improvement_case_execution_intelligence_runs
            WHERE organization_id = :org AND improvement_case_id = ANY(:ids)
            ORDER BY improvement_case_id, created_at DESC
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    return {row.improvement_case_id: row for row in rows}


def _load_latest_analysis_fingerprints(
    conn, org_id: UUID, case_ids: list[UUID]
) -> dict[UUID, str]:
    if not case_ids:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (improvement_case_id)
                   improvement_case_id, input_fingerprint
            FROM improvement_case_analysis_runs
            WHERE organization_id = :org AND improvement_case_id = ANY(:ids)
            ORDER BY improvement_case_id, created_at DESC
            """
        ),
        {"org": org_id, "ids": case_ids},
    ).all()
    return {row.improvement_case_id: row.input_fingerprint for row in rows}


def _freshness(current_fp: str, run) -> IntelligenceFreshness:
    if run is None:
        return "never_analyzed"
    if run.input_fingerprint == current_fp:
        return "current"
    return "stale"


def _parse_result(run) -> dict:
    if run is None:
        return {}
    result = run.result
    if isinstance(result, str):
        return json.loads(result)
    if hasattr(result, "keys"):
        return dict(result)
    return json.loads(json.dumps(result))


def _closure_from_agg(
    agg: dict,
    *,
    has_problem_analysis: bool,
    problem_analysis_is_stale: bool,
) -> tuple[str, str]:
    return evaluate_closure_readiness(
        has_problem_analysis=has_problem_analysis,
        problem_analysis_is_stale=problem_analysis_is_stale,
        action_count=agg["action_count"],
        has_incomplete_actions=(
            agg["action_count"] >= 1 and not agg["all_actions_terminal"]
        ),
        has_outcome=agg["has_outcome"],
        outcome_direction=agg["outcome_direction"],
        measurement_posture=agg["measurement_posture"],
    )


def _project_cases(
    ctx: OrgContext,
    *,
    as_of: datetime,
    case_status: list[str] | None = None,
    related_process: str | None = None,
    search: str | None = None,
    include_closed: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[list[CockpitCaseItemOut], CockpitCoverage, dict[UUID, dict]]:
    require_role(ctx, *_READ_ROLES)
    org_id = ctx.organization_id
    with tenant_connection(org_id) as conn:
        params: dict[str, Any] = {"org": org_id}
        where = ["c.organization_id = :org"]
        if case_status:
            where.append("c.status = ANY(:statuses)")
            params["statuses"] = case_status
        elif not include_closed:
            where.append("c.status <> 'closed'")
        if related_process:
            where.append("c.related_process ILIKE :process")
            params["process"] = f"%{related_process.strip()}%"
        if search:
            where.append(
                "(c.problem_statement ILIKE :q OR c.related_process ILIKE :q)"
            )
            params["q"] = f"%{search.strip()}%"
        rows = conn.execute(
            text(
                f"""
                SELECT c.id, c.status, c.problem_statement, c.impact_statement,
                       c.related_process, c.updated_at
                FROM improvement_cases c
                WHERE {' AND '.join(where)}
                ORDER BY c.updated_at DESC, c.id
                """
            ),
            params,
        ).all()
        case_ids = [row.id for row in rows]
        cases = {row.id: row for row in rows}
        fingerprints = batch_fingerprints(
            conn, org_id, case_ids, captured_at=as_of, chunk_size=chunk_size
        )
        runs = _load_latest_ei_runs(conn, org_id, case_ids)
        analysis_fps = _load_latest_analysis_fingerprints(conn, org_id, case_ids)

    profile = orgs_service.get_or_create_organization_profile(ctx)

    items: list[CockpitCaseItemOut] = []
    extras: dict[UUID, dict] = {}
    for case_id in case_ids:
        case = cases[case_id]
        packed = fingerprints.get(case_id)
        if packed is None:
            continue
        snapshot, fp = packed
        run = runs.get(case_id)
        freshness = _freshness(fp, run)
        result = _parse_result(run)
        agg = case_action_aggregates(snapshot, as_of=as_of)
        if agg["last_activity_at"] is None:
            agg["last_activity_at"] = case.updated_at
        signals = result.get("signals") or []
        current_attention = 0
        if freshness == "current":
            current_attention = sum(
                1 for s in signals if (s.get("level") if isinstance(s, dict) else getattr(s, "level", None)) == "attention"
            )
        posture = result.get("execution_posture")
        awaiting_obs = (
            case.status == "reviewing"
            or posture == "awaiting_result_evaluation"
            or (agg["all_actions_terminal"] and not agg["has_outcome"])
        )
        snap = CasePrioritySnapshot(
            case_status=case.status,
            intelligence_freshness=freshness,
            execution_posture=posture,
            has_overdue_action=agg["overdue_action_count"] > 0,
            has_active_impediment=agg["active_impediment_count"] > 0,
            has_open_dependency=agg["open_dependency_count"] > 0,
            has_overdue_dependency=agg["overdue_dependency_count"] > 0,
            measurement_posture=agg["measurement_posture"],
            target_posture=agg["target_posture"],
            claims_execution_without_approved_evidence=agg[
                "claims_without_approved_evidence"
            ]
            > 0,
            has_current_attention_signal=current_attention > 0,
            has_stale_check_in=agg["has_stale_check_in"],
            awaiting_human_observation=awaiting_obs,
            has_outcome_observation=agg["has_outcome"],
            has_active_execution=agg["has_active_execution"],
        )
        band, reasons = compute_priority(snap)
        stored_analysis_fp = analysis_fps.get(case_id)
        has_problem_analysis = stored_analysis_fp is not None
        current_problem_fp = fingerprint_problem_context_input(
            build_problem_context_input(
                case_id=case_id,
                problem_statement=case.problem_statement or "",
                impact_statement=case.impact_statement or "",
                related_process=case.related_process or "",
                profile=profile,
                core_organization_id=org_id,
            )
        )
        problem_analysis_is_stale = (
            has_problem_analysis and stored_analysis_fp != current_problem_fp
        )
        readiness, readiness_reason = _closure_from_agg(
            agg,
            has_problem_analysis=has_problem_analysis,
            problem_analysis_is_stale=problem_analysis_is_stale,
        )
        item = CockpitCaseItemOut(
            case_id=case_id,
            problem_label=_truncate(case.problem_statement),
            related_process=case.related_process,
            case_status=case.status,
            priority_band=band,
            priority_band_label=priority_band_label(band),
            priority_reasons=reasons,
            action_count=agg["action_count"],
            completed_action_count=agg["completed_action_count"],
            overdue_action_count=agg["overdue_action_count"],
            active_impediment_count=agg["active_impediment_count"],
            open_dependency_count=agg["open_dependency_count"],
            overdue_dependency_count=agg["overdue_dependency_count"],
            last_activity_at=agg["last_activity_at"],
            oldest_due_at=agg["oldest_due_at"],
            measurement_posture=agg["measurement_posture"],
            target_posture=agg["target_posture"],
            substantiation=agg["substantiation"],
            outcome_result_direction=agg["outcome_direction"],
            outcome_observed_at=agg["outcome_observed_at"],
            execution_posture=posture,
            intelligence_generated_at=run.generated_at if run else None,
            intelligence_mechanism_version=run.mechanism_version if run else None,
            intelligence_signal_count=len(signals) if run else 0,
            intelligence_freshness=freshness,
            intelligence_freshness_label=FRESHNESS_LABELS[freshness],
            closure_readiness=readiness,
            closure_readiness_reason=readiness_reason,
            current_attention_signal_count=current_attention,
        )
        items.append(item)
        extras[case_id] = {
            "fingerprint": fp,
            "run": run,
            "result": result,
            "agg": agg,
            "freshness": freshness,
            "signals": signals,
        }

    coverage = CockpitCoverage(
        analyzed_count=len(case_ids),
        included_count=len(items),
        excluded_count=0,
        complete=True,
    )
    return items, coverage, extras


def _filter_items(
    items: list[CockpitCaseItemOut],
    extras: dict[UUID, dict],
    *,
    priority_band: CockpitPriorityBand | None = None,
    execution_posture: str | None = None,
    intelligence_freshness: IntelligenceFreshness | None = None,
    measurement_posture: str | None = None,
    target_posture: str | None = None,
    signal_category: str | None = None,
    ready_for_review: bool | None = None,
    has_overdue_actions: bool | None = None,
    has_active_impediment: bool | None = None,
) -> list[CockpitCaseItemOut]:
    out: list[CockpitCaseItemOut] = []
    for item in items:
        if priority_band and item.priority_band != priority_band:
            continue
        if execution_posture and item.execution_posture != execution_posture:
            continue
        if intelligence_freshness and item.intelligence_freshness != intelligence_freshness:
            continue
        if measurement_posture and item.measurement_posture != measurement_posture:
            continue
        if target_posture and item.target_posture != target_posture:
            continue
        if ready_for_review is True and item.closure_readiness != "ready_for_review":
            continue
        if ready_for_review is False and item.closure_readiness == "ready_for_review":
            continue
        if has_overdue_actions is True and item.overdue_action_count < 1:
            continue
        if has_overdue_actions is False and item.overdue_action_count >= 1:
            continue
        if has_active_impediment is True and item.active_impediment_count < 1:
            continue
        if has_active_impediment is False and item.active_impediment_count >= 1:
            continue
        if signal_category:
            meta = extras.get(item.case_id) or {}
            signals = meta.get("signals") or []
            freshness = item.intelligence_freshness
            if freshness != "current":
                continue
            cats = {
                (s.get("category") if isinstance(s, dict) else getattr(s, "category", None))
                for s in signals
            }
            if signal_category not in cats:
                continue
        out.append(item)
    return out


def _sort_items(items: list[CockpitCaseItemOut]) -> list[CockpitCaseItemOut]:
    return sorted(
        items,
        key=lambda item: sort_key_for_case(
            band=item.priority_band,
            oldest_due_at=item.oldest_due_at,
            last_activity_at=item.last_activity_at,
            case_id=str(item.case_id),
        ),
    )


def _sort_key_encoded(item: CockpitCaseItemOut) -> tuple[int, str, str, str]:
    key = sort_key_for_case(
        band=item.priority_band,
        oldest_due_at=item.oldest_due_at,
        last_activity_at=item.last_activity_at,
        case_id=str(item.case_id),
    )
    return (
        key[0],
        key[1].isoformat() if hasattr(key[1], "isoformat") else str(key[1]),
        key[2].isoformat() if hasattr(key[2], "isoformat") else str(key[2]),
        key[3],
    )


def list_cases(
    ctx: OrgContext,
    *,
    case_status: list[str] | None = None,
    priority_band: CockpitPriorityBand | None = None,
    execution_posture: str | None = None,
    intelligence_freshness: IntelligenceFreshness | None = None,
    measurement_posture: str | None = None,
    target_posture: str | None = None,
    signal_category: str | None = None,
    related_process: str | None = None,
    search: str | None = None,
    ready_for_review: bool | None = None,
    has_overdue_actions: bool | None = None,
    has_active_impediment: bool | None = None,
    limit: int = 25,
    cursor: str | None = None,
    as_of: datetime | None = None,
) -> CockpitCasesPageOut:
    if limit < 1 or limit > 100:
        raise AppError("invalid_limit", "limit must be between 1 and 100", status_code=422)
    when = as_of or _as_of()
    cursor_data = _decode_cursor(ctx.organization_id, cursor)
    include_closed = bool(case_status and "closed" in case_status)
    items, coverage, extras = _project_cases(
        ctx,
        as_of=when,
        case_status=case_status,
        related_process=related_process,
        search=search,
        include_closed=include_closed,
    )
    filtered = _sort_items(
        _filter_items(
            items,
            extras,
            priority_band=priority_band,
            execution_posture=execution_posture,
            intelligence_freshness=intelligence_freshness,
            measurement_posture=measurement_posture,
            target_posture=target_posture,
            signal_category=signal_category,
            ready_for_review=ready_for_review,
            has_overdue_actions=has_overdue_actions,
            has_active_impediment=has_active_impediment,
        )
    )
    if cursor_data:
        cursor_key = (
            int(cursor_data.get("band_rank", 0)),
            str(cursor_data.get("oldest_due_at") or "9999"),
            str(cursor_data.get("last_activity_at") or "9999"),
            str(cursor_data.get("case_id") or ""),
        )

        def _after(item: CockpitCaseItemOut) -> bool:
            return _sort_key_encoded(item) > cursor_key

        filtered = [item for item in filtered if _after(item)]

    page = filtered[:limit]
    next_cursor = None
    if len(filtered) > limit:
        last = page[-1]
        key = _sort_key_encoded(last)
        next_cursor = _encode_cursor(
            ctx.organization_id,
            {
                "band_rank": key[0],
                "oldest_due_at": key[1],
                "last_activity_at": key[2],
                "case_id": key[3],
            },
        )
    return CockpitCasesPageOut(
        as_of=when,
        items=page,
        limit=limit,
        next_cursor=next_cursor,
        coverage=coverage,
    )


_ACTIVITY_UNION_SQL = """
WITH events AS (
    SELECT ci.reported_at AS occurred_at,
           'check_in_recorded'::text AS event_type,
           a.improvement_case_id AS case_id,
           ci.action_item_id AS action_item_id,
           ci.id AS source_id,
           'Check-in de execução registrado'::text AS summary
    FROM action_execution_check_ins ci
    JOIN action_items ai ON ai.id = ci.action_item_id
    JOIN action_plans a ON a.id = ai.action_plan_id
    WHERE ci.organization_id = :org AND ci.reported_at >= :since

    UNION ALL

    SELECT i.opened_at AS occurred_at,
           'impediment_opened'::text AS event_type,
           a.improvement_case_id AS case_id,
           i.action_item_id AS action_item_id,
           i.id AS source_id,
           'Impedimento aberto'::text AS summary
    FROM action_impediments i
    JOIN action_items ai ON ai.id = i.action_item_id
    JOIN action_plans a ON a.id = ai.action_plan_id
    WHERE i.organization_id = :org AND i.opened_at >= :since

    UNION ALL

    SELECT i.resolved_at AS occurred_at,
           'impediment_resolved'::text AS event_type,
           a.improvement_case_id AS case_id,
           i.action_item_id AS action_item_id,
           i.id AS source_id,
           'Impedimento resolvido'::text AS summary
    FROM action_impediments i
    JOIN action_items ai ON ai.id = i.action_item_id
    JOIN action_plans a ON a.id = ai.action_plan_id
    WHERE i.organization_id = :org
      AND i.resolved_at IS NOT NULL
      AND i.resolved_at >= :since

    UNION ALL

    SELECT mr.recorded_at AS occurred_at,
           CASE
             WHEN mr.supersedes_measurement_id IS NOT NULL
               THEN 'measurement_corrected'::text
             ELSE 'measurement_recorded'::text
           END AS event_type,
           p.improvement_case_id AS case_id,
           NULL::uuid AS action_item_id,
           mr.id AS source_id,
           CASE
             WHEN mr.supersedes_measurement_id IS NOT NULL
               THEN 'Medição corrigida'::text
             ELSE 'Medição registrada'::text
           END AS summary
    FROM measurement_records mr
    JOIN action_measurement_plans p ON p.id = mr.measurement_plan_id
    WHERE mr.organization_id = :org AND mr.recorded_at >= :since

    UNION ALL

    SELECT observed_at AS occurred_at,
           'outcome_observed'::text AS event_type,
           improvement_case_id AS case_id,
           NULL::uuid AS action_item_id,
           id AS source_id,
           'Observação de resultado registrada'::text AS summary
    FROM improvement_case_outcome_observations
    WHERE organization_id = :org AND observed_at >= :since

    UNION ALL

    SELECT created_at AS occurred_at,
           'execution_intelligence_run'::text AS event_type,
           improvement_case_id AS case_id,
           NULL::uuid AS action_item_id,
           id AS source_id,
           'Interpretação de execução registrada'::text AS summary
    FROM improvement_case_execution_intelligence_runs
    WHERE organization_id = :org AND created_at >= :since
)
SELECT occurred_at, event_type, case_id, action_item_id, source_id, summary
FROM events
WHERE (
    :has_seek = 0
    OR (
        occurred_at, event_type, case_id::text,
        coalesce(action_item_id::text, ''), source_id::text
    ) < (
        CAST(:seek_occurred_at AS timestamptz),
        CAST(:seek_event_type AS text),
        CAST(:seek_case_id AS text),
        CAST(:seek_action_item_id AS text),
        CAST(:seek_source_id AS text)
    )
)
ORDER BY occurred_at DESC, event_type DESC, case_id DESC,
         coalesce(action_item_id::text, '') DESC, source_id DESC
LIMIT :lim
"""


def _activity_items(
    conn,
    org_id: UUID,
    *,
    since: datetime,
    limit: int,
    seek: dict[str, Any] | None = None,
) -> list[tuple[CockpitActivityItemOut, str]]:
    params: dict[str, Any] = {
        "org": org_id,
        "since": since,
        "lim": limit,
        "has_seek": 0,
        "seek_occurred_at": since,
        "seek_event_type": "",
        "seek_case_id": "",
        "seek_action_item_id": "",
        "seek_source_id": "",
    }
    if seek and seek.get("occurred_at"):
        stamp = seek["occurred_at"]
        if isinstance(stamp, str):
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        params["has_seek"] = 1
        params["seek_occurred_at"] = stamp
        params["seek_event_type"] = str(seek.get("event_type") or "")
        params["seek_case_id"] = str(seek.get("case_id") or "")
        params["seek_action_item_id"] = str(seek.get("action_item_id") or "")
        params["seek_source_id"] = str(seek.get("source_id") or "")

    rows = conn.execute(text(_ACTIVITY_UNION_SQL), params).all()
    items: list[tuple[CockpitActivityItemOut, str]] = []
    for row in rows:
        code = row.event_type
        items.append(
            (
                CockpitActivityItemOut(
                    event_type=code,
                    event_type_label=ACTIVITY_LABELS.get(code, code),
                    occurred_at=row.occurred_at,
                    summary=row.summary,
                    case_id=row.case_id,
                    action_item_id=row.action_item_id,
                ),
                str(row.source_id),
            )
        )
    return items


def list_activity(
    ctx: OrgContext,
    *,
    activity_window_days: ActivityWindowDays = 30,
    limit: int = 25,
    cursor: str | None = None,
    as_of: datetime | None = None,
) -> CockpitActivityPageOut:
    require_role(ctx, *_READ_ROLES)
    if limit < 1 or limit > 100:
        raise AppError("invalid_limit", "limit must be between 1 and 100", status_code=422)
    when = as_of or _as_of()
    cursor_data = _decode_cursor(ctx.organization_id, cursor)
    since = when - timedelta(days=int(activity_window_days))
    fetch_limit = limit + 1
    with tenant_connection(ctx.organization_id) as conn:
        packed = _activity_items(
            conn,
            ctx.organization_id,
            since=since,
            limit=fetch_limit,
            seek=cursor_data,
        )
    page_packed = packed[:limit]
    page = [item for item, _sid in page_packed]
    next_cursor = None
    if len(packed) > limit:
        last_item, last_sid = page_packed[-1]
        next_cursor = _encode_cursor(
            ctx.organization_id,
            {
                "occurred_at": last_item.occurred_at.isoformat(),
                "event_type": last_item.event_type,
                "case_id": str(last_item.case_id) if last_item.case_id else "",
                "action_item_id": (
                    str(last_item.action_item_id) if last_item.action_item_id else ""
                ),
                "source_id": last_sid,
            },
        )
    return CockpitActivityPageOut(
        as_of=when,
        activity_window_days=activity_window_days,
        items=page,
        limit=limit,
        next_cursor=next_cursor,
        coverage=CockpitCoverage(
            analyzed_count=len(page),
            included_count=len(page),
            complete=True,
        ),
    )


def get_summary(
    ctx: OrgContext,
    *,
    activity_window_days: ActivityWindowDays = 30,
    as_of: datetime | None = None,
) -> CockpitSummaryOut:
    require_role(ctx, *_READ_ROLES)
    when = as_of or _as_of()
    # Queue scope: non-closed. Totals also need org-wide status counts.
    items, coverage, extras = _project_cases(ctx, as_of=when, include_closed=False)
    with tenant_connection(ctx.organization_id) as conn:
        status_rows = conn.execute(
            text(
                """
                SELECT status, count(*)::int AS n
                FROM improvement_cases
                WHERE organization_id = :org
                GROUP BY status
                """
            ),
            {"org": ctx.organization_id},
        ).all()
    status_counts = {row.status: row.n for row in status_rows}
    total = sum(status_counts.values())
    closed = status_counts.get("closed", 0)
    reviewing = status_counts.get("reviewing", 0)
    ready = sum(1 for i in items if i.closure_readiness == "ready_for_review")

    priority_counter: Counter[str] = Counter(i.priority_band for i in items)
    for band in PRIORITY_BAND_LABELS:
        priority_counter.setdefault(band, 0)

    exec_totals = ExecutionTotalsOut(
        active_actions=sum(
            i.action_count - i.completed_action_count for i in items
        ),
        completed_actions=sum(i.completed_action_count for i in items),
        overdue_actions=sum(i.overdue_action_count for i in items),
        blocked_cases=sum(1 for i in items if i.active_impediment_count > 0),
        active_impediments=sum(i.active_impediment_count for i in items),
        open_dependencies=sum(i.open_dependency_count for i in items),
        overdue_dependencies=sum(i.overdue_dependency_count for i in items),
        actions_without_recent_check_in=sum(
            (extras.get(i.case_id) or {}).get("agg", {}).get("stale_check_in_count", 0)
            for i in items
        ),
    )
    claims = sum(
        (extras.get(i.case_id) or {}).get("agg", {}).get("claims_execution_count", 0)
        for i in items
    )
    claims_without = sum(
        (extras.get(i.case_id) or {})
        .get("agg", {})
        .get("claims_without_approved_evidence", 0)
        for i in items
    )
    evidence = EvidenceTotalsOut(
        claims_execution_actions=claims,
        with_approved_evidence=max(claims - claims_without, 0),
        without_approved_evidence=claims_without,
    )

    m_posture = Counter(i.measurement_posture for i in items)
    t_posture = Counter(i.target_posture for i in items)
    subst = Counter(i.substantiation for i in items)
    overdue_indicators = sum(
        (extras.get(i.case_id) or {}).get("agg", {}).get("overdue_indicator_count", 0)
        for i in items
    )
    measurement = MeasurementTotalsOut(
        by_measurement_posture=_labeled(
            m_posture,
            {
                "not_planned": "Não planejada",
                "awaiting_baseline": "Aguardando baseline",
                "awaiting_measurement": "Aguardando medição",
                "on_time": "Em dia",
                "overdue": "Atrasada",
            },
            "cases",
        ),
        by_target_posture=_labeled(
            t_posture,
            {
                "unknown": "Desconhecida",
                "met": "Atingida",
                "not_met": "Não atingida",
                "mixed": "Mista",
            },
            "cases",
        ),
        by_substantiation=_labeled(
            subst,
            {"none": "Nenhuma", "partial": "Parcial", "verified": "Verificada"},
            "cases",
        ),
        overdue_indicators=overdue_indicators,
    )

    freshness_counter = Counter(i.intelligence_freshness for i in items)
    intel = IntelligenceCoverageOut(
        current=freshness_counter.get("current", 0),
        stale=freshness_counter.get("stale", 0),
        never_analyzed=freshness_counter.get("never_analyzed", 0),
    )

    posture_current: Counter[str] = Counter()
    posture_stale: Counter[str] = Counter()
    signals_current: Counter[tuple[str | None, str | None]] = Counter()
    signals_stale: Counter[tuple[str | None, str | None]] = Counter()
    for item in items:
        meta = extras.get(item.case_id) or {}
        posture = item.execution_posture
        if posture and item.intelligence_freshness == "current":
            posture_current[posture] += 1
        elif posture and item.intelligence_freshness == "stale":
            posture_stale[posture] += 1
        for signal in meta.get("signals") or []:
            if isinstance(signal, dict):
                cat, level = signal.get("category"), signal.get("level")
            else:
                cat, level = getattr(signal, "category", None), getattr(
                    signal, "level", None
                )
            key = (cat, level)
            if item.intelligence_freshness == "current":
                signals_current[key] += 1
            elif item.intelligence_freshness == "stale":
                signals_stale[key] += 1

    activity = list_activity(
        ctx, activity_window_days=activity_window_days, limit=10, as_of=when
    )

    return CockpitSummaryOut(
        as_of=when,
        scope=CockpitScopeOut(
            organization_id=ctx.organization_id,
            case_status_filter=None,
            activity_window_days=activity_window_days,
        ),
        case_totals=CaseTotalsOut(
            total=total,
            active=total - closed,
            reviewing=reviewing,
            closed=closed,
            ready_for_review=ready,
        ),
        priority_distribution=_labeled(priority_counter, PRIORITY_BAND_LABELS, "cases"),
        execution=exec_totals,
        evidence=evidence,
        measurement=measurement,
        intelligence_coverage=intel,
        execution_posture_distribution_current=[
            LabeledCount(code=k, label=k, count=v, unit="cases")
            for k, v in sorted(posture_current.items())
        ],
        execution_posture_distribution_stale=[
            LabeledCount(code=k, label=k, count=v, unit="cases")
            for k, v in sorted(posture_stale.items())
        ],
        signals_current=[
            SignalCountOut(category=cat, level=level, count=n)  # type: ignore[arg-type]
            for (cat, level), n in sorted(signals_current.items())
        ],
        signals_stale=[
            SignalCountOut(category=cat, level=level, count=n)  # type: ignore[arg-type]
            for (cat, level), n in sorted(signals_stale.items())
        ],
        recent_activity=activity.items,
        coverage=coverage,
    )
