"""HTTP routes: Core → OI organizational intelligence."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.oi import service
from app.modules.oi.schemas import OrganizationalInsights
from app.schemas.common import ERROR_RESPONSES

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
    summary="Analyze current organization via QMind OI (HTTP)",
)
def analyze_current_organization_intelligence(ctx: OrgContextDep) -> OrganizationalInsights:
    """
    Loads the persistent Organization Profile for the OrgContext tenant,
    builds OrganizationContextInput v1, and calls QMind OI over HTTP.
    """
    return service.analyze_current_organization(ctx)
