"""HTTP routes: ImprovementCase (ISOI-002)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.improvement_cases import analysis_service
from app.modules.improvement_cases import service
from app.modules.improvement_cases.problem_schemas import ImprovementCaseAnalysisRunOut
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


@router.post(
    "/current/improvement-cases/{case_id}/analysis-runs",
    response_model=ImprovementCaseAnalysisRunOut,
    status_code=201,
    operation_id="createCurrentOrganizationImprovementCaseAnalysisRun",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        502: ERROR_RESPONSES[502],
        503: ERROR_RESPONSES[503],
        504: ERROR_RESPONSES[504],
    },
    summary="Generate Problem Analysis for an improvement case (persist new run)",
)
def create_current_organization_improvement_case_analysis_run(
    case_id: UUID,
    ctx: OrgContextDep,
) -> ImprovementCaseAnalysisRunOut:
    return analysis_service.create_analysis_run(ctx, case_id)


@router.get(
    "/current/improvement-cases/{case_id}/analysis-runs",
    response_model=list[ImprovementCaseAnalysisRunOut],
    operation_id="listCurrentOrganizationImprovementCaseAnalysisRuns",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="List analysis runs for an improvement case (newest first)",
)
def list_current_organization_improvement_case_analysis_runs(
    case_id: UUID,
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
) -> list[ImprovementCaseAnalysisRunOut]:
    return analysis_service.list_analysis_runs(ctx, case_id, limit=limit)


@router.get(
    "/current/improvement-cases/{case_id}/analysis-runs/{run_id}",
    response_model=ImprovementCaseAnalysisRunOut,
    operation_id="getCurrentOrganizationImprovementCaseAnalysisRun",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="Get one analysis run for an improvement case",
)
def get_current_organization_improvement_case_analysis_run(
    case_id: UUID,
    run_id: UUID,
    ctx: OrgContextDep,
) -> ImprovementCaseAnalysisRunOut:
    return analysis_service.get_analysis_run(ctx, case_id, run_id)
