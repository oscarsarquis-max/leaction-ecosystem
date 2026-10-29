"""Etapa visível. A exclusão gerencial não troca o rótulo; tira o pedido da fila."""

import pytest
from app.domain.managerial_exclusion import exclude_subject, reverse_subject
from app.domain.order_board import classify_payment, managerial_board, visible_stage_for_order
from app.domain.orders import confirm_delivery, start_production, transition_order
from app.domain.payment_webhooks import apply_actionhub_observation
from app.core.config import get_settings
from app.models.enums import OrderStatus
from app.models.payments import PaymentRecord
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, send_submitted, variant

pytestmark = pytest.mark.contract


def _bucket(db: Session, order) -> str:
    records = list(db.query(PaymentRecord).filter_by(order_id=order.id))
    return classify_payment(order, records)


def _stage(db: Session, order) -> str:
    return visible_stage_for_order(order, _bucket(db, order))


def test_stage_table_from_real_commands(db: Session) -> None:
    # visible_stage_for_order: status + balde + delivery_confirmed_at
    # uma receita-base só: o teto diário de tipos não é o objeto deste caso
    bread = variant(db, "Pão contrato")
    submitted = send_submitted(db, "stage-open")
    assert _stage(db, submitted) == "open"
    assert _bucket(db, submitted) == "awaiting"

    accepted = send_confirmed(db, "stage-accepted", bread)
    assert _bucket(db, accepted) == "awaiting"
    assert _stage(db, accepted) == "accepted"

    paid = send_confirmed(db, "stage-paid", bread)
    record = db.query(PaymentRecord).filter_by(order_id=paid.id).one()
    record.external_reference = "hub-stage-paid"
    record.idempotency_key = record.idempotency_key or "pay-stage-paid"
    db.flush()
    settings = get_settings()
    apply_actionhub_observation(
        db,
        settings,
        {
            "app_id": settings.actionhub_app_id,
            "outbox_id": "stage-paid-event",
            "event_type": "PAYMENT_CONFIRMED",
            "payload": {
                "order_id": record.external_reference,
                "order_reference": paid.public_reference,
                "financial_status": "paid",
                "paid_amount_cents": paid.total_cents,
                "mp_status": "approved",
                "method": "card",
                "provider_approved_at": "2026-10-29T10:00:00-03:00",
            },
        },
    )
    db.flush()
    assert paid.status == "confirmed"
    assert _bucket(db, paid) == "paid"
    assert _stage(db, paid) == "paid"

    producing = send_confirmed(db, "stage-prod", bread)
    start_production(db, producing.id, actor_ref="admin:contrato", unpaid_exception=True)
    assert _stage(db, producing) == "in_production"

    ready = send_confirmed(db, "stage-ready", bread)
    start_production(db, ready.id, actor_ref="admin:contrato", unpaid_exception=True)
    transition_order(db, ready.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato")
    assert _stage(db, ready) == "ready_legacy"

    finalized = send_confirmed(db, "stage-final", bread)
    start_production(db, finalized.id, actor_ref="admin:contrato", unpaid_exception=True)
    transition_order(db, finalized.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato")
    transition_order(
        db, finalized.id, OrderStatus.COMPLETED.value, "entregue ou retirado", actor_ref="admin:contrato"
    )
    assert finalized.delivery_confirmed_at is None
    assert _stage(db, finalized) == "finalized"

    delivered = send_confirmed(db, "stage-delivered", bread)
    start_production(db, delivered.id, actor_ref="admin:contrato", unpaid_exception=True)
    confirm_delivery(db, delivered.id, actor_ref="admin:contrato")
    assert _stage(db, delivered) == "delivered"

    cancelled = send_confirmed(db, "stage-cancel", bread)
    from app.domain.orders import cancel_order

    cancel_order(db, cancelled.id, "desistiu", actor_ref="admin:contrato")
    assert _stage(db, cancelled) == "cancelled"


def test_exclusion_hides_the_order_and_keeps_the_stage(db: Session) -> None:
    order = send_confirmed(db, "stage-hidden")
    stage = _stage(db, order)
    status = order.status
    anchor = f"order:{order.id}"
    _board, keys = managerial_board(db, get_settings())
    assert anchor in keys["stage:accepted"]
    exclude_subject(db, "order", order.id, author_ref="admin:contrato", reason="ensaio")
    db.flush()
    assert order.status == status
    assert _stage(db, order) == stage
    board, keys = managerial_board(db, get_settings())
    assert anchor not in keys["stage:accepted"]
    assert board["excluded_tests"] >= 1
    reverse_subject(db, "order", order.id, author_ref="admin:contrato", reason="devolve à fila")
    db.flush()
    assert order.status == status
    assert _stage(db, order) == stage
