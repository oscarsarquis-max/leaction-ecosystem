from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.findings import service
from app.modules.findings.schemas import (
    DiscardIn,
    FindingCreate,
    FindingOut,
    FindingTransitionResult,
    FindingUpdate,
    RejectIn,
    WithdrawIn,
)
from app.schemas.common import (
    ERROR_RESPONSES,
    CursorQuery,
    IdempotencyKeyHeader,
    LimitQuery,
)

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post(
    "",
    response_model=FindingOut,
    status_code=201,
    operation_id="createFinding",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_finding(
    payload: FindingCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> FindingOut:
    return service.create_draft(ctx, payload)


@router.get(
    "",
    response_model=list[FindingOut],
    operation_id="listFindings",
    summary="List findings (filters + pagination query)",
)
def list_findings(
    ctx: OrgContextDep,
    assessment_id: UUID | None = Query(
        default=None, description="Filter by assessment UUID"
    ),
    include_discarded: bool = Query(default=False),
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[FindingOut]:
    _ = cursor
    items = service.list_findings(ctx, assessment_id, include_discarded=include_discarded)
    return items[:limit]


@router.get(
    "/{finding_id}",
    response_model=FindingOut,
    operation_id="getFinding",
    responses={404: ERROR_RESPONSES[404]},
)
def get_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingOut:
    return service.get_finding(ctx, finding_id)


@router.patch(
    "/{finding_id}",
    response_model=FindingOut,
    operation_id="updateFinding",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Update finding draft (requirements + approved evidence links)",
)
def update_finding(
    finding_id: UUID,
    payload: FindingUpdate,
    ctx: OrgContextDep,
) -> FindingOut:
    return service.update_draft(ctx, finding_id, payload)


@router.post(
    "/{finding_id}/transitions/submit",
    response_model=FindingTransitionResult,
    operation_id="submitFinding",
    responses={409: ERROR_RESPONSES[409]},
)
def submit_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.submit(ctx, finding_id)


@router.post(
    "/{finding_id}/transitions/approve",
    response_model=FindingTransitionResult,
    operation_id="approveFinding",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def approve_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.approve(ctx, finding_id)


@router.post(
    "/{finding_id}/transitions/reject",
    response_model=FindingTransitionResult,
    operation_id="rejectFinding",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def reject_finding(
    finding_id: UUID, payload: RejectIn, ctx: OrgContextDep
) -> FindingTransitionResult:
    return service.reject(ctx, finding_id, payload)


@router.post(
    "/{finding_id}/transitions/discard",
    response_model=FindingTransitionResult,
    operation_id="discardFinding",
    responses={409: ERROR_RESPONSES[409]},
)
def discard_finding(
    finding_id: UUID,
    ctx: OrgContextDep,
    payload: DiscardIn | None = None,
) -> FindingTransitionResult:
    return service.discard(ctx, finding_id, payload)


@router.post(
    "/{finding_id}/transitions/withdraw",
    response_model=FindingTransitionResult,
    operation_id="withdrawFinding",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def withdraw_finding(
    finding_id: UUID, payload: WithdrawIn, ctx: OrgContextDep
) -> FindingTransitionResult:
    return service.withdraw(ctx, finding_id, payload)


@router.post(
    "/{finding_id}/transitions/rework",
    response_model=FindingTransitionResult,
    operation_id="reworkFinding",
    responses={409: ERROR_RESPONSES[409]},
)
def rework_finding(finding_id: UUID, ctx: OrgContextDep) -> FindingTransitionResult:
    return service.rework(ctx, finding_id)
