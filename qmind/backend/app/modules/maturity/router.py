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
from app.schemas.common import (
    ERROR_RESPONSES,
    CursorQuery,
    IdempotencyKeyHeader,
    LimitQuery,
)

router = APIRouter(prefix="/maturity-assessments", tags=["maturity"])


@router.post(
    "",
    response_model=MaturityPackageOut,
    status_code=201,
    operation_id="createMaturityAssessment",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_or_get_draft(
    payload: MaturityPackageCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> MaturityPackageOut:
    return service.create_or_get_draft(ctx, payload)


@router.get(
    "",
    response_model=list[MaturityPackageOut],
    operation_id="listMaturityAssessments",
)
def list_packages(
    ctx: OrgContextDep,
    assessment_id: UUID = Query(..., description="Required assessment filter"),
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[MaturityPackageOut]:
    _ = cursor
    return service.list_packages(ctx, assessment_id)[:limit]


@router.get(
    "/{package_id}",
    response_model=MaturityPackageOut,
    operation_id="getMaturityAssessment",
    responses={404: ERROR_RESPONSES[404]},
)
def get_package(package_id: UUID, ctx: OrgContextDep) -> MaturityPackageOut:
    return service.get_package(ctx, package_id)


@router.put(
    "/{package_id}/scores",
    response_model=MaturityPackageOut,
    operation_id="upsertMaturityScores",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def upsert_scores(
    package_id: UUID, payload: ScoresUpsertIn, ctx: OrgContextDep
) -> MaturityPackageOut:
    return service.upsert_scores(ctx, package_id, payload)


@router.post(
    "/{package_id}/transitions/submit",
    response_model=MaturityTransitionResult,
    operation_id="submitMaturityAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def submit(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.submit(ctx, package_id)


@router.post(
    "/{package_id}/transitions/approve",
    response_model=MaturityTransitionResult,
    operation_id="approveMaturityAssessment",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def approve(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.approve(ctx, package_id)


@router.post(
    "/{package_id}/transitions/reject",
    response_model=MaturityTransitionResult,
    operation_id="rejectMaturityAssessment",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def reject(package_id: UUID, payload: ReasonIn, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.reject(ctx, package_id, payload)


@router.post(
    "/{package_id}/transitions/rework",
    response_model=MaturityTransitionResult,
    operation_id="reworkMaturityAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def rework(package_id: UUID, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.rework(ctx, package_id)


@router.post(
    "/{package_id}/transitions/discard",
    response_model=MaturityTransitionResult,
    operation_id="discardMaturityAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def discard(
    package_id: UUID,
    ctx: OrgContextDep,
    payload: DiscardIn | None = None,
) -> MaturityTransitionResult:
    return service.discard(ctx, package_id, payload)


@router.post(
    "/{package_id}/transitions/supersede",
    response_model=MaturityTransitionResult,
    operation_id="supersedeMaturityAssessment",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def supersede(package_id: UUID, payload: ReasonIn, ctx: OrgContextDep) -> MaturityTransitionResult:
    return service.supersede(ctx, package_id, payload)
