from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.evidence import service
from app.modules.evidence.schemas import (
    AuthorizeUploadIn,
    EvidenceOut,
    EvidenceTransitionResult,
    ReceiveUploadIn,
)

router = APIRouter(prefix="/evidences", tags=["evidences"])


@router.post("/authorize", response_model=EvidenceOut, status_code=201)
def authorize_upload(payload: AuthorizeUploadIn, ctx: OrgContextDep) -> EvidenceOut:
    return service.authorize_upload(ctx, payload)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceOut:
    return service.get_evidence(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/receive", response_model=EvidenceTransitionResult)
def receive_upload(
    evidence_id: UUID, payload: ReceiveUploadIn, ctx: OrgContextDep
) -> EvidenceTransitionResult:
    return service.receive_upload(ctx, evidence_id, payload)


@router.post("/{evidence_id}/transitions/security_pass", response_model=EvidenceTransitionResult)
def security_pass(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_pass(ctx, evidence_id)


@router.post("/{evidence_id}/transitions/security_fail", response_model=EvidenceTransitionResult)
def security_fail(evidence_id: UUID, ctx: OrgContextDep) -> EvidenceTransitionResult:
    return service.security_fail(ctx, evidence_id)
