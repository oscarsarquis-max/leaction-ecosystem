"""Comandos operacionais não abrem e-mail nem push. Congela o silêncio de hoje."""

import pytest
from app.core.config import get_settings
from app.domain.orders import confirm_delivery, start_production, transition_order
from app.domain.payment_webhooks import apply_actionhub_observation
from app.domain.storefront_orders import start_checkout
from app.models.email_outbox import EmailOutbox
from app.models.enums import OrderStatus
from app.models.managerial import OpsPushDelivery
from app.models.orders import Order
from app.models.payments import PaymentRecord
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, variant

pytestmark = pytest.mark.contract


def _counts(db: Session, order: Order) -> tuple[int, int]:
    emails = db.query(EmailOutbox).filter_by(order_id=order.id).count()
    pushes = (
        db.query(OpsPushDelivery).filter(OpsPushDelivery.path == f"/admin/pedidos/{order.id}").count()
    )
    return emails, pushes


def _unchanged(db: Session, order: Order, before: tuple[int, int]) -> None:
    assert _counts(db, order) == before


def _fake_checkout(_settings, prepared):
    return {
        "external_reference": "hub-" + prepared["payment_request_id"][:8],
        "expected_cents": prepared["expected_cents"],
        "reused": False,
        "checkout_url": None,
        "hub_result": None,
    }


def test_production_ready_complete_delivery_and_cancel_stay_silent(db: Session, monkeypatch) -> None:
    # start_production, mark ready, complete, confirm_delivery e cancel não chamam a caixa de saída.
    monkeypatch.setattr("app.domain.storefront_orders.recover_or_create_checkout", _fake_checkout)
    bread = variant(db, "Pão silêncio")

    paid = send_confirmed(db, "silence-paid", bread)
    start_checkout(db, get_settings(), paid, "pix")
    record = db.query(PaymentRecord).filter_by(order_id=paid.id, financial_status="pending").one()
    settings = get_settings()
    apply_actionhub_observation(
        db,
        settings,
        {
            "app_id": settings.actionhub_app_id,
            "outbox_id": "silence-paid-once",
            "event_type": "PAYMENT_CONFIRMED",
            "payload": {
                "order_id": record.external_reference,
                "order_reference": paid.public_reference,
                "financial_status": "paid",
                "paid_amount_cents": paid.total_cents,
                "mp_payment_id": "mp-silence-1",
                "mp_status": "approved",
                "method": "pix",
            },
        },
    )
    before = _counts(db, paid)
    start_production(db, paid.id, actor_ref="admin:contrato")
    assert paid.status == "in_production"
    _unchanged(db, paid, before)

    exception = send_confirmed(db, "silence-exception", bread)
    before = _counts(db, exception)
    start_production(db, exception.id, actor_ref="admin:contrato", unpaid_exception=True)
    assert exception.status == "in_production"
    _unchanged(db, exception, before)

    ready = send_confirmed(db, "silence-ready", bread)
    start_production(db, ready.id, actor_ref="admin:contrato", unpaid_exception=True)
    before = _counts(db, ready)
    transition_order(
        db, ready.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato"
    )
    assert ready.status == "ready"
    _unchanged(db, ready, before)

    finished = send_confirmed(db, "silence-complete", bread)
    start_production(db, finished.id, actor_ref="admin:contrato", unpaid_exception=True)
    transition_order(
        db, finished.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato"
    )
    before = _counts(db, finished)
    transition_order(
        db, finished.id, OrderStatus.COMPLETED.value, "entregue ou retirado", actor_ref="admin:contrato"
    )
    assert finished.status == "completed"
    assert finished.delivery_confirmed_at is None
    _unchanged(db, finished, before)

    delivered = send_confirmed(db, "silence-delivery", bread)
    start_production(db, delivered.id, actor_ref="admin:contrato", unpaid_exception=True)
    before = _counts(db, delivered)
    confirm_delivery(db, delivered.id, actor_ref="admin:contrato")
    assert delivered.delivery_confirmed_at is not None
    _unchanged(db, delivered, before)

    cancelled = send_confirmed(db, "silence-cancel", bread)
    before = _counts(db, cancelled)
    transition_order(db, cancelled.id, OrderStatus.CANCELLED.value, "desistiu", actor_ref="admin:contrato")
    assert cancelled.status == "cancelled"
    _unchanged(db, cancelled, before)
