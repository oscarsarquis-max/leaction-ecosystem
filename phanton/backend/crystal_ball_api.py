"""Rotas Crystal Ball — prefixo /api/crystal-ball (aditivo)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import AuthUser, assert_shadow_owner, get_current_user
from database import get_db
from services.crystal_ball import service as cb
from services.crystal_ball.experimental_run import (
    ExperimentalRunError,
    build_shadow_lineage,
    experimental_edit_and_recalculate,
    run_mativas_experimental,
)
from services.crystal_ball import corpora as corpora_svc
from services.crystal_ball.resultado_real import (
    ResultadoRealError,
    registrar_resultado_real,
)
from services.crystal_ball.sugestao_prompt import (
    SugestaoPromptError,
    gerar_sugestao_prompt_geral,
    list_ciclos,
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


class RegisterCorpusRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=80)
    nome: str = Field(..., min_length=2, max_length=200)
    tipo_fonte: str = Field(default="upload_json")
    schema_config: dict[str, Any]


class SugestaoPromptRequest(BaseModel):
    shadow_run_ids: list[UUID] = Field(..., min_length=2)
    prompt_mestre: Optional[str] = None


class ResultadoRealRequest(BaseModel):
    chave_valor: str = Field(..., min_length=1)
    payload: Any
    desafio_texto: Optional[str] = None
    numero_ciclo: Optional[int] = None


# Rotas estáticas ANTES de /{run_id}/… para não capturar "experimental-run" como UUID.


@router.post("/experimental-run")
async def crystal_experimental_run(
    payload: ExperimentalRunRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Shadow-only: context7(Mativas) → methodology → synthesize → entrega_final."""
    try:
        return await run_mativas_experimental(
            db,
            user_prompt=payload.user_prompt,
            metodologia=payload.metodologia,
            owned_by_user_id=user.id,
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
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Edita (opcional) uma fase da Simulação e recalcula só o downstream."""
    assert_shadow_owner(db, shadow_run_id, user)
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


@router.get("/corpora")
def crystal_list_corpora(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return {"items": corpora_svc.list_corpora(db)}


@router.post("/corpora")
def crystal_register_corpus(
    payload: RegisterCorpusRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    try:
        row = corpora_svc.register_corpus(
            db,
            slug=payload.slug,
            nome=payload.nome,
            tipo_fonte=payload.tipo_fonte,
            schema_config=payload.schema_config,
        )
        return {
            "id": str(row.id),
            "slug": row.slug,
            "nome": row.nome,
            "tipo_fonte": row.tipo_fonte,
            "schema_config": row.schema_config,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corpus/{corpus_id}/sugestao-prompt")
def crystal_sugestao_prompt(
    corpus_id: str,
    payload: SugestaoPromptRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Fase sugestao_prompt_geral — texto copiável; nunca aplica em sistema externo."""
    _ = user
    try:
        return gerar_sugestao_prompt_geral(
            db,
            corpus_id=corpus_id,
            shadow_run_ids=list(payload.shadow_run_ids),
            prompt_mestre=payload.prompt_mestre,
        )
    except SugestaoPromptError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"sugestao-prompt: {exc}"
        ) from exc


@router.get("/corpus/{corpus_id}/ciclos")
def crystal_list_ciclos(
    corpus_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    try:
        return {"items": list_ciclos(db, corpus_id)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/corpus/{corpus_id}/resultado-real")
def crystal_resultado_real(
    corpus_id: str,
    payload: ResultadoRealRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Cola resultado real (manual) e compara campo-a-campo — sem automação externa."""
    _ = user
    try:
        return registrar_resultado_real(
            db,
            corpus_id=corpus_id,
            chave_valor=payload.chave_valor,
            payload=payload.payload,
            desafio_texto=payload.desafio_texto,
            numero_ciclo=payload.numero_ciclo,
        )
    except ResultadoRealError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"resultado-real: {exc}"
        ) from exc


@router.get("/shadow/{shadow_run_id}/lineage")
def crystal_shadow_lineage(
    shadow_run_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    assert_shadow_owner(db, shadow_run_id, user)
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
    shadow_run_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    assert_shadow_owner(db, shadow_run_id, user)
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
