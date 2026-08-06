"""Public (PT-BR) evidence situation labels for the Guided Wizard.

Internal EvidenceStatus values must never be shown raw in the UI.
"""

from __future__ import annotations

from app.modules.evidence.collection import public_collection_origin

# Technical → public vocabulary.
_PUBLIC_SITUATION: dict[str, str] = {
    "upload_pending": "Aguardando envio",
    "quarantined": "Em verificação",
    "rejected": "Rejeitada",
    "approved": "Aprovada",
    "superseded": "Substituída",
    "pending_disposal": "Aguardando revisão",
    "disposed": "Substituída",
}


def public_situation(status: str | None) -> str:
    if not status:
        return "Aguardando revisão"
    return _PUBLIC_SITUATION.get(status, "Aguardando revisão")


def situation_bucket(status: str | None) -> str:
    """Coarse bucket for narrative / summary counts (not a conformity judgment)."""
    if status == "upload_pending":
        return "awaiting_upload"
    if status in ("quarantined", "pending_disposal"):
        return "processing"
    if status == "approved":
        return "approved"
    if status == "rejected":
        return "rejected"
    if status in ("superseded", "disposed"):
        return "replaced"
    return "processing"


def public_origin_label(collected_phase: str | None) -> str | None:
    return public_collection_origin(collected_phase)
