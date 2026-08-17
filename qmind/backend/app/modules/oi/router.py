"""HTTP routes: Core → OI organizational intelligence."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.oi import service
from app.modules.oi.schemas import OrganizationIntelligenceRunOut, OrganizationalInsights
from app.schemas.common import ERROR_RESPONSES, LimitQuery

router = APIRouter(prefix="/organizations", tags=["organizational-intelligence"])


@router.post(
    "/current/intelligence/analyze",
    response_model=OrganizationalInsights,
    operation_id="analyzeCurrentOrganizationIntelligence",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        502: ERROR_RESPONSES[502],
        503: ERROR_RESPONSES[503],
        504: ERROR_RESPONSES[504],
    },
    summary="Analyze current organization via QMind OI (HTTP) and persist the run",
)
def analyze_current_organization_intelligence(ctx: OrgContextDep) -> OrganizationalInsights:
    """
    Loads the persistent Organization Profile for the OrgContext tenant,
    builds OrganizationContextInput v1, calls QMind OI over HTTP, and stores
    the successful OrganizationalInsights envelope for the current organization.
    """
    return service.analyze_current_organization(ctx)


@router.get(
    "/current/intelligence/runs",
    response_model=list[OrganizationIntelligenceRunOut],
    operation_id="listCurrentOrganizationIntelligenceRuns",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403]},
    summary="List organizational intelligence runs for current tenant (newest first)",
)
def list_current_organization_intelligence_runs(
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
) -> list[OrganizationIntelligenceRunOut]:
    return service.list_intelligence_runs(ctx, limit=limit)


@router.get(
    "/current/intelligence/runs/{run_id}",
    response_model=OrganizationIntelligenceRunOut,
    operation_id="getCurrentOrganizationIntelligenceRun",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
    },
    summary="Get one organizational intelligence run by id (current tenant)",
)
def get_current_organization_intelligence_run(
    run_id: UUID,
    ctx: OrgContextDep,
) -> OrganizationIntelligenceRunOut:
    return service.get_intelligence_run(ctx, run_id)
