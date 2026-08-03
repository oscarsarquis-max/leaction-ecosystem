from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.maturity import service
from app.modules.maturity.schemas import (
    DiscardIn,
    MaturityPackageCreate,
    MaturityPackageOut,
    MaturityTransitionResult,
    ReasonIn,
    ScoresUpsertIn,
)

router = APIRouter(prefix="/maturity-assessments", tags=["maturity"])


@router.post("", response_model=MaturityPackageOut, status_code=201)
def create_or_get_draft(payload: MaturityPackageCreate, ctx: OrgContextDep) -> MaturityPackageOut:
    return service.create_or_get_draft(ctx, payload)


@router.get("", response_model=list[MaturityPackageOut])
def list_packages(ctx: OrgContextDep, assessment_id: UUID = Query(...)) -> list[MaturityPackageOut]:
    return service.list_packages(ctx, assessment_id)


@router.get("/{package_id}", response_model=MaturityPackageOut)
def get_package(package_id: UUID, ctx: OrgContextDep) -> MaturityPackageOut:
    return service.get_package(ctx, package_id)


@router.put("/{package_id}/scores", response_model=MaturityPackageOut)
def upsert_scores(
    package_id: UUID, payload: ScoresUpsertIn, ctx: OrgContextDep
) -> MaturityPackageOut:
    return service.upsert_scores(ctx, package_id, payload)


@router.post("/{package_id}/transitions/submit", response_model=MaturityTransitionResult)
def submit(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.submit(ctx, package_id)


@router.post("/{package_id}/transitions/approve", response_model=MaturityTransitionResult)
def approve(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.approve(ctx, package_id)


@router.post("/{package_id}/transitions/reject", response_model=MaturityTransitionResult)
def reject(package_id: UUID, payload: ReasonIn, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.reject(ctx, package_id, payload)


@router.post("/{package_id}/transitions/rework", response_model=MaturityTransitionResult)
def rework(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.rework(ctx, package_id)


@router.post("/{package_id}/transitions/discard", response_model=MaturityTransitionResult)
def discard(
    package_id: UUID,
    ctx: OrgContextDep,
    payload: DiscardIn | None = None,
) -> MaturityTransitionResult:
    return service.discard(ctx, package_id, payload)


@router.post("/{package_id}/transitions/supersede", response_model=MaturityTransitionResult)
def supersede(package_id: UUID, payload: ReasonIn, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.supersede(ctx, package_id, payload)
