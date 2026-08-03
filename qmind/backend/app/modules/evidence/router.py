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

router = APIRouter(prefix="/evidences", tags=["evidences"])


@router.post("/authorize", response_model=AuthorizeUploadOut, status_code=201)
def authorize_upload(payload: AuthorizeUploadIn, ctx: OrgContextDep) -> AuthorizeUploadOut:
    return service.authorize_upload(ctx, payload)


@router.post("/cleanup-expired", response_model=CleanupResult)
def cleanup_expired(_ctx: OrgContextDep) -> CleanupResult:
    """Dispose abandoned/expired upload_pending rows (system-style; org admin/operators)."""
    from app.modules.orgs.service import require_role

    require_role(_ctx, "org_admin", "consultant_auditor", "quality_manager")
    return service.cleanup_expired_uploads()


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceOut:
    return service.get_evidence(ctx, evidence_id)


@router.get("/{evidence_id}/download-url", response_model=DownloadUrlOut)
def download_url(evidence_id: UUID, ctx: OrgContextDep) -> DownloadUrlOut:
    return service.download_url(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/receive", response_model=EvidenceTransitionResult)
def receive_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.receive_upload(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/security_pass", response_model=EvidenceTransitionResult)
def security_pass(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_pass(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/security_fail", response_model=EvidenceTransitionResult)
def security_fail(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_fail(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/abandon", response_model=EvidenceTransitionResult)
def abandon_upload(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.abandon_upload(ctx, evidence_id)
