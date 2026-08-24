"""HTTP routes — action measurement plans and indicators (ISOI-008)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.measurements import service
from app.modules.measurements.schemas import (
    IndicatorCreate,
    IndicatorOut,
    IndicatorRetireIn,
    IndicatorReviseIn,
    MeasurementCorrectionIn,
    MeasurementPlanCloseIn,
    MeasurementPlanCreate,
    MeasurementPlanOut,
    MeasurementPlanUpdate,
    MeasurementRecordCreate,
    MeasurementRecordOut,
    MeasurementSummaryOut,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(tags=["measurements"])

_PLANS = "/organizations/current/measurement-plans"


@router.post(
    _PLANS,
    response_model=MeasurementPlanOut,
    status_code=201,
    operation_id="createMeasurementPlan",
    summary="Plan how one action plan will prove it worked",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def create_measurement_plan(
    payload: MeasurementPlanCreate, ctx: OrgContextDep
) -> MeasurementPlanOut:
    return service.create_plan(ctx, payload)


@router.get(
    _PLANS,
    response_model=list[MeasurementPlanOut],
    operation_id="listMeasurementPlans",
)
def list_measurement_plans(
    ctx: OrgContextDep,
    action_plan_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[MeasurementPlanOut]:
    return service.list_plans(ctx, action_plan_id=action_plan_id, status=status)


@router.get(
    _PLANS + "/{plan_id}",
    response_model=MeasurementPlanOut,
    operation_id="getMeasurementPlan",
    responses={404: ERROR_RESPONSES[404]},
)
def get_measurement_plan(plan_id: UUID, ctx: OrgContextDep) -> MeasurementPlanOut:
    return service.get_plan(ctx, plan_id)


@router.patch(
    _PLANS + "/{plan_id}",
    response_model=MeasurementPlanOut,
    operation_id="patchMeasurementPlan",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def patch_measurement_plan(
    plan_id: UUID, payload: MeasurementPlanUpdate, ctx: OrgContextDep
) -> MeasurementPlanOut:
    return service.update_plan(ctx, plan_id, payload)


@router.post(
    _PLANS + "/{plan_id}/transitions/activate",
    response_model=MeasurementPlanOut,
    operation_id="activateMeasurementPlan",
    summary="Activate a measurement plan (requires an indicator with a baseline)",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def activate_measurement_plan(plan_id: UUID, ctx: OrgContextDep) -> MeasurementPlanOut:
    return service.activate_plan(ctx, plan_id)


@router.post(
    _PLANS + "/{plan_id}/transitions/close",
    response_model=MeasurementPlanOut,
    operation_id="closeMeasurementPlan",
    responses={409: ERROR_RESPONSES[409]},
)
def close_measurement_plan(
    plan_id: UUID, payload: MeasurementPlanCloseIn, ctx: OrgContextDep
) -> MeasurementPlanOut:
    return service.close_plan(ctx, plan_id, payload)


# --- indicators ---


@router.post(
    _PLANS + "/{plan_id}/indicators",
    response_model=IndicatorOut,
    status_code=201,
    operation_id="createIndicatorDefinition",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_indicator(
    plan_id: UUID, payload: IndicatorCreate, ctx: OrgContextDep
) -> IndicatorOut:
    return service.create_indicator(ctx, plan_id, payload)


@router.get(
    _PLANS + "/{plan_id}/indicators",
    response_model=list[IndicatorOut],
    operation_id="listIndicatorDefinitions",
)
def list_indicators(
    plan_id: UUID,
    ctx: OrgContextDep,
    include_superseded: bool = Query(
        default=False, description="Include superseded/retired versions (history)"
    ),
) -> list[IndicatorOut]:
    return service.list_indicators(
        ctx, plan_id, include_superseded=include_superseded
    )


@router.post(
    "/organizations/current/indicators/{indicator_id}/revise",
    response_model=IndicatorOut,
    operation_id="reviseIndicatorDefinition",
    summary="Revise an indicator (creates a new version once it has measurements)",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def revise_indicator(
    indicator_id: UUID, payload: IndicatorReviseIn, ctx: OrgContextDep
) -> IndicatorOut:
    return service.revise_indicator(ctx, indicator_id, payload)


@router.post(
    "/organizations/current/indicators/{indicator_id}/retire",
    response_model=IndicatorOut,
    operation_id="retireIndicatorDefinition",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def retire_indicator(
    indicator_id: UUID, payload: IndicatorRetireIn, ctx: OrgContextDep
) -> IndicatorOut:
    return service.retire_indicator(ctx, indicator_id, payload)


# --- measurement records ---


@router.post(
    _PLANS + "/{plan_id}/measurements",
    response_model=MeasurementRecordOut,
    status_code=201,
    operation_id="createMeasurementRecord",
    summary="Record a measurement (Idempotency-Key recommended)",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_measurement(
    plan_id: UUID,
    payload: MeasurementRecordCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> MeasurementRecordOut:
    if _idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": _idempotency_key})
    return service.create_measurement(ctx, plan_id, payload)


@router.get(
    _PLANS + "/{plan_id}/measurements",
    response_model=list[MeasurementRecordOut],
    operation_id="listMeasurementRecords",
)
def list_measurements(
    plan_id: UUID,
    ctx: OrgContextDep,
    indicator_definition_id: UUID | None = Query(default=None),
    include_superseded: bool = Query(
        default=False, description="Include corrected (superseded) readings"
    ),
) -> list[MeasurementRecordOut]:
    return service.list_measurements(
        ctx,
        plan_id,
        indicator_definition_id=indicator_definition_id,
        include_superseded=include_superseded,
    )


@router.post(
    "/organizations/current/measurements/{record_id}/correct",
    response_model=MeasurementRecordOut,
    status_code=201,
    operation_id="correctMeasurementRecord",
    summary="Correct a measurement by superseding it (history is preserved)",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def correct_measurement(
    record_id: UUID, payload: MeasurementCorrectionIn, ctx: OrgContextDep
) -> MeasurementRecordOut:
    return service.correct_measurement(ctx, record_id, payload)


# --- projection ---


@router.get(
    "/action-plans/{action_plan_id}/measurement-summary",
    response_model=MeasurementSummaryOut,
    operation_id="getActionPlanMeasurementSummary",
    summary="Does this action plan have proof that it worked?",
    responses={404: ERROR_RESPONSES[404]},
)
def get_measurement_summary(
    action_plan_id: UUID, ctx: OrgContextDep
) -> MeasurementSummaryOut:
    return service.get_action_plan_summary(ctx, action_plan_id)
