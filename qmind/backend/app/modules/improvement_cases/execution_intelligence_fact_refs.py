"""Canonical Execution Intelligence fact_ref registry (ISOI-009 R1).

Both Core and OI must publish/cite the same field-level refs. Opaque entity
refs (action:1, indicator:1) are only prefixes — signals always cite fields.
"""

from __future__ import annotations

from collections.abc import Iterable

ACTION_FIELD_REFS = (
    "status",
    "owner_assigned",
    "due_at",
    "is_overdue",
    "last_check_in_at",
    "active_impediment_count",
    "open_dependency_count",
    "overdue_dependency_count",
    "approved_evidence_count",
    "is_terminal",
    "claims_execution",
)

INDICATOR_FIELD_REFS = (
    "baseline_value",
    "latest_value",
    "measurement_posture",
    "is_measurement_overdue",
    "substantiation",
    "target_posture",
    "baseline_status",
)


def case_status_ref() -> str:
    return "case.status"


def plan_status_ref() -> str:
    return "execution.plan.status"


def outcome_direction_ref() -> str:
    return "outcome.latest.result_direction"


def action_field_ref(action_ref: str, field: str) -> str:
    return f"execution.action:{action_ref}:{field}"


def indicator_field_ref(indicator_ref: str, field: str) -> str:
    return f"measurement.indicator:{indicator_ref}:{field}"


def action_fact_refs(action_ref: str, fields: Iterable[str] = ACTION_FIELD_REFS) -> list[str]:
    return [action_field_ref(action_ref, field) for field in fields]


def indicator_fact_refs(
    indicator_ref: str, fields: Iterable[str] = INDICATOR_FIELD_REFS
) -> list[str]:
    return [indicator_field_ref(indicator_ref, field) for field in fields]


# Core lifecycle: only these close the work item as terminal for EI.
CORE_TERMINAL_ACTION_STATUSES = frozenset({"done", "cancelled", "ineffective_closed"})

# Cancelled is terminal but does not claim the work was executed.
CORE_EXECUTED_TERMINAL_STATUSES = frozenset({"done", "ineffective_closed"})
