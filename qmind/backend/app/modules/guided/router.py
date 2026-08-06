from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep, PrincipalDep
from app.modules.guided import service
from app.modules.guided.schemas import (
    GuidedAnswerUpsert,
    GuidedContextPatch,
    GuidedPositionPatch,
    GuidedSessionOut,
)
from app.schemas.common import ERROR_RESPONSES

router = APIRouter(tags=["guided"])


@router.get(
    "/guided/catalog",
    operation_id="getGuidedCatalog",
    summary="Catálogo versionado do roteiro guiado (cláusulas 4–10)",
    responses={404: ERROR_RESPONSES[404]},
)
def get_catalog(
    _principal: PrincipalDep,
    version: str | None = None,
) -> dict[str, Any]:
    """Sem `version`, devolve o catálogo padrão (mais recente)."""
    return service.get_catalog(version)


@router.get(
    "/assessments/{assessment_id}/guided",
    response_model=GuidedSessionOut,
    operation_id="getOrCreateGuidedSession",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def get_or_create_guided_session(
    assessment_id: UUID, ctx: OrgContextDep
) -> GuidedSessionOut:
    return service.get_or_create_session(ctx, assessment_id)


@router.patch(
    "/assessments/{assessment_id}/guided",
    response_model=GuidedSessionOut,
    operation_id="patchGuidedSession",
    responses={404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def patch_guided_session(
    assessment_id: UUID, payload: GuidedContextPatch, ctx: OrgContextDep
) -> GuidedSessionOut:
    return service.patch_context(ctx, assessment_id, payload)


@router.patch(
    "/assessments/{assessment_id}/guided/position",
    response_model=GuidedSessionOut,
    operation_id="patchGuidedPosition",
)
def patch_guided_position(
    assessment_id: UUID, payload: GuidedPositionPatch, ctx: OrgContextDep
) -> GuidedSessionOut:
    return service.patch_position(ctx, assessment_id, payload)


@router.put(
    "/assessments/{assessment_id}/guided/answers/{question_id}",
    response_model=GuidedSessionOut,
    operation_id="upsertGuidedAnswer",
    responses={404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def upsert_guided_answer(
    assessment_id: UUID,
    question_id: str,
    payload: GuidedAnswerUpsert,
    ctx: OrgContextDep,
) -> GuidedSessionOut:
    return service.upsert_answer(ctx, assessment_id, question_id, payload)
