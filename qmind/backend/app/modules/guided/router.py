from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep, PrincipalDep
from app.modules.evidence.schemas import AuthorizeUploadIn, AuthorizeUploadOut
from app.modules.guided import evidence_links
from app.modules.guided import service
from app.modules.guided.schemas import (
    GuidedAnswerUpsert,
    GuidedContextPatch,
    GuidedEvidenceLinkCreate,
    GuidedEvidenceLinkOut,
    GuidedEvidenceStatusOut,
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


@router.get(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences",
    response_model=list[GuidedEvidenceLinkOut],
    operation_id="listGuidedAnswerEvidences",
    responses={404: ERROR_RESPONSES[404]},
    summary="Listar evidências vinculadas à resposta guiada",
)
def list_guided_answer_evidences(
    assessment_id: UUID, question_id: str, ctx: OrgContextDep
) -> list[GuidedEvidenceLinkOut]:
    return evidence_links.list_answer_evidences(ctx, assessment_id, question_id)


@router.get(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences/status",
    response_model=GuidedEvidenceStatusOut,
    operation_id="getGuidedAnswerEvidenceStatus",
    responses={404: ERROR_RESPONSES[404]},
    summary="Situação atual das evidências da resposta (vocabulário público)",
)
def get_guided_answer_evidence_status(
    assessment_id: UUID, question_id: str, ctx: OrgContextDep
) -> GuidedEvidenceStatusOut:
    return evidence_links.answer_evidence_status(ctx, assessment_id, question_id)


@router.post(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences/link",
    response_model=GuidedSessionOut,
    operation_id="linkGuidedAnswerEvidence",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Vincular evidência existente à resposta",
)
def link_guided_answer_evidence(
    assessment_id: UUID,
    question_id: str,
    payload: GuidedEvidenceLinkCreate,
    ctx: OrgContextDep,
) -> GuidedSessionOut:
    return evidence_links.link_existing(ctx, assessment_id, question_id, payload)


@router.delete(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences/{evidence_id}",
    response_model=GuidedSessionOut,
    operation_id="unlinkGuidedAnswerEvidence",
    responses={404: ERROR_RESPONSES[404]},
    summary="Remover vínculo resposta ↔ evidência",
)
def unlink_guided_answer_evidence(
    assessment_id: UUID,
    question_id: str,
    evidence_id: UUID,
    ctx: OrgContextDep,
) -> GuidedSessionOut:
    return evidence_links.unlink(ctx, assessment_id, question_id, evidence_id)


@router.post(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences/authorize",
    response_model=AuthorizeUploadOut,
    status_code=201,
    operation_id="authorizeGuidedAnswerEvidenceUpload",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Autorizar upload no contexto da pergunta (reutiliza fluxo S3)",
)
def authorize_guided_answer_evidence_upload(
    assessment_id: UUID,
    question_id: str,
    payload: AuthorizeUploadIn,
    ctx: OrgContextDep,
) -> AuthorizeUploadOut:
    return evidence_links.authorize_for_question(
        ctx, assessment_id, question_id, payload
    )


@router.post(
    "/assessments/{assessment_id}/guided/answers/{question_id}/evidences/{evidence_id}/complete",
    response_model=GuidedSessionOut,
    operation_id="completeGuidedAnswerEvidenceLink",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
    },
    summary="Concluir vínculo tipado após receive",
)
def complete_guided_answer_evidence_link(
    assessment_id: UUID,
    question_id: str,
    evidence_id: UUID,
    ctx: OrgContextDep,
) -> GuidedSessionOut:
    return evidence_links.complete_after_receive(
        ctx, assessment_id, question_id, evidence_id
    )
