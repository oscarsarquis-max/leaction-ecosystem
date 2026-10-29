"""Pagamento não move o status operacional."""

import pytest
from app.core.config import get_settings
from app.domain.errors import ConfirmationError
from app.domain.orders import start_production
from app.domain.payment_webhooks import apply_actionhub_observation
from app.domain.storefront_orders import start_checkout
from app.models.email_outbox import EmailOutbox
from app.models.orders import OrderStatusHistory
from app.models.payments import PaymentRecord
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, send_submitted

pytestmark = pytest.mark.contract


def _fake_checkout(settings, prepared):
    del settings
    return {
        "external_reference": "hub-" + prepared["payment_request_id"][:8],
        "expected_cents": prepared["expected_cents"],
        "reused": False,
        "checkout_url": None,
        "hub_result": None,
    }


def test_checkout_is_refused_before_accept(db: Session) -> None:
    # start_checkout em submitted
    order = send_submitted(db, "pay-before-accept")
    with pytest.raises(ConfirmationError, match="depois do aceite"):
        start_checkout(db, get_settings(), order, "card")
    assert order.status == "submitted"


def test_checkout_after_accept_and_repeated_webhook_do_not_move_status(db: Session, monkeypatch) -> None:
    # recover_or_create_checkout falso; apply_actionhub_observation
    monkeypatch.setattr("app.domain.storefront_orders.recover_or_create_checkout", _fake_checkout)
    order = send_confirmed(db, "pay-axis")
    status_before = order.status
    history_before = db.query(OrderStatusHistory).filter_by(order_id=order.id).count()
    start_checkout(db, get_settings(), order, "pix")
    db.flush()
    assert order.status == status_before
    assert db.query(OrderStatusHistory).filter_by(order_id=order.id).count() == history_before
    record = db.query(PaymentRecord).filter_by(order_id=order.id, financial_status="pending").one()
    assert record.external_reference
    settings = get_settings()
    event = {
        "app_id": settings.actionhub_app_id,
        "outbox_id": "pay-axis-once",
        "event_type": "PAYMENT_CONFIRMED",
        "payload": {
            "order_id": record.external_reference,
            "order_reference": order.public_reference,
            "financial_status": "paid",
            "paid_amount_cents": order.total_cents,
            "mp_payment_id": "mp-axis-1",
            "mp_status": "approved",
            "method": "pix",
            "provider_approved_at": "2026-10-29T10:15:00-03:00",
        },
    }
    first = apply_actionhub_observation(db, settings, event)
    db.flush()
    assert first["process_status"] == "applied"
    assert order.status == "confirmed"
    assert order.production_started_at is None
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1
    second = apply_actionhub_observation(db, settings, event)
    assert second["duplicate"] is True
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1
    start_production(db, order.id, actor_ref="admin:contrato")
    assert order.status == "in_production"


def test_method_replace_cancels_the_open_attempt(db: Session, monkeypatch) -> None:
    # start_checkout replace=True
    monkeypatch.setattr("app.domain.storefront_orders.recover_or_create_checkout", _fake_checkout)
    monkeypatch.setattr("app.domain.storefront_orders.cancel_amount_checkout", lambda *a, **k: None)
    order = send_confirmed(db, "pay-replace")
    start_checkout(db, get_settings(), order, "pix")
    start_checkout(db, get_settings(), order, "card", replace=True)
    db.flush()
    rows = db.query(PaymentRecord).filter_by(order_id=order.id).all()
    assert any(row.financial_status == "cancelled" and row.method == "pix" for row in rows)
    assert any(row.financial_status == "pending" and row.method == "card" for row in rows)
    assert order.status == "confirmed"
