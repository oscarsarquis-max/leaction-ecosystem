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

router = APIRouter(tags=["actions"])


@router.post("/action-plans", response_model=ActionPlanOut, status_code=201)
def create_plan(payload: ActionPlanCreate, ctx: OrgContextDep) -> ActionPlanOut:
    return service.create_plan(ctx, payload)


@router.get("/action-plans", response_model=list[ActionPlanOut])
def list_plans(
    ctx: OrgContextDep,
    assessment_id: UUID | None = Query(default=None),
) -> list[ActionPlanOut]:
    return service.list_plans(ctx, assessment_id)


@router.get("/action-plans/{plan_id}", response_model=ActionPlanOut)
def get_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanOut:
    return service.get_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/activate",
    response_model=ActionPlanTransitionResult,
)
def activate_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.activate_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/complete",
    response_model=ActionPlanTransitionResult,
)
def complete_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.complete_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/transitions/cancel",
    response_model=ActionPlanTransitionResult,
)
def cancel_plan(plan_id: UUID, ctx: OrgContextDep) -> ActionPlanTransitionResult:
    return service.cancel_plan(ctx, plan_id)


@router.post(
    "/action-plans/{plan_id}/items",
    response_model=ActionItemOut,
    status_code=201,
)
def create_item(plan_id: UUID, payload: ActionItemCreate, ctx: OrgContextDep) -> ActionItemOut:
    return service.create_item(ctx, plan_id, payload)


@router.get("/action-plans/{plan_id}/items", response_model=list[ActionItemOut])
def list_items(plan_id: UUID, ctx: OrgContextDep) -> list[ActionItemOut]:
    return service.list_items(ctx, plan_id)


@router.get("/action-items/{item_id}", response_model=ActionItemOut)
def get_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemOut:
    return service.get_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/start",
    response_model=ActionItemTransitionResult,
)
def start_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.start_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/mark_implemented",
    response_model=ActionItemTransitionResult,
)
def mark_implemented(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.mark_implemented(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/validate",
    response_model=ActionItemTransitionResult,
)
def validate_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.validate_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/reject_implementation",
    response_model=ActionItemTransitionResult,
)
def reject_implementation(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.reject_implementation(ctx, item_id, payload)


@router.post(
    "/action-items/{item_id}/transitions/confirm_efficacy",
    response_model=ActionItemTransitionResult,
)
def confirm_efficacy(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.confirm_efficacy(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/fail_efficacy",
    response_model=ActionItemTransitionResult,
)
def fail_efficacy(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.fail_efficacy(ctx, item_id, payload)


@router.post(
    "/action-items/{item_id}/transitions/reopen",
    response_model=ActionItemTransitionResult,
)
def reopen_item(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.reopen_item(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/close_ineffective",
    response_model=ActionItemTransitionResult,
)
def close_ineffective(item_id: UUID, ctx: OrgContextDep) -> ActionItemTransitionResult:
    return service.close_ineffective(ctx, item_id)


@router.post(
    "/action-items/{item_id}/transitions/cancel",
    response_model=ActionItemTransitionResult,
)
def cancel_item(
    item_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ActionItemTransitionResult:
    return service.cancel_item(ctx, item_id, payload)
