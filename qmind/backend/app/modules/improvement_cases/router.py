"""HTTP routes: ImprovementCase (ISOI-002)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header

from app.auth.deps import OrgContextDep
from app.modules.actions.schemas import (
    ActionItemOut,
    FindingActionCreate,
    ImprovementCaseActionsOut,
)
from app.modules.improvement_cases import analysis_service
from app.modules.improvement_cases import evolution_service
from app.modules.improvement_cases import execution_intelligence_service
from app.modules.improvement_cases import finding_actions
from app.modules.improvement_cases import service
from app.modules.improvement_cases.evolution_schemas import (
    ImprovementCaseEvolutionOut,
    OutcomeObservationCreate,
    OutcomeObservationOut,
)
from app.modules.improvement_cases.problem_schemas import ImprovementCaseAnalysisRunOut
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceRunOut,
)
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


@router.post(
    "/current/improvement-cases/{case_id}/execution-intelligence/runs",
    response_model=ExecutionIntelligenceRunOut,
    status_code=201,
    operation_id="createCurrentOrganizationImprovementCaseExecutionIntelligenceRun",
    responses={
        401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422], 502: ERROR_RESPONSES[502],
        503: ERROR_RESPONSES[503], 504: ERROR_RESPONSES[504],
    },
    summary="Interpret the current execution facts through QMind OI",
)
def create_current_organization_execution_intelligence_run(
    case_id: UUID,
    ctx: OrgContextDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ExecutionIntelligenceRunOut:
    return execution_intelligence_service.create_run(
        ctx, case_id, idempotency_key=idempotency_key
    )


@router.get(
    "/current/improvement-cases/{case_id}/execution-intelligence/runs",
    response_model=list[ExecutionIntelligenceRunOut],
    operation_id="listCurrentOrganizationImprovementCaseExecutionIntelligenceRuns",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="List immutable Execution Intelligence runs",
)
def list_current_organization_execution_intelligence_runs(
    case_id: UUID, ctx: OrgContextDep, limit: LimitQuery = 50
) -> list[ExecutionIntelligenceRunOut]:
    return execution_intelligence_service.list_runs(ctx, case_id, limit=limit)


@router.get(
    "/current/improvement-cases/{case_id}/execution-intelligence/latest",
    response_model=ExecutionIntelligenceRunOut,
    operation_id="getLatestCurrentOrganizationImprovementCaseExecutionIntelligence",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="Get the latest Execution Intelligence run",
)
def get_latest_current_organization_execution_intelligence(
    case_id: UUID, ctx: OrgContextDep
) -> ExecutionIntelligenceRunOut:
    return execution_intelligence_service.latest_run(ctx, case_id)


@router.get(
    "/current/improvement-cases/{case_id}/execution-intelligence/runs/{run_id}",
    response_model=ExecutionIntelligenceRunOut,
    operation_id="getCurrentOrganizationImprovementCaseExecutionIntelligenceRun",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="Get one immutable Execution Intelligence run",
)
def get_current_organization_execution_intelligence_run(
    case_id: UUID, run_id: UUID, ctx: OrgContextDep
) -> ExecutionIntelligenceRunOut:
    return execution_intelligence_service.get_run(ctx, case_id, run_id)


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


@router.post(
    "/current/improvement-cases/{case_id}/analysis-runs/{run_id}/findings/{finding_code}/actions",
    response_model=ActionItemOut,
    status_code=201,
    operation_id="createActionFromImprovementCaseFinding",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Create an ActionItem from an analysis finding (human confirmation)",
)
def create_action_from_improvement_case_finding(
    case_id: UUID,
    run_id: UUID,
    finding_code: str,
    payload: FindingActionCreate,
    ctx: OrgContextDep,
) -> ActionItemOut:
    return finding_actions.create_action_from_finding(
        ctx, case_id, run_id, finding_code, payload
    )


@router.get(
    "/current/improvement-cases/{case_id}/actions",
    response_model=ImprovementCaseActionsOut,
    operation_id="listCurrentOrganizationImprovementCaseActions",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="List ActionPlan and ActionItems for an improvement case",
)
def list_current_organization_improvement_case_actions(
    case_id: UUID,
    ctx: OrgContextDep,
) -> ImprovementCaseActionsOut:
    return finding_actions.list_case_actions(ctx, case_id)


@router.post(
    "/current/improvement-cases/{case_id}/outcome-observations",
    response_model=OutcomeObservationOut,
    status_code=201,
    operation_id="createCurrentOrganizationImprovementCaseOutcomeObservation",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        422: ERROR_RESPONSES[422],
    },
    summary="Register an observed outcome for an improvement case",
)
def create_current_organization_improvement_case_outcome_observation(
    case_id: UUID,
    payload: OutcomeObservationCreate,
    ctx: OrgContextDep,
) -> OutcomeObservationOut:
    return evolution_service.create_outcome_observation(ctx, case_id, payload)


@router.get(
    "/current/improvement-cases/{case_id}/outcome-observations",
    response_model=list[OutcomeObservationOut],
    operation_id="listCurrentOrganizationImprovementCaseOutcomeObservations",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="List outcome observations for an improvement case (newest first)",
)
def list_current_organization_improvement_case_outcome_observations(
    case_id: UUID,
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
) -> list[OutcomeObservationOut]:
    return evolution_service.list_outcome_observations(ctx, case_id, limit=limit)


@router.get(
    "/current/improvement-cases/{case_id}/evolution",
    response_model=ImprovementCaseEvolutionOut,
    operation_id="getCurrentOrganizationImprovementCaseEvolution",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="Read-only evolution projection for an improvement case",
)
def get_current_organization_improvement_case_evolution(
    case_id: UUID,
    ctx: OrgContextDep,
) -> ImprovementCaseEvolutionOut:
    return evolution_service.get_evolution(ctx, case_id)
