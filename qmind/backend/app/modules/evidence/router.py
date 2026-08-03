from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.evidence import service
from app.modules.evidence.schemas import (
    AuthorizeUploadIn,
    AuthorizeUploadOut,
    CleanupResult,
    DownloadUrlOut,
    EvidenceOut,
    EvidenceTransitionResult,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(prefix="/evidences", tags=["evidences"])


@router.post(
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


@router.post(
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


@router.get(
    "/{evidence_id}",
    response_model=EvidenceOut,
    operation_id="getEvidence",
    responses={404: ERROR_RESPONSES[404]},
)
def get_evidence(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceOut:
    return service.get_evidence(ctx, evidence_id)


@router.get(
    "/{evidence_id}/download-url",
    response_model=DownloadUrlOut,
    operation_id="getEvidenceDownloadUrl",
    responses={404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def download_url(evidence_id: UUID, ctx: OrgContextDep) -> DownloadUrlOut:
    return service.download_url(ctx, evidence_id)


@router.post(
    "/{evidence_id}/transitions/receive",
    response_model=EvidenceTransitionResult,
    operation_id="receiveEvidenceUpload",
    responses={409: ERROR_RESPONSES[409], 410: ERROR_RESPONSES[410], 422: ERROR_RESPONSES[422]},
)
def receive_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.receive_upload(ctx, evidence_id)


@router.post(
    "/{evidence_id}/transitions/security_pass",
    response_model=EvidenceTransitionResult,
    operation_id="securityPassEvidence",
    responses={409: ERROR_RESPONSES[409], 503: ERROR_RESPONSES[503]},
)
def security_pass(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_pass(ctx, evidence_id)


@router.post(
    "/{evidence_id}/transitions/security_fail",
    response_model=EvidenceTransitionResult,
    operation_id="securityFailEvidence",
    responses={409: ERROR_RESPONSES[409]},
)
def security_fail(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_fail(ctx, evidence_id)


@router.post(
    "/{evidence_id}/transitions/abandon",
    response_model=EvidenceTransitionResult,
    operation_id="abandonEvidenceUpload",
    responses={409: ERROR_RESPONSES[409]},
)
def abandon_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.abandon_upload(ctx, evidence_id)
