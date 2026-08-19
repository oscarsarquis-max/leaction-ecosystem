"""HTTP routes: ImprovementCase (ISOI-002)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.improvement_cases import service
from app.modules.improvement_cases.schemas import (
    ImprovementCaseCreate,
    ImprovementCaseOut,
    ImprovementCasePatch,
)
from app.schemas.common import ERROR_RESPONSES, LimitQuery

router = APIRouter(prefix="/organizations", tags=["improvement-cases"])


@router.post(
    "/current/improvement-cases",
    response_model=ImprovementCaseOut,
    status_code=201,
    operation_id="createCurrentOrganizationImprovementCase",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        422: ERROR_RESPONSES[422],
    },
    summary="Register a business problem (ImprovementCase) for the current organization",
)
def create_current_organization_improvement_case(
    payload: ImprovementCaseCreate,
    ctx: OrgContextDep,
) -> ImprovementCaseOut:
    return service.create_case(ctx, payload)


@router.get(
    "/current/improvement-cases",
    response_model=list[ImprovementCaseOut],
    operation_id="listCurrentOrganizationImprovementCases",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403]},
    summary="List improvement cases for the current organization (newest updated first)",
)
def list_current_organization_improvement_cases(
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
) -> list[ImprovementCaseOut]:
    return service.list_cases(ctx, limit=limit)


@router.get(
    "/current/improvement-cases/{case_id}",
    response_model=ImprovementCaseOut,
    operation_id="getCurrentOrganizationImprovementCase",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="Get one improvement case by id (current organization)",
)
def get_current_organization_improvement_case(
    case_id: UUID,
    ctx: OrgContextDep,
) -> ImprovementCaseOut:
    return service.get_case(ctx, case_id)


@router.patch(
    "/current/improvement-cases/{case_id}",
    response_model=ImprovementCaseOut,
    operation_id="patchCurrentOrganizationImprovementCase",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Update facts or status of an improvement case (valid transitions only)",
)
def patch_current_organization_improvement_case(
    case_id: UUID,
    payload: ImprovementCasePatch,
    ctx: OrgContextDep,
) -> ImprovementCaseOut:
    return service.patch_case(ctx, case_id, payload)
