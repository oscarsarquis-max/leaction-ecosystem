"""Bridge: handlers oficiais leem deps via latest_phase_artifact.

Em modo shadow, redireciona a leitura para crystal_shadow_phases sem alterar
o código dos handlers — só durante o contexto de recálculo.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy.orm import Session

import services.phase_artifacts as phase_artifacts
from services.crystal_ball.models import CrystalShadowPhase, CrystalShadowRun


def _as_uuid(run_id: str | UUID) -> UUID:
    return run_id if isinstance(run_id, UUID) else UUID(str(run_id))


def _shadow_latest(
    db_session: Session,
    run_id: str | UUID,
    phase_id: str,
) -> Any:
    run_uuid = _as_uuid(run_id)
    shadow = db_session.get(CrystalShadowRun, run_uuid)
    if shadow is None:
        return phase_artifacts.latest_phase_artifact(db_session, run_id, phase_id)

    row = (
        db_session.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == run_uuid,
            CrystalShadowPhase.phase_id == phase_id,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    if row is None or row.artifact_data is None:
        return None
    return phase_artifacts.unwrap_artifact(row.artifact_data)


@contextmanager
def shadow_artifact_bridge() -> Iterator[None]:
    """Monkeypatch temporário — falha isolada: restaura sempre no finally."""
    original = phase_artifacts.latest_phase_artifact
    phase_artifacts.latest_phase_artifact = _shadow_latest  # type: ignore[assignment]
    try:
        yield
    finally:
        phase_artifacts.latest_phase_artifact = original
