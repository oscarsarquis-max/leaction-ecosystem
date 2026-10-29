from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult, HubUnavailableError
from app.domain.errors import ConfirmationError
from app.domain.payment_webhooks import apply_actionhub_observation
from app.domain.payment_worker import process_payment_checks
from app.domain.payments import order_is_financially_settled
from app.domain.storefront_orders import (
    public_order_view,
    reconcile_checkout,
    refresh_open_checkout,
    start_checkout,
    submit_order,
)
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from sqlalchemy import select
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_storefront import _next_wednesday, _product


def make_order(db, *, state="confirmed", total=7000):
    order = Order(
        public_reference="LP" + uuid4().hex[:10].upper(),
        status=state,
        currency="BRL",
        subtotal_cents=total,
        total_cents=total,
        fulfillment_modality="delivery",
        customer_name="Teste",
        customer_email="teste@example.com",
    )
    db.add(order)
    db.flush()
    record = PaymentRecord(
        order_id=order.id,
        expected_cents=total,
        currency="BRL",
        method="card",
        financial_status="pending",
        external_reference=str(uuid4()),
        idempotency_key=str(uuid4()),
    )
    db.add(record)
    db.flush()
    return order, record


def approved(order, record):
    return HubCheckoutResult(
        order_id=record.external_reference,
        status="PAID",
        checkout_url=None,
        amount_cents=record.expected_cents,
        reused=True,
        method="card",
        mp_payment_id="test-" + record.id.hex,
        currency="BRL",
        order_reference=order.public_reference,
        paid_amount_cents=record.expected_cents,
        refunded_amount_cents=0,
        provider_status="approved",
        provider_approved_at="2026-10-27T17:10:26-03:00",
        provider_observed_at="2026-10-27T17:10:27-03:00",
    )


@pytest.mark.parametrize("state", ["submitted", "confirmed", "in_production", "ready", "completed"])
def test_recovery_independent_of_operational_state(db, monkeypatch, state):
    order, record = make_order(db, state=state)
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order, record),
    )
    refresh_open_checkout(db, get_settings(), order.id)
    assert record.financial_status == "paid"
    assert record.method == "card"
    assert record.mp_payment_id.startswith("test-")
    assert record.confirmed_at.hour == 17
    assert order.status == state
    assert order.delivery_confirmed_at is None
    assert order_is_financially_settled(order, [record])
    reconcile_checkout(db, get_settings(), order)
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1
    assert db.query(PaymentIntegrationEvent).count() == 1


def test_two_orders_same_value_do_not_exchange_payment(db, monkeypatch):
    order1, record1 = make_order(db)
    order2, record2 = make_order(db)
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order2, record2),
    )
    refresh_open_checkout(db, get_settings(), order1.id)
    assert record1.financial_status == "pending"
    assert "diverge" in record1.sanitized_error
    assert record2.financial_status == "pending"
    assert db.query(EmailOutbox).count() == 0


@pytest.mark.parametrize(
    "change",
    [
        {"paid_amount_cents": None},
        {"paid_amount_cents": 6999},
        {"provider_status": "authorized"},
        {"currency": "USD"},
    ],
)
def test_unproven_payment_does_not_confirm(db, monkeypatch, change):
    order, record = make_order(db)
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: replace(approved(order, record), **change),
    )
    refresh_open_checkout(db, get_settings(), order.id)
    assert record.financial_status == "pending"
    assert record.amount_paid_cents is None
    assert record.sanitized_error
    assert db.query(EmailOutbox).count() == 0


def test_pending_attempt_cannot_hide_an_independent_paid_attempt(db):
    order, card = make_order(db)
    card.financial_status = "paid"
    card.amount_paid_cents = 7000
    pix = PaymentRecord(
        order_id=order.id,
        currency="BRL",
        expected_cents=7000,
        financial_status="pending",
        method="pix",
    )
    db.add(pix)
    db.flush()
    assert order_is_financially_settled(order, [card, pix])
    card.financial_status = "partially_refunded"
    card.amount_refunded_cents = 100
    assert not order_is_financially_settled(order, [card, pix])


def test_worker_recovers_after_failure_and_restart_without_browser(db, monkeypatch):
    order, record = make_order(db, state="in_production")
    # Production DB triggers own updated_at; advance the scheduler's clock instead.
    now = datetime.now(UTC) + timedelta(minutes=2)
    db.commit()

    def unavailable(*a, **k):
        raise HubUnavailableError("offline")

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", unavailable)
    assert process_payment_checks(db, get_settings(), now=now)["failures"] == 1
    db.commit()
    db.expire_all()
    assert record.financial_status == "pending"
    assert record.sanitized_error
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order, record),
    )
    assert (
        process_payment_checks(db, get_settings(), now=now + timedelta(seconds=31))["checked"] == 1
    )
    db.commit()
    assert record.financial_status == "paid"
    assert record.sanitized_error is None
    assert order.status == "in_production"
    assert db.query(EmailOutbox).filter_by(kind="payment_approved").count() == 1


def test_standard_under_review_cannot_open_checkout(db, monkeypatch):
    order, record = make_order(db, state="submitted")
    monkeypatch.setattr("app.domain.storefront_orders._order_contains_custom", lambda *a: False)
    assert public_order_view(db, order)["payment_available"] is False
    with pytest.raises(ConfirmationError, match="depois do aceite"):
        start_checkout(db, get_settings(), order, "pix")
    assert record.financial_status == "pending"


def test_cart_multiple_items_one_order_one_total_one_payment(db, monkeypatch):
    a, b = _product(db), _product(db)
    payload = {
        "requested_date": _next_wednesday(),
        "items": [
            {"variant_id": str(a.id), "quantity": 1},
            {"variant_id": str(b.id), "quantity": 2},
        ],
        "quoted_cents": 7470,
        "customer_name": "Teste Carrinho",
        "customer_email": "cart@example.com",
        "idempotency_key": "105a-cart-one-order",
        **NEW_ORDER_ADDRESS,
    }
    first, _ = submit_order(db, get_settings(), payload)
    second, _ = submit_order(db, get_settings(), payload)
    assert first.id == second.id
    assert first.status == "confirmed"
    assert first.total_cents == 7470
    assert db.query(Order).count() == 1
    items = list(db.scalars(select(OrderItem).where(OrderItem.order_id == first.id)))
    assert len(items) == 2 and sum(item.quantity for item in items) == 3
    record = db.query(PaymentRecord).filter_by(order_id=first.id).one()
    record.idempotency_key = str(uuid4())
    record.external_reference = str(uuid4())
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(first, record),
    )
    reconcile_checkout(db, get_settings(), first)
    assert record.amount_paid_cents == 7470
    assert first.status == "confirmed"
    assert db.query(PaymentRecord).count() == 1


def test_webhook_unknown_charge_does_not_fall_back_to_latest_attempt(db):
    order, record = make_order(db)
    settings = get_settings()
    result = apply_actionhub_observation(
        db,
        settings,
        {
            "app_id": settings.actionhub_app_id,
            "outbox_id": "unknown-charge",
            "payload": {
                "order_id": str(uuid4()),
                "order_reference": order.public_reference,
                "financial_status": "paid",
                "paid_amount_cents": 7000,
            },
        },
    )
    assert result["process_status"] == "ignored"
    assert record.financial_status == "pending"
