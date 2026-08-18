"""Rotas Crystal Ball — prefixo /api/crystal-ball (aditivo)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.crystal_ball import service as cb
from services.crystal_ball.experimental_run import (
    ExperimentalRunError,
    build_shadow_lineage,
    experimental_edit_and_recalculate,
    run_mativas_experimental,
)
from services.crystal_ball.service import CrystalBallError

router = APIRouter(prefix="/api/crystal-ball", tags=["crystal-ball"])


class ForkRequest(BaseModel):
    fork_phase_id: str = Field(..., min_length=1)


class EditShadowRequest(BaseModel):
    phase_id: str = Field(..., min_length=1)
    artifact_data: dict[str, Any]


class QuickPreviewRequest(BaseModel):
    text: Optional[str] = None
    structured_requirements: Optional[dict[str, Any]] = None
    link_source_run_id: Optional[UUID] = None


class ExperimentalRunRequest(BaseModel):
    user_prompt: str = Field(..., min_length=8)
    metodologia: str = Field(..., min_length=2)


class ExperimentalRecalculateRequest(BaseModel):
    from_phase_id: str = Field(..., min_length=1)
    artifact_data: Optional[dict[str, Any]] = None


class RecalculateRequest(BaseModel):
    shadow_run_id: UUID


# Rotas estáticas ANTES de /{run_id}/… para não capturar "experimental-run" como UUID.


@router.post("/experimental-run")
async def crystal_experimental_run(
    payload: ExperimentalRunRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Shadow-only: context7(Mativas) → methodology → synthesize → entrega_final."""
    try:
        return await run_mativas_experimental(
            db,
            user_prompt=payload.user_prompt,
            metodologia=payload.metodologia,
        )
    except ExperimentalRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball experimental-run: {exc}"
        ) from exc


@router.post("/experimental-run/{shadow_run_id}/recalculate")
async def crystal_experimental_recalculate(
    shadow_run_id: UUID,
    payload: ExperimentalRecalculateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Edita (opcional) uma fase da Simulação e recalcula só o downstream."""
    try:
        return await experimental_edit_and_recalculate(
            db,
            shadow_run_id,
            from_phase_id=payload.from_phase_id,
            artifact_data=payload.artifact_data,
        )
    except ExperimentalRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Crystal Ball experimental recalculate: {exc}",
        ) from exc


@router.get("/shadow/{shadow_run_id}/lineage")
def crystal_shadow_lineage(
    shadow_run_id: UUID, db: Session = Depends(get_db)
) -> dict[str, Any]:
    try:
        return build_shadow_lineage(db, shadow_run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball shadow lineage: {exc}"
        ) from exc


@router.get("/{run_id}/lineage")
def crystal_lineage(run_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return cb.get_lineage(db, run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crystal Ball lineage: {exc}") from exc


@router.post("/{run_id}/fork")
def crystal_fork(
    run_id: UUID,
    payload: ForkRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return cb.create_fork(db, run_id, payload.fork_phase_id)
    except CrystalBallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crystal Ball fork: {exc}") from exc


@router.post("/shadow/{shadow_run_id}/edit")
def crystal_edit_shadow(
    shadow_run_id: UUID,
    payload: EditShadowRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return cb.edit_shadow_phase(
            db, shadow_run_id, payload.phase_id, payload.artifact_data
        )
    except CrystalBallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/recalculate")
async def crystal_recalculate(
    run_id: UUID,
    payload: RecalculateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Recalcula downstream do shadow ligado ao run oficial."""
    try:
        shadow = cb.get_shadow(db, payload.shadow_run_id)
        if shadow.get("source_run_id") != str(run_id):
            raise CrystalBallError(
                "shadow_run_id não pertence ao run_id informado"
            )
        return await cb.recalculate(db, payload.shadow_run_id)
    except CrystalBallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball recalculate: {exc}"
        ) from exc


@router.post("/shadow/{shadow_run_id}/recalculate")
async def crystal_recalculate_shadow(
    shadow_run_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await cb.recalculate(db, shadow_run_id)
    except CrystalBallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball recalculate: {exc}"
        ) from exc


@router.get("/shadow/{shadow_run_id}")
def crystal_get_shadow(
    shadow_run_id: UUID, db: Session = Depends(get_db)
) -> dict[str, Any]:
    try:
        return cb.get_shadow(db, shadow_run_id)
    except CrystalBallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quick-preview")
async def crystal_quick_preview(
    payload: QuickPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await cb.run_quick_preview(
            db,
            text=payload.text,
            structured_requirements=payload.structured_requirements,
            link_source_run_id=(
                str(payload.link_source_run_id) if payload.link_source_run_id else None
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball preview: {exc}"
        ) from exc


@router.post("/{run_id}/calibrate")
def crystal_calibrate(run_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return cb.calibrate_against_run(db, run_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Crystal Ball calibrate: {exc}"
        ) from exc
