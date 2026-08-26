"""HTTP routes: ISO Intelligence Cockpit (ISOI-010) — GET only."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.auth.deps import OrgContextDep
from app.modules.cockpit import service
from app.modules.cockpit.schemas import (
    CockpitActivityPageOut,
    CockpitCasesPageOut,
    CockpitPriorityBand,
    CockpitSummaryOut,
    IntelligenceFreshness,
    parse_activity_window_days,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionPosture,
    SignalCategory,
)
from app.modules.improvement_cases.schemas import ImprovementCaseStatus
from app.schemas.common import ERROR_RESPONSES
from app.schemas.enums import MeasurementPosture, TargetPosture

router = APIRouter(prefix="/organizations", tags=["iso-intelligence-cockpit"])

_CACHE = "private, no-store"


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = _CACHE


@router.get(
    "/current/iso-intelligence/cockpit/summary",
    response_model=CockpitSummaryOut,
    operation_id="getCurrentOrganizationIsoIntelligenceCockpitSummary",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403]},
    summary="Organizational ISO Intelligence cockpit summary",
)
def get_cockpit_summary(
    ctx: OrgContextDep,
    response: Response,
    activity_window_days: int = Query(default=30, enum=[7, 30, 90]),
) -> CockpitSummaryOut:
    _no_store(response)
    try:
        window = parse_activity_window_days(activity_window_days)
    except ValueError as exc:
        from app.errors import AppError

        raise AppError("invalid_activity_window", str(exc), status_code=422) from exc
    return service.get_summary(ctx, activity_window_days=window)


@router.get(
    "/current/iso-intelligence/cockpit/cases",
    response_model=CockpitCasesPageOut,
    operation_id="listCurrentOrganizationIsoIntelligenceCockpitCases",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        422: ERROR_RESPONSES[422],
    },
    summary="Paginated cockpit attention queue",
)
def list_cockpit_cases(
    ctx: OrgContextDep,
    response: Response,
    case_status: list[ImprovementCaseStatus] | None = Query(default=None),
    priority_band: CockpitPriorityBand | None = Query(default=None),
    execution_posture: ExecutionPosture | None = Query(default=None),
    intelligence_freshness: IntelligenceFreshness | None = Query(default=None),
    measurement_posture: MeasurementPosture | None = Query(default=None),
    target_posture: TargetPosture | None = Query(default=None),
    signal_category: SignalCategory | None = Query(default=None),
    related_process: str | None = Query(default=None, max_length=400),
    search: str | None = Query(default=None, max_length=200),
    ready_for_review: bool | None = Query(default=None),
    has_overdue_actions: bool | None = Query(default=None),
    has_active_impediment: bool | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> CockpitCasesPageOut:
    _no_store(response)
    return service.list_cases(
        ctx,
        case_status=list(case_status) if case_status else None,
        priority_band=priority_band,
        execution_posture=execution_posture,
        intelligence_freshness=intelligence_freshness,
        measurement_posture=(
            measurement_posture.value
            if measurement_posture is not None
            else None
        ),
        target_posture=target_posture.value if target_posture is not None else None,
        signal_category=signal_category,
        related_process=related_process,
        search=search,
        ready_for_review=ready_for_review,
        has_overdue_actions=has_overdue_actions,
        has_active_impediment=has_active_impediment,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/current/iso-intelligence/cockpit/activity",
    response_model=CockpitActivityPageOut,
    operation_id="listCurrentOrganizationIsoIntelligenceCockpitActivity",
    responses={
        401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403],
        422: ERROR_RESPONSES[422],
    },
    summary="Recent safe operational activity for the cockpit",
)
def list_cockpit_activity(
    ctx: OrgContextDep,
    response: Response,
    activity_window_days: int = Query(default=30, enum=[7, 30, 90]),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> CockpitActivityPageOut:
    _no_store(response)
    try:
        window = parse_activity_window_days(activity_window_days)
    except ValueError as exc:
        from app.errors import AppError

        raise AppError("invalid_activity_window", str(exc), status_code=422) from exc
    return service.list_activity(
        ctx,
        activity_window_days=window,
        limit=limit,
        cursor=cursor,
    )
