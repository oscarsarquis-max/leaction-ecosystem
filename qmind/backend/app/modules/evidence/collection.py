"""Evidence collection windows by assessment phase (server-derived)."""

from __future__ import annotations

from app.errors import AppError

# Assessment statuses that accept new uploads / evidence mutations.
COLLECTING_STATUSES = frozenset({"draft", "planned", "in_progress", "analysis"})

# Explicit block list (includes closed/cancelled).
BLOCKED_UPLOAD_STATUSES = frozenset({"actions", "report", "closed", "cancelled"})

_PHASE_BY_STATUS = {
    "draft": "preparation",
    "planned": "planning",
    "in_progress": "field",
    "analysis": "analysis",
}

COLLECTED_PHASES = frozenset(
    {"preparation", "planning", "field", "analysis", "unknown_legacy"}
)

_ORIGIN_LABEL = {
    "preparation": "Disponível antecipadamente",
    "planning": "Disponível antecipadamente",
    "field": "Coletada em campo",
    "analysis": "Complementação da análise",
}


def collected_phase_for_status(assessment_status: str) -> str:
    """Derive collection phase from current assessment status (never trust client)."""
    return _PHASE_BY_STATUS.get(assessment_status, "unknown_legacy")


def public_collection_origin(collected_phase: str | None) -> str | None:
    if not collected_phase or collected_phase == "unknown_legacy":
        return None
    return _ORIGIN_LABEL.get(collected_phase)


def assert_assessment_allows_collection(assessment_status: str) -> None:
    if assessment_status in ("closed", "cancelled"):
        raise AppError(
            "assessment_closed",
            "Assessment closed/cancelled",
            status_code=409,
        )
    if assessment_status not in COLLECTING_STATUSES:
        raise AppError(
            "assessment_not_collecting",
            f"Upload not allowed in assessment status {assessment_status}",
            status_code=409,
        )
