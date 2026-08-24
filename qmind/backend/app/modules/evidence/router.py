from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.auth.deps import OrgContextDep
from app.modules.evidence import service
from app.modules.evidence.schemas import (
    AuthorizeUploadIn,
    AuthorizeUploadOut,
    CleanupResult,
    ContextualAuthorizeUploadIn,
    DownloadUrlOut,
    EvidenceAttachmentOut,
    EvidenceLinkCreate,
    EvidenceLinkOut,
    EvidenceLinkRemoveIn,
    EvidenceOut,
    EvidenceTransitionResult,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader
from app.schemas.enums import EvidenceLinkTargetType

router = APIRouter(tags=["evidences"])


@router.post(
    "/organizations/current/actions/{action_item_id}/evidences/authorize",
    response_model=AuthorizeUploadOut,
    status_code=201,
    operation_id="authorizeActionItemEvidenceUpload",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
    summary="Authorize an evidence for one action and link it in the same step",
)
def authorize_action_item_evidence(
    action_item_id: UUID,
    payload: ContextualAuthorizeUploadIn,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AuthorizeUploadOut:
    if _idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": _idempotency_key})
    return service.authorize_action_item_upload(ctx, action_item_id, payload)


@router.post(
    "/organizations/current/improvement-cases/{case_id}/evidences/authorize",
    response_model=AuthorizeUploadOut,
    status_code=201,
    operation_id="authorizeImprovementCaseEvidenceUpload",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
    summary="Authorize an evidence that belongs to an improvement case",
)
def authorize_improvement_case_evidence(
    case_id: UUID,
    payload: ContextualAuthorizeUploadIn,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AuthorizeUploadOut:
    if _idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": _idempotency_key})
    return service.authorize_improvement_case_upload(ctx, case_id, payload)


@router.get(
    "/organizations/current/evidence-links",
    response_model=list[EvidenceAttachmentOut],
    operation_id="listEvidenceLinksForTarget",
    summary="Evidences attached to one domain object, with the document summary",
)
def list_evidence_links_for_target(
    ctx: OrgContextDep,
    target_type: EvidenceLinkTargetType = Query(...),
    target_id: UUID = Query(...),
    include_removed: bool = Query(
        default=False,
        description="Include soft-removed links (history); operators only",
    ),
) -> list[EvidenceAttachmentOut]:
    return service.list_links_for_target(
        ctx,
        target_type=target_type.value,
        target_id=target_id,
        include_removed=include_removed,
    )


@router.get(
    "/assessments/{assessment_id}/evidences",
    response_model=list[EvidenceOut],
    operation_id="listAssessmentEvidences",
    responses={404: ERROR_RESPONSES[404]},
)
def list_assessment_evidences(
    assessment_id: UUID, ctx: OrgContextDep
) -> list[EvidenceOut]:
    return service.list_assessment_evidences(ctx, assessment_id)


evidences_router = APIRouter(prefix="/evidences", tags=["evidences"])


@evidences_router.post(
    "/authorize",
    response_model=AuthorizeUploadOut,
    status_code=201,
    operation_id="authorizeEvidenceUpload",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
    summary="Authorize evidence upload (Idempotency-Key recommended)",
)
def authorize_upload(
    payload: AuthorizeUploadIn,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AuthorizeUploadOut:
    return service.authorize_upload(ctx, payload)


@evidences_router.post(
    "/cleanup-expired",
    response_model=CleanupResult,
    operation_id="cleanupExpiredEvidences",
    responses={403: ERROR_RESPONSES[403]},
)
def cleanup_expired(_ctx: OrgContextDep) -> CleanupResult:
    """Dispose abandoned/expired upload_pending rows (system-style; org admin/operators)."""
    from app.modules.orgs.service import require_role

    require_role(_ctx, "org_admin", "consultant_auditor", "quality_manager")
    return service.cleanup_expired_uploads()


@evidences_router.put(
    "/{evidence_id}/bytes",
    status_code=204,
    operation_id="putEvidenceBytesLocal",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        410: ERROR_RESPONSES[410],
        422: ERROR_RESPONSES[422],
        503: ERROR_RESPONSES[503],
    },
    summary="Local memory storage PUT (not available in prod/S3)",
)
async def put_evidence_bytes_local(
    evidence_id: UUID,
    request: Request,
    ctx: OrgContextDep,
) -> Response:
    data = await request.body()
    ctype = request.headers.get("content-type", "application/octet-stream")
    service.put_bytes_local(ctx, evidence_id, data, ctype)
    return Response(status_code=204)


@evidences_router.get(
    "/{evidence_id}",
    response_model=EvidenceOut,
    operation_id="getEvidence",
    responses={404: ERROR_RESPONSES[404]},
)
def get_evidence(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceOut:
    return service.get_evidence(ctx, evidence_id)


@evidences_router.get(
    "/{evidence_id}/download-url",
    response_model=DownloadUrlOut,
    operation_id="getEvidenceDownloadUrl",
    responses={404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def download_url(evidence_id: UUID, ctx: OrgContextDep) -> DownloadUrlOut:
    return service.download_url(ctx, evidence_id)


@evidences_router.get(
    "/{evidence_id}/bytes",
    operation_id="getEvidenceBytesLocal",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
        503: ERROR_RESPONSES[503],
    },
    summary="Local memory storage GET (not available in prod/S3)",
)
def get_evidence_bytes_local(evidence_id: UUID, ctx: OrgContextDep) -> Response:
    data, ctype = service.get_bytes_local(ctx, evidence_id)
    return Response(content=data, media_type=ctype)


@evidences_router.post(
    "/{evidence_id}/links",
    response_model=EvidenceLinkOut,
    status_code=201,
    operation_id="createEvidenceLink",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_evidence_link(
    evidence_id: UUID,
    payload: EvidenceLinkCreate,
    ctx: OrgContextDep,
) -> EvidenceLinkOut:
    return service.create_evidence_link(ctx, evidence_id, payload)


@evidences_router.get(
    "/{evidence_id}/links",
    response_model=list[EvidenceLinkOut],
    operation_id="listEvidenceLinks",
    responses={404: ERROR_RESPONSES[404]},
)
def list_evidence_links(
    evidence_id: UUID,
    ctx: OrgContextDep,
    include_removed: bool = Query(
        default=False,
        description="Include soft-removed links (history); operators only",
    ),
) -> list[EvidenceLinkOut]:
    return service.list_evidence_links(
        ctx, evidence_id, include_removed=include_removed
    )


@evidences_router.delete(
    "/{evidence_id}/links/{link_id}",
    status_code=204,
    operation_id="deleteEvidenceLink",
    responses={404: ERROR_RESPONSES[404]},
    summary="Soft-remove an evidence link (history is preserved)",
)
def delete_evidence_link(
    evidence_id: UUID,
    link_id: UUID,
    ctx: OrgContextDep,
    payload: EvidenceLinkRemoveIn | None = None,
) -> None:
    service.delete_evidence_link(
        ctx,
        evidence_id,
        link_id,
        removal_reason=payload.removal_reason if payload else "",
    )


@evidences_router.post(
    "/{evidence_id}/transitions/receive",
    response_model=EvidenceTransitionResult,
    operation_id="receiveEvidenceUpload",
    responses={409: ERROR_RESPONSES[409], 410: ERROR_RESPONSES[410], 422: ERROR_RESPONSES[422]},
)
def receive_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.receive_upload(ctx, evidence_id)


@evidences_router.post(
    "/{evidence_id}/transitions/security_pass",
    response_model=EvidenceTransitionResult,
    operation_id="securityPassEvidence",
    responses={409: ERROR_RESPONSES[409], 503: ERROR_RESPONSES[503]},
)
def security_pass(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_pass(ctx, evidence_id)


@evidences_router.post(
    "/{evidence_id}/transitions/security_fail",
    response_model=EvidenceTransitionResult,
    operation_id="securityFailEvidence",
    responses={409: ERROR_RESPONSES[409]},
)
def security_fail(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_fail(ctx, evidence_id)


@evidences_router.post(
    "/{evidence_id}/transitions/abandon",
    response_model=EvidenceTransitionResult,
    operation_id="abandonEvidenceUpload",
    responses={409: ERROR_RESPONSES[409]},
)
def abandon_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.abandon_upload(ctx, evidence_id)


# Composite router: assessment-scoped list + /evidences/*
router.include_router(evidences_router)
