"""Helpers para recuperar artifact_data de fases anteriores (IDs dinâmicos)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models import PhaseExecution


def as_uuid(run_id: str | UUID) -> UUID:
    return run_id if isinstance(run_id, UUID) else UUID(str(run_id))


def unwrap_artifact(raw: Any) -> Any:
    if isinstance(raw, dict) and "artifact_data" in raw:
        return raw.get("artifact_data")
    return raw


def latest_phase_artifact(
    db_session: Session,
    run_id: str | UUID,
    phase_id: str,
) -> Any:
    run_uuid = as_uuid(run_id)
    row = (
        db_session.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_uuid,
            PhaseExecution.phase_id == phase_id,
        )
        .order_by(PhaseExecution.id.desc())
        .first()
    )
    if row is None:
        return None
    return unwrap_artifact(row.artifact_data)


def latest_artifact_by_level(
    db_session: Session,
    run_id: str | UUID,
    level: str,
) -> Any:
    """Busca artefato por ID exato (L3) ou prefixo dinâmico (L3_sintese, L3_html...)."""
    exact = latest_phase_artifact(db_session, run_id, level)
    if exact is not None:
        return exact

    run_uuid = as_uuid(run_id)
    prefix = f"{level}_"
    rows = (
        db_session.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_uuid,
            PhaseExecution.phase_id.like(f"{prefix}%"),
        )
        .order_by(PhaseExecution.id.desc())
        .all()
    )
    for row in rows:
        if row.artifact_data is not None:
            return unwrap_artifact(row.artifact_data)
    return None
