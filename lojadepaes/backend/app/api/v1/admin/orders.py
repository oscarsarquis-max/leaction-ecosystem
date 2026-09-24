from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.adaptations import evaluate_adaptation
from app.domain.admin_orders import get_order_detail, list_orders
from app.domain.errors import NotFoundError
from app.domain.orders import add_internal_note, transition_order
from app.domain.storefront_orders import propose_production_date
from app.models.enums import OrderStatus
from app.models.orders import Order
from app.schemas.admin import (
    AdaptationEvaluateIn,
    CancelRequest,
    NoteCreateRequest,
    NoteOut,
    OrderDetailOut,
    OrderListOut,
    OrderListQuery,
)
from app.schemas.storefront import ProposeDateIn

router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


@router.get("", response_model=OrderListOut)
def admin_list_orders(
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    query: Annotated[OrderListQuery, Depends()],
) -> OrderListOut:
    del principal
    return list_orders(db, settings, query)


@router.get("/{order_id}", response_model=OrderDetailOut)
def admin_get_order(order_id: UUID, db: DbSession, principal: AdminUser) -> OrderDetailOut:
    del principal
    return get_order_detail(db, order_id)


@router.post("/{order_id}/confirm", response_model=OrderDetailOut)
def admin_confirm_order(order_id: UUID, db: DbSession, principal: AdminUser) -> OrderDetailOut:
    transition_order(db, order_id, OrderStatus.CONFIRMED.value, actor_ref=principal.actor_ref)
    return get_order_detail(db, order_id)


@router.post("/{order_id}/propose-date", response_model=OrderDetailOut)
def admin_propose_date(
    order_id: UUID, payload: ProposeDateIn, db: DbSession, principal: AdminUser
) -> OrderDetailOut:
    del principal
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("pedido não encontrado")
    propose_production_date(db, order, payload.date)
    return get_order_detail(db, order_id)


@router.post("/{order_id}/start-production", response_model=OrderDetailOut)
def admin_start_production(order_id: UUID, db: DbSession, principal: AdminUser) -> OrderDetailOut:
    transition_order(db, order_id, OrderStatus.IN_PRODUCTION.value, actor_ref=principal.actor_ref)
    return get_order_detail(db, order_id)


@router.post("/{order_id}/mark-ready", response_model=OrderDetailOut)
def admin_mark_ready(order_id: UUID, db: DbSession, principal: AdminUser) -> OrderDetailOut:
    transition_order(db, order_id, OrderStatus.READY.value, actor_ref=principal.actor_ref)
    return get_order_detail(db, order_id)


@router.post("/{order_id}/complete", response_model=OrderDetailOut)
def admin_complete_order(order_id: UUID, db: DbSession, principal: AdminUser) -> OrderDetailOut:
    transition_order(db, order_id, OrderStatus.COMPLETED.value, actor_ref=principal.actor_ref)
    return get_order_detail(db, order_id)


@router.post("/{order_id}/cancel", response_model=OrderDetailOut)
def admin_cancel_order(
    order_id: UUID, payload: CancelRequest, db: DbSession, principal: AdminUser
) -> OrderDetailOut:
    transition_order(
        db,
        order_id,
        OrderStatus.CANCELLED.value,
        payload.reason,
        actor_ref=principal.actor_ref,
    )
    return get_order_detail(db, order_id)


@router.post("/{order_id}/items/{item_id}/adaptation", response_model=OrderDetailOut)
def admin_evaluate_adaptation(
    order_id: UUID,
    item_id: UUID,
    payload: AdaptationEvaluateIn,
    db: DbSession,
    principal: AdminUser,
) -> OrderDetailOut:
    evaluate_adaptation(
        db,
        order_id,
        item_id,
        decision=payload.decision,
        response=payload.response,
        actor_ref=principal.actor_ref,
    )
    return get_order_detail(db, order_id)


@router.post("/{order_id}/notes", response_model=NoteOut)
def admin_add_note(
    order_id: UUID, payload: NoteCreateRequest, db: DbSession, principal: AdminUser
) -> NoteOut:
    note = add_internal_note(db, order_id, payload.body, actor_ref=principal.actor_ref)
    return NoteOut(
        id=note.id, body=note.body, author_ref=note.author_ref, created_at=note.created_at
    )
