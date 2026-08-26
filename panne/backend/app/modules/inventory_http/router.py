from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.inventory_http import serialize
from app.modules.inventory_procurement import services
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyBody(StrictModel):
    code: str
    display_name: str | None = None
    establishment_id: UUID | None = None
    allow_negative_balance: bool = False
    lot_mode: str = "optional"
    expiry_required: bool = False
    lot_consumption: str = "fefo_suggest"
    receipt_tolerance_percent: str = "0"
    count_tolerance_percent: str = "0"
    reserve_on_release: bool = False
    cancelled_order_treatment: str = "release_reservation"
    return_restores_available: bool = True
    waste_reduces_physical: bool = True
    adjust_requires_approval: bool = True
    lock_location_on_count: bool = True
    expiry_alert_days: int = 7
    justification: str | None = None
    effective_from: str


class LocationBody(StrictModel):
    establishment_id: UUID
    code: str
    display_name: str | None = None
    kind: str
    responsible_user_id: UUID | None = None


class StatusBody(StrictModel):
    status: str


class ItemBody(StrictModel):
    ingredient_id: UUID
    unit_code: str
    lot_control: str = "optional"
    expiry_control: bool = False
    reorder_point: str | None = None
    safety_stock: str | None = None
    target_quantity: str | None = None
    preferred_supplier_id: UUID | None = None
    preferred_supplier_item_id: UUID | None = None


class LotStatusBody(StrictModel):
    status: str
    reason: str


class OpeningBody(StrictModel):
    inventory_item_id: UUID
    inventory_location_id: UUID
    quantity: str
    supplier_lot_code: str | None = None
    manufactured_on: str | None = None
    expires_on: str | None = None
    reason: str | None = None


class MovementBody(StrictModel):
    movement_type: str
    inventory_item_id: UUID
    inventory_lot_id: UUID | None = None
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    quantity: str
    unit_code: str | None = None
    origin_type: str | None = None
    origin_id: UUID | None = None
    production_order_id: UUID | None = None
    production_batch_id: UUID | None = None
    reason: str | None = None
    approved: bool = False
    expired_override: bool = False
    effective_at: str | None = None


class AllocationBody(StrictModel):
    inventory_lot_id: UUID
    quantity: str


class ReserveBody(StrictModel):
    production_order_id: UUID
    production_batch_id: UUID | None = None
    inventory_item_id: UUID
    required_quantity: str
    allocations: list[AllocationBody] | None = None
    adopt_historical: bool = False
    reason: str | None = None


class PickLineBody(StrictModel):
    inventory_item_id: UUID
    inventory_lot_id: UUID
    quantity: str
    suggested: bool = False
    substituted: bool = False
    reason: str | None = None
    expired_override: bool = False


class PickBody(StrictModel):
    production_order_id: UUID
    production_batch_id: UUID | None = None
    lines: list[PickLineBody]


class ConsumptionBody(StrictModel):
    ingredient_id: UUID
    inventory_lot_id: UUID | None = None
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    expired_override: bool = False


class CountBody(StrictModel):
    inventory_location_id: UUID
    cutoff_at: str
    require_second_count: bool = False


class CountEntryBody(StrictModel):
    inventory_count_scope_id: UUID
    pass_number: int
    quantity: str


class ReviewBody(StrictModel):
    decision: str
    reason: str | None = None


class ReplenishBody(StrictModel):
    horizon_days: int = 7


class RequisitionItemBody(StrictModel):
    inventory_item_id: UUID
    quantity: str
    unit_code: str


class RequisitionBody(StrictModel):
    establishment_id: UUID
    inventory_location_id: UUID | None = None
    needed_by: str | None = None
    justification: str
    origin_type: str = "manual"
    origin_id: UUID | None = None
    items: list[RequisitionItemBody]


class QuotationItemBody(StrictModel):
    inventory_item_id: UUID
    supplier_item_id: UUID | None = None
    quantity: str
    package_quantity: str | None = None
    unit_code: str
    unit_price: str


class QuotationBody(StrictModel):
    supplier_id: UUID
    valid_until: str | None = None
    lead_time_days: int | None = None
    conditions: str | None = None
    evidence_ref: str | None = None
    currency: str = "BRL"
    items: list[QuotationItemBody]


class OrderItemBody(StrictModel):
    inventory_item_id: UUID
    supplier_item_id: UUID | None = None
    procurement_requisition_item_id: UUID | None = None
    procurement_quotation_item_id: UUID | None = None
    quantity: str
    package_quantity: str | None = None
    unit_code: str
    unit_price: str


class OrderBody(StrictModel):
    establishment_id: UUID
    supplier_id: UUID
    inventory_location_id: UUID
    expected_at: str | None = None
    currency: str = "BRL"
    items: list[OrderItemBody]


class OrderReviseBody(StrictModel):
    reason: str | None = None
    items: list[OrderItemBody]


class ReceiptItemBody(StrictModel):
    procurement_order_item_id: UUID
    quantity: str
    unit_code: str | None = None
    supplier_lot_code: str | None = None
    manufactured_on: str | None = None
    expires_on: str | None = None
    observed_unit_price: str | None = None
    quarantine: bool = False


class ReceiptBody(StrictModel):
    procurement_order_id: UUID
    inventory_location_id: UUID | None = None
    evidence_ref: str | None = None
    items: list[ReceiptItemBody]


class ReturnBody(StrictModel):
    procurement_receipt_id: UUID
    inventory_lot_id: UUID
    quantity: str
    reason: str


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)
        raise


def _command_keys(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key)


@router.get("/inventory/policies")
def list_policies(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_policies(session, principal))
    return {"items": [serialize.policy_out(row, services.latest_policy_version(session, row.id)) for row in rows]}


@router.post("/inventory/policies")
def create_policy(
    body: PolicyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_policy(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {
        "data": serialize.policy_out(row, services.latest_policy_version(session, row.id)),
        "row_version": row.row_version,
    }


@router.post("/inventory/policies/{policy_id}/publish")
def publish_policy(
    policy_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.publish_policy(
            session, principal, policy_id, expected_version=parse_if_match(if_match, required=False), idempotency_key=idempotency_key
        )
    )
    return {
        "data": serialize.policy_out(row, services.latest_policy_version(session, row.id)),
        "row_version": row.row_version,
    }


@router.post("/inventory/policies/{policy_id}/revise")
def revise_policy(
    policy_id: UUID,
    body: PolicyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.revise_policy(
            session,
            principal,
            policy_id,
            body.model_dump(),
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {
        "data": serialize.policy_out(row, services.latest_policy_version(session, row.id)),
        "row_version": row.row_version,
    }


@router.get("/inventory/locations")
def list_locations(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.location_out(row) for row in _run(lambda: services.list_locations(session, principal))]}


@router.post("/inventory/locations")
def create_location(
    body: LocationBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_location(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.location_out(row), "row_version": row.row_version}


@router.post("/inventory/locations/{location_id}/status")
def location_status(
    location_id: UUID,
    body: StatusBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.set_location_status(
            session,
            principal,
            location_id,
            body.status,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.location_out(row), "row_version": row.row_version}


@router.get("/inventory/items")
def list_items(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.item_out(row) for row in _run(lambda: services.list_items(session, principal))]}


@router.post("/inventory/items")
def create_item(
    body: ItemBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_item(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.item_out(row), "row_version": row.row_version}


@router.get("/inventory/lots")
def list_lots(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.lot_out(row, session) for row in _run(lambda: services.list_lots(session, principal))]}


@router.post("/inventory/lots/{lot_id}/status")
def lot_status(
    lot_id: UUID,
    body: LotStatusBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.set_lot_status(
            session,
            principal,
            lot_id,
            body.status,
            body.reason,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.lot_out(row), "row_version": row.row_version}


@router.get("/inventory/balances")
def list_balances(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.balance_out(row, session) for row in _run(lambda: services.list_balances(session, principal))]}


@router.get("/inventory/movements")
def list_movements(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.movement_out(row) for row in _run(lambda: services.list_movements(session, principal))]}


@router.post("/inventory/openings")
def open_balance(
    body: OpeningBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.open_balance(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.lot_out(row), "row_version": row.row_version}


@router.post("/inventory/movements")
def post_movement(
    body: MovementBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.post_movement(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.movement_out(row)}


@router.get("/inventory/fefo")
def fefo(
    inventory_item_id: UUID,
    quantity: str,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": _run(lambda: services.suggest_fefo(session, principal, inventory_item_id, quantity))}


@router.get("/inventory/reservations")
def list_reservations(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_reservations(session, principal))
    return {
        "items": [
            serialize.reservation_out(row, services.reservation_allocations(session, row.id)) for row in rows
        ]
    }


@router.post("/inventory/reservations")
def reserve(
    body: ReserveBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    payload = body.model_dump()
    row = _run(lambda: services.reserve_order(session, principal, payload, idempotency_key=idempotency_key))
    return {
        "data": serialize.reservation_out(row, services.reservation_allocations(session, row.id)),
        "row_version": row.row_version,
    }


@router.post("/inventory/reservations/{reservation_id}/release")
def release_reservation(
    reservation_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.release_reservation(
            session,
            principal,
            reservation_id,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.reservation_out(row), "row_version": row.row_version}


@router.post("/inventory/picks")
def confirm_pick(
    body: PickBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.confirm_pick(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.pick_out(row, services.pick_lines(session, row.id)), "row_version": row.row_version}


@router.get("/inventory/picks")
def list_picks(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_picks(session, principal))
    return {"items": [serialize.pick_out(row, services.pick_lines(session, row.id)) for row in rows]}


@router.post("/inventory/consumptions/{consumption_id}/post")
def post_consumption(
    consumption_id: UUID,
    body: ConsumptionBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.post_consumption(
            session, principal, consumption_id, body.model_dump(), idempotency_key=idempotency_key
        )
    )
    return {"data": {"id": str(row.id), "status": row.status, "last_error": row.last_error}}


@router.get("/inventory/counts")
def list_counts(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_counts(session, principal))
    return {"items": [serialize.count_out(row, services.count_variances(session, row)) for row in rows]}


@router.post("/inventory/counts")
def create_count(
    body: CountBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_count(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.count_out(row), "row_version": row.row_version}


@router.post("/inventory/counts/{session_id}/scope")
def freeze_scope(
    session_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.freeze_count_scope(
            session, principal, session_id, expected_version=parse_if_match(if_match, required=False), idempotency_key=idempotency_key
        )
    )
    return {"data": serialize.count_out(row, services.count_variances(session, row)), "row_version": row.row_version}


@router.post("/inventory/counts/{session_id}/entries")
def record_count(
    session_id: UUID,
    body: CountEntryBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.record_count(
            session, principal, session_id, body.model_dump(), idempotency_key=idempotency_key
        )
    )
    return {"data": serialize.count_out(row, services.count_variances(session, row)), "row_version": row.row_version}


@router.post("/inventory/counts/{session_id}/review")
def review_count(
    session_id: UUID,
    body: ReviewBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.review_count(
            session,
            principal,
            session_id,
            body.model_dump(),
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.count_out(row, services.count_variances(session, row)), "row_version": row.row_version}


@router.post("/inventory/counts/{session_id}/approve")
def approve_count(
    session_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.approve_count(
            session, principal, session_id, expected_version=parse_if_match(if_match, required=False), idempotency_key=idempotency_key
        )
    )
    return {"data": serialize.count_out(row, services.count_variances(session, row)), "row_version": row.row_version}


@router.post("/inventory/replenishment")
def replenish(
    body: ReplenishBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.suggest_replenishment(session, principal, body.model_dump(), idempotency_key=idempotency_key)
    )
    return {"data": serialize.suggestion_out(row, services.replenishment_items(session, row.id), session)}


@router.get("/procurement/requisitions")
def list_requisitions(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_requisitions(session, principal))
    return {"items": [serialize.requisition_out(row, services.requisition_items(session, row.id)) for row in rows]}


@router.post("/procurement/requisitions")
def create_requisition(
    body: RequisitionBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.create_requisition(session, principal, body.model_dump(), idempotency_key=idempotency_key)
    )
    return {
        "data": serialize.requisition_out(row, services.requisition_items(session, row.id)),
        "row_version": row.row_version,
    }


@router.post("/procurement/requisitions/{requisition_id}/transition")
def transition_requisition(
    requisition_id: UUID,
    body: StatusBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.transition_requisition(
            session,
            principal,
            requisition_id,
            body.status,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.requisition_out(row), "row_version": row.row_version}


@router.get("/procurement/quotations")
def list_quotations(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_quotations(session, principal))
    return {"items": [serialize.quotation_out(row, services.quotation_items(session, row.id), session) for row in rows]}


@router.post("/procurement/quotations")
def create_quotation(
    body: QuotationBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_quotation(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.quotation_out(row, services.quotation_items(session, row.id)), "row_version": row.row_version}


@router.get("/procurement/quotations/compare")
def compare_quotations(
    inventory_item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": _run(lambda: services.compare_quotations(session, principal, inventory_item_id))}


@router.get("/procurement/orders")
def list_orders(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_orders(session, principal))
    return {"items": [serialize.order_out(row, services.current_order_items(session, row), session) for row in rows]}


@router.post("/procurement/orders")
def create_order(
    body: OrderBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_order(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.order_out(row, services.current_order_items(session, row)), "row_version": row.row_version}


@router.post("/procurement/orders/{order_id}/transition")
def transition_order(
    order_id: UUID,
    body: StatusBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.transition_order(
            session,
            principal,
            order_id,
            body.status,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.order_out(row), "row_version": row.row_version}


@router.post("/procurement/orders/{order_id}/revise")
def revise_order(
    order_id: UUID,
    body: OrderReviseBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.revise_order(
            session,
            principal,
            order_id,
            body.model_dump(),
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": serialize.order_out(row, services.current_order_items(session, row)), "row_version": row.row_version}


@router.get("/procurement/receipts")
def list_receipts(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_receipts(session, principal))
    return {"items": [serialize.receipt_out(row, services.receipt_items(session, row.id)) for row in rows]}


@router.post("/procurement/receipts")
def receive_order(
    body: ReceiptBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.receive_order(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.receipt_out(row, services.receipt_items(session, row.id)), "row_version": row.row_version}


@router.post("/procurement/receipts/items/{receipt_item_id}/observe-price")
def observe_price(
    receipt_item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.record_observed_price(session, principal, receipt_item_id, idempotency_key=idempotency_key)
    )
    return {"data": {"id": str(row.id), "unit_price": format(row.unit_price, "f"), "source": row.source}}


@router.get("/procurement/returns")
def list_returns(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [serialize.return_out(row) for row in _run(lambda: services.list_returns(session, principal))]}


@router.post("/procurement/returns")
def create_return(
    body: ReturnBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.return_to_supplier(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": serialize.return_out(row)}


@router.get("/inventory/traceability")
def inventory_trace(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    lot_id: UUID | None = None,
    production_order_id: UUID | None = None,
):
    return {
        "data": _run(lambda: services.traceability(session, principal, lot_id=lot_id, order_id=production_order_id))
    }
