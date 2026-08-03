from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.findings import service
from app.modules.findings.schemas import (
    FindingCreate,
    FindingOut,
    FindingTransitionResult,
    RejectIn,
)

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post("", response_model=FindingOut, status_code=201)
def create_finding(payload: FindingCreate, ctx: OrgContextDep) -> FindingOut:
    return service.create_draft(ctx, payload)


@router.get("", response_model=list[FindingOut])
def list_findings(
    ctx: OrgContextDep,
    assessment_id: UUID | None = Query(default=None),
) -> list[FindingOut]:
    return service.list_findings(ctx, assessment_id)


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingOut:
    return service.get_finding(ctx, finding_id)


@router.post("/{finding_id}/transitions/submit", response_model=FindingTransitionResult)
def submit_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.submit(ctx, finding_id)


@router.post("/{finding_id}/transitions/approve", response_model=FindingTransitionResult)
def approve_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.approve(ctx, finding_id)


@router.post("/{finding_id}/transitions/reject", response_model=FindingTransitionResult)
def reject_finding(
    finding_id: UUID, payload: RejectIn, ctx: OrgContextDep
) -> FindingTransitionResult:
    return service.reject(ctx, finding_id, payload)


@router.post("/{finding_id}/transitions/rework", response_model=FindingTransitionResult)
def rework_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.rework(ctx, finding_id)
