from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.actions import service
from app.modules.actions.schemas import (
    ActionItemCreate,
    ActionItemOut,
    ActionItemTransitionResult,
    ActionPlanCreate,
    ActionPlanOut,
    ActionPlanTransitionResult,
    ReasonIn,
)
from app.schemas.common import (
    ERROR_RESPONSES,
    CursorQuery,
    IdempotencyKeyHeader,
    LimitQuery,
)

router = APIRouter(tags=["actions"])


@router.post(
    "/action-plans",
    response_model=ActionPlanOut,
    status_code=201,
    operation_id="createActionPlan",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_plan(
    payload: ActionPlanCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> ActionPlanOut:
    return service.create_plan(ctx, payload)


@router.get(
    "/action-plans",
    response_model=list[ActionPlanOut],
    operation_id="listActionPlans",
)
def list_plans(
    ctx: OrgContextDep,
    assessment_id: UUID | None = Query(default=None, description="Filter by assessment"),
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[ActionPlanOut]:
    _ = cursor
    return service.list_plans(ctx, assessment_id)[:limit]


@router.get(
    "/action-plans/{plan_id}",
    response_model=ActionPlanOut,
    operation_id="getActionPlan",
    responses={404: ERROR_RESPONSES[404]},
)
def get_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanOut:
    return service.get_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/activate",
    response_model=ActionPlanTransitionResult,
    operation_id="activateActionPlan",
    responses={409: ERROR_RESPONSES[409]},
)
def activate_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.activate_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/complete",
    response_model=ActionPlanTransitionResult,
    operation_id="completeActionPlan",
    responses={409: ERROR_RESPONSES[409]},
)
def complete_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.complete_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/cancel",
    response_model=ActionPlanTransitionResult,
    operation_id="cancelActionPlan",
    responses={409: ERROR_RESPONSES[409]},
)
def cancel_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.cancel_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/items",
    response_model=ActionItemOut,
    status_code=201,
    operation_id="createActionItem",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_item(
    plan_id: UUID,
    payload: ActionItemCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> ActionItemOut:
    return service.create_item(ctx, plan_id, payload)


@router.get(
    "/action-plans/{plan_id}/items",
    response_model=list[ActionItemOut],
    operation_id="listActionItems",
)
def list_items(
    plan_id: UUID,
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[ActionItemOut]:
    _ = cursor
    return service.list_items(ctx, plan_id)[:limit]


@router.get(
    "/action-items/{item_id}",
    response_model=ActionItemOut,
    operation_id="getActionItem",
    responses={404: ERROR_RESPONSES[404]},
)
def get_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemOut:
    return service.get_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/start",
    response_model=ActionItemTransitionResult,
    operation_id="startActionItem",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def start_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.start_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/mark_implemented",
    response_model=ActionItemTransitionResult,
    operation_id="markActionItemImplemented",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def mark_implemented(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.mark_implemented(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/validate",
    response_model=ActionItemTransitionResult,
    operation_id="validateActionItem",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def validate_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.validate_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/reject_implementation",
    response_model=ActionItemTransitionResult,
    operation_id="rejectActionItemImplementation",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def reject_implementation(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.reject_implementation(ctx, item_id, payload)


@router.post(
    "/action-items/{item_id}/transitions/confirm_efficacy",
    response_model=ActionItemTransitionResult,
    operation_id="confirmActionItemEfficacy",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def confirm_efficacy(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.confirm_efficacy(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/fail_efficacy",
    response_model=ActionItemTransitionResult,
    operation_id="failActionItemEfficacy",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def fail_efficacy(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.fail_efficacy(ctx, item_id, payload)


@router.post(
    "/action-items/{item_id}/transitions/reopen",
    response_model=ActionItemTransitionResult,
    operation_id="reopenActionItem",
    responses={409: ERROR_RESPONSES[409]},
)
def reopen_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.reopen_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/close_ineffective",
    response_model=ActionItemTransitionResult,
    operation_id="closeIneffectiveActionItem",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
)
def close_ineffective(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.close_ineffective(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/cancel",
    response_model=ActionItemTransitionResult,
    operation_id="cancelActionItem",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def cancel_item(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.cancel_item(ctx, item_id, payload)
