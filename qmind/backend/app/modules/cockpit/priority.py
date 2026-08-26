"""Pure priority-band precedence for the ISO Intelligence Cockpit (ISOI-010)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.cockpit.schemas import (
    PRIORITY_BAND_LABELS,
    PRIORITY_REASON_LABELS,
    CockpitPriorityBand,
    PriorityReasonOut,
)

BAND_RANK: dict[CockpitPriorityBand, int] = {
    "immediate_attention": 0,
    "attention": 1,
    "follow_up": 2,
    "on_course": 3,
    "completed_or_observed": 4,
}

_IMMEDIATE = frozenset(
    {
        "ei_current_stalled",
        "overdue_action_with_active_impediment",
        "overdue_dependency_with_overdue_action",
    }
)
_ATTENTION = frozenset(
    {
        "ei_current_attention_required",
        "overdue_action",
        "active_impediment",
        "active_dependency",
        "measurement_overdue",
        "target_not_met",
        "target_mixed",
        "claims_execution_without_approved_evidence",
        "current_oi_attention_signal",
    }
)
_FOLLOW_UP = frozenset(
    {
        "ei_stale",
        "ei_never_analyzed",
        "awaiting_result_evaluation",
        "awaiting_baseline",
        "awaiting_measurement",
        "stale_check_in",
        "pending_human_observation",
    }
)


@dataclass(frozen=True)
class CasePrioritySnapshot:
    """Factual inputs for priority — no database, no opaque score."""

    case_status: str
    intelligence_freshness: str  # current | stale | never_analyzed
    execution_posture: str | None
    has_overdue_action: bool
    has_active_impediment: bool
    has_open_dependency: bool
    has_overdue_dependency: bool
    measurement_posture: str
    target_posture: str
    claims_execution_without_approved_evidence: bool
    has_current_attention_signal: bool
    has_stale_check_in: bool
    awaiting_human_observation: bool
    has_outcome_observation: bool
    has_active_execution: bool = False


def _reason(code: str) -> PriorityReasonOut:
    return PriorityReasonOut(
        code=code,
        label=PRIORITY_REASON_LABELS.get(code, code),
    )


def _dedupe(reasons: list[PriorityReasonOut]) -> list[PriorityReasonOut]:
    seen: set[str] = set()
    out: list[PriorityReasonOut] = []
    for item in reasons:
        if item.code in seen:
            continue
        seen.add(item.code)
        out.append(item)
    return out


def collect_priority_reasons(snap: CasePrioritySnapshot) -> list[PriorityReasonOut]:
    """Return all matching reason codes (deterministic order)."""
    reasons: list[PriorityReasonOut] = []
    freshness = snap.intelligence_freshness
    posture = snap.execution_posture
    current = freshness == "current"

    critical_overdue_impediment = snap.has_overdue_action and snap.has_active_impediment
    critical_overdue_dependency = (
        snap.has_overdue_dependency and snap.has_overdue_action
    )

    # --- immediate_attention ---
    if current and posture == "stalled":
        reasons.append(_reason("ei_current_stalled"))
    if critical_overdue_impediment:
        reasons.append(_reason("overdue_action_with_active_impediment"))
    if critical_overdue_dependency:
        reasons.append(_reason("overdue_dependency_with_overdue_action"))

    # --- attention ---
    if current and posture == "attention_required":
        reasons.append(_reason("ei_current_attention_required"))
    # overdue without a critical combo that already explains it
    if snap.has_overdue_action and not critical_overdue_impediment and not critical_overdue_dependency:
        reasons.append(_reason("overdue_action"))
    if snap.has_active_impediment and not critical_overdue_impediment:
        reasons.append(_reason("active_impediment"))
    if snap.has_open_dependency and not critical_overdue_dependency:
        reasons.append(_reason("active_dependency"))
    if snap.measurement_posture == "overdue":
        reasons.append(_reason("measurement_overdue"))
    if snap.target_posture == "not_met":
        reasons.append(_reason("target_not_met"))
    if snap.target_posture == "mixed":
        reasons.append(_reason("target_mixed"))
    if snap.claims_execution_without_approved_evidence:
        reasons.append(_reason("claims_execution_without_approved_evidence"))
    if snap.has_current_attention_signal:
        reasons.append(_reason("current_oi_attention_signal"))

    # --- follow_up ---
    if freshness == "stale":
        reasons.append(_reason("ei_stale"))
    if freshness == "never_analyzed":
        reasons.append(_reason("ei_never_analyzed"))
    if posture == "awaiting_result_evaluation":
        reasons.append(_reason("awaiting_result_evaluation"))
    if snap.measurement_posture == "awaiting_baseline":
        reasons.append(_reason("awaiting_baseline"))
    if snap.measurement_posture == "awaiting_measurement":
        reasons.append(_reason("awaiting_measurement"))
    if snap.has_stale_check_in and not (current and posture == "stalled"):
        reasons.append(_reason("stale_check_in"))
    if snap.awaiting_human_observation:
        reasons.append(_reason("pending_human_observation"))

    return _dedupe(reasons)


def band_for_reasons(
    reasons: list[PriorityReasonOut],
    snap: CasePrioritySnapshot,
) -> CockpitPriorityBand:
    codes = {r.code for r in reasons}
    if codes & _IMMEDIATE:
        return "immediate_attention"
    if codes & _ATTENTION:
        return "attention"
    if codes & _FOLLOW_UP:
        return "follow_up"
    if snap.case_status == "closed" or (
        snap.has_outcome_observation and snap.case_status == "reviewing"
    ):
        return "completed_or_observed"
    if snap.has_outcome_observation and not snap.has_active_execution:
        return "completed_or_observed"
    return "on_course"


def compute_priority(
    snap: CasePrioritySnapshot,
) -> tuple[CockpitPriorityBand, list[PriorityReasonOut]]:
    reasons = collect_priority_reasons(snap)
    band = band_for_reasons(reasons, snap)
    if band == "on_course":
        extra: list[PriorityReasonOut] = []
        if (
            snap.intelligence_freshness == "current"
            and snap.execution_posture == "progressing"
        ):
            extra.append(_reason("ei_current_progressing"))
        elif not reasons:
            extra.append(_reason("active_without_alerts"))
        reasons = _dedupe([*reasons, *extra]) or [_reason("active_without_alerts")]
    elif band == "completed_or_observed":
        if not ({r.code for r in reasons} & (_IMMEDIATE | _ATTENTION | _FOLLOW_UP)):
            completed: list[PriorityReasonOut] = []
            if snap.has_outcome_observation:
                completed.append(_reason("outcome_observed"))
            if snap.case_status == "closed":
                completed.append(_reason("case_closed"))
            reasons = completed or [_reason("outcome_observed")]
    return band, reasons


def priority_band_label(band: CockpitPriorityBand) -> str:
    return PRIORITY_BAND_LABELS[band]


def sort_key_for_case(
    *,
    band: CockpitPriorityBand,
    oldest_due_at: datetime | None,
    last_activity_at: datetime | None,
    case_id: str,
) -> tuple:
    """Worse band first; within band oldest due, then oldest activity, then id."""
    due_key = (
        oldest_due_at.astimezone(UTC)
        if oldest_due_at
        else datetime.max.replace(tzinfo=UTC)
    )
    act_key = (
        last_activity_at.astimezone(UTC)
        if last_activity_at
        else datetime.max.replace(tzinfo=UTC)
    )
    return (BAND_RANK[band], due_key, act_key, case_id)
