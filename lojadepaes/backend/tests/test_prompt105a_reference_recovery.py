"""Recuperação do identificador do provedor sem repetir efeitos comerciais."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.domain.actionhub_client import HubUnavailableError
from app.domain.payment_webhooks import apply_actionhub_observation
from app.domain.payment_worker import process_payment_checks
from app.domain.storefront_orders import reconcile_payment_record
from app.models.email_outbox import EmailOutbox
from app.models.house_fidelity import HouseFidelityEvent
from app.models.managerial import OpsOwnerAlert, OpsPushDelivery
from app.models.orders import OrderStatusHistory
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from sqlalchemy import text
from tests.test_prompt105a_followup import _device, _enable_ops
from tests.test_prompt105a_payments import approved, make_order

APPROVED_AT = "2026-09-27T13:08:08+00:00"
VERIFYING = "Pagamento em verificação: falta confirmação do valor recebido. Não refaça o pagamento."


def _paid_without_id(db, *, state="confirmed"):
    order, record = make_order(db, state=state)
    record.financial_status = "paid"
    record.amount_paid_cents = 7000
    record.method = "card"
    record.mp_payment_id = None
    record.external_status_raw = None
    record.confirmed_at = datetime(2026, 9, 27, 13, 8, 8, tzinfo=UTC)
    record.sanitized_error = VERIFYING
    record.amount_refunded_cents = None
    db.flush()
    return order, record


def _event(order, record, *, outbox_id, provider_id="180134636613"):
    return {
        "app_id": get_settings().actionhub_app_id,
        "outbox_id": outbox_id,
        "event_type": "PAYMENT_CONFIRMED",
        "payload": {
            "order_id": record.external_reference,
            "order_reference": order.public_reference,
            "financial_status": "paid",
            "paid_amount_cents": 7000,
            "amount_refunded_cents": 0,
            "mp_payment_id": provider_id,
            "mp_status": "approved",
            "method": "card",
            "provider_approved_at": APPROVED_AT,
        },
    }


def _counts(db, order):
    return {
        "paid_mail": db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count(),
        "alert_mail": db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_sync_alert").count(),
        "push": db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").count(),
        "fidelity": db.query(HouseFidelityEvent).count(),
        "history": db.query(OrderStatusHistory).filter_by(order_id=order.id).count(),
        "payments": db.query(PaymentRecord).filter_by(order_id=order.id).count(),
    }


def test_r06_paid_record_gains_provider_metadata_without_new_effects(db):
    order, record = _paid_without_id(db)
    settings = get_settings()
    db.add(EmailOutbox(
        order_id=order.id, kind="payment_approved", to_address="cliente@example.com",
        subject="Pagamento recebido", body="já enviado", status="sent", attempts=1,
        dedupe_key=f"{order.id}:payment_approved",
    ))
    db.flush()
    before = _counts(db, order)
    confirmed_at = record.confirmed_at
    result = apply_actionhub_observation(db, settings, _event(order, record, outbox_id="enrich-paid"))
    assert result["process_status"] == "applied"
    assert result["duplicate"] is False
    assert record.mp_payment_id == "180134636613"
    assert record.external_status_raw == "approved"
    assert record.method == "card"
    assert record.amount_paid_cents == 7000
    assert record.amount_refunded_cents == 0
    assert record.confirmed_at == confirmed_at
    assert record.sanitized_error is None
    assert record.last_synced_at is not None
    event = db.query(PaymentIntegrationEvent).filter_by(external_event_id="enrich-paid").one()
    assert event.provider_occurred_at == datetime(2026, 9, 27, 13, 8, 8, tzinfo=UTC)
    assert order.status == "confirmed"
    assert order.production_started_at is None
    assert _counts(db, order) == before


def test_r07_webhook_and_lookup_keep_a_single_receipt(db, monkeypatch):
    settings = get_settings()
    webhook_first, webhook_record = _paid_without_id(db)
    lookup_first, lookup_record = _paid_without_id(db)
    for order in (webhook_first, lookup_first):
        db.add(EmailOutbox(
            order_id=order.id, kind="payment_approved", to_address="cliente@example.com",
            subject="Pagamento recebido", body="já enviado", status="sent", attempts=1,
            dedupe_key=f"{order.id}:payment_approved",
        ))
    db.flush()
    before_webhook = _counts(db, webhook_first)
    before_lookup = _counts(db, lookup_first)

    def same_confirmation(order, record):
        found = approved(order, record)
        return replace(found, mp_payment_id=record.mp_payment_id or "180134636613", provider_approved_at=APPROVED_AT)

    apply_actionhub_observation(db, settings, _event(webhook_first, webhook_record, outbox_id="wh-first"))
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: same_confirmation(webhook_first, webhook_record),
    )
    reconcile_payment_record(db, settings, webhook_first, webhook_record)
    apply_actionhub_observation(db, settings, _event(webhook_first, webhook_record, outbox_id="wh-first"))

    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: same_confirmation(lookup_first, lookup_record),
    )
    reconcile_payment_record(db, settings, lookup_first, lookup_record)
    apply_actionhub_observation(
        db, settings, _event(lookup_first, lookup_record, outbox_id="lookup-then-wh", provider_id=lookup_record.mp_payment_id)
    )
    apply_actionhub_observation(
        db, settings, _event(lookup_first, lookup_record, outbox_id="lookup-then-wh", provider_id=lookup_record.mp_payment_id)
    )

    assert webhook_record.amount_paid_cents == 7000
    assert lookup_record.amount_paid_cents == 7000
    assert webhook_record.mp_payment_id
    assert lookup_record.mp_payment_id == webhook_record.mp_payment_id or lookup_record.mp_payment_id
    assert webhook_record.external_status_raw == "approved"
    assert _counts(db, webhook_first)["paid_mail"] == before_webhook["paid_mail"]
    assert _counts(db, lookup_first)["paid_mail"] == before_lookup["paid_mail"]
    assert _counts(db, webhook_first)["fidelity"] == before_webhook["fidelity"]
    assert db.query(HouseFidelityEvent).count() == 0
    assert webhook_first.status == "confirmed"
    assert lookup_first.status == "confirmed"


def test_r07_repeated_confirmation_fills_metadata_the_first_apply_left_empty(db):
    order, record = _paid_without_id(db)
    record.mp_payment_id = "180134636613"
    record.sanitized_error = None
    confirmed_at = record.confirmed_at
    recorded = PaymentIntegrationEvent(
        provider="actionhub",
        external_event_id="already-applied",
        external_type="PAYMENT_RECONCILED",
        payment_record_id=record.id,
        received_at=datetime(2026, 10, 28, 17, 46, 49, tzinfo=UTC),
        process_status="applied",
    )
    db.add(recorded)
    db.add(EmailOutbox(
        order_id=order.id, kind="payment_approved", to_address="cliente@example.com",
        subject="Pagamento recebido", body="já enviado", status="sent", attempts=1,
        dedupe_key=f"{order.id}:payment_approved",
    ))
    db.flush()
    before = _counts(db, order)
    settings = get_settings()
    result = apply_actionhub_observation(db, settings, _event(order, record, outbox_id="already-applied"))
    assert result == {"duplicate": True, "process_status": "applied"}
    assert record.external_status_raw == "approved"
    assert record.amount_refunded_cents == 0
    assert record.amount_paid_cents == 7000
    assert record.mp_payment_id == "180134636613"
    assert record.method == "card"
    assert record.confirmed_at == confirmed_at
    assert recorded.provider_occurred_at == datetime(2026, 9, 27, 13, 8, 8, tzinfo=UTC)
    assert db.query(PaymentIntegrationEvent).filter_by(external_event_id="already-applied").count() == 1
    assert _counts(db, order) == before

    pix_attempt = dict(_event(order, record, outbox_id="already-applied"))
    pix_attempt["payload"] = {**pix_attempt["payload"], "method": "pix", "mp_status": ""}
    apply_actionhub_observation(db, settings, pix_attempt)
    assert record.method == "card"
    assert record.external_status_raw == "approved"
    assert _counts(db, order) == before

    record.external_status_raw = None
    conflict = PaymentIntegrationEvent(
        provider="actionhub",
        external_event_id="conflict-applied",
        external_type="PAYMENT_RECONCILED",
        payment_record_id=record.id,
        received_at=datetime(2026, 10, 28, 17, 46, 50, tzinfo=UTC),
        process_status="applied",
    )
    db.add(conflict)
    db.flush()
    apply_actionhub_observation(
        db, settings, _event(order, record, outbox_id="conflict-applied", provider_id="999")
    )
    assert record.mp_payment_id == "180134636613"
    assert record.external_status_raw is None
    assert conflict.provider_occurred_at is None
    assert record.amount_paid_cents == 7000


def test_r08_cancelled_order_keeps_the_card_and_the_cancelled_pix(db):
    order, card = _paid_without_id(db, state="cancelled")
    order.holds_capacity = False
    order.production_started_at = None
    pix = PaymentRecord(
        order_id=order.id,
        provider="actionhub",
        expected_cents=7000,
        currency="BRL",
        method="pix",
        financial_status="cancelled",
        external_status_raw="cancelled",
        external_reference=str(uuid4()),
        idempotency_key=str(uuid4()),
    )
    db.add(pix)
    db.flush()
    apply_actionhub_observation(db, get_settings(), _event(order, card, outbox_id="cancelled-card"))
    db.refresh(pix)
    assert order.status == "cancelled"
    assert order.holds_capacity is False
    assert order.production_started_at is None
    assert card.financial_status == "paid"
    assert card.method == "card"
    assert card.mp_payment_id == "180134636613"
    assert pix.financial_status == "cancelled"
    assert pix.method == "pix"
    assert pix.mp_payment_id is None
    assert db.query(OrderStatusHistory).count() == 0
    assert db.query(EmailOutbox).filter_by(kind="payment_approved").count() == 0


def _hold_paid_clock(db, record_id, opened: datetime) -> None:
    """The updated_at trigger would replace the test clock. Paid selection is five minutes."""
    db.execute(text("ALTER TABLE payment_records DISABLE TRIGGER trg_payment_records_updated_at"))
    db.execute(
        text("UPDATE payment_records SET updated_at = :ts WHERE id = :id"),
        {"ts": opened - timedelta(minutes=10), "id": record_id},
    )
    db.commit()


def _release_paid_clock(db) -> None:
    db.execute(text("ALTER TABLE payment_records ENABLE TRIGGER trg_payment_records_updated_at"))
    db.commit()


@pytest.fixture
def restore_paid_clock(db):
    yield
    _release_paid_clock(db)


def test_r09_paid_cadence_closes_one_alert_and_the_next_check_stays_closed(db, monkeypatch, restore_paid_clock):
    _enable_ops(monkeypatch)
    _device(db)
    order, record = _paid_without_id(db)
    db.commit()
    opened = datetime.now(UTC)
    _hold_paid_clock(db, record.id, opened)

    def incomplete(*args, **kwargs):
        return replace(
            approved(order, record),
            status="PAID",
            provider_status="pending",
            paid_amount_cents=None,
            mp_payment_id=None,
        )

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", incomplete)
    process_payment_checks(db, get_settings(), now=opened)
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    process_payment_checks(db, get_settings(), now=opened + timedelta(seconds=90))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=5))
    mail = db.query(EmailOutbox).filter_by(kind="payment_sync_alert").one()
    assert db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").count() == 1

    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: approved(order, record),
    )
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=10))
    db.refresh(record)
    assert record.mp_payment_id == "test-" + record.id.hex
    assert record.sanitized_error is None
    assert record.financial_status == "paid"
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    assert db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").count() == 1
    closed = db.query(OpsOwnerAlert).filter_by(event_key=mail.dedupe_key).all()
    assert closed and all("encerrada" in row.summary for row in closed)
    watch = db.query(PaymentIntegrationEvent).filter_by(external_event_id=mail.dedupe_key).one()
    assert watch.process_status == "applied"

    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=16))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    assert db.query(PaymentIntegrationEvent).filter_by(external_type="SYNC_WATCH", process_status="received").count() == 0
    assert record.sanitized_error is None


def test_r10_a_later_distinct_failure_is_still_detected(db, monkeypatch, restore_paid_clock):
    _enable_ops(monkeypatch)
    _device(db)
    order, record = _paid_without_id(db)
    db.commit()
    opened = datetime.now(UTC)
    _hold_paid_clock(db, record.id, opened)
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: (_ for _ in ()).throw(HubUnavailableError("offline")),
    )
    process_payment_checks(db, get_settings(), now=opened)
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=5))
    first = db.query(EmailOutbox).filter_by(kind="payment_sync_alert").one()
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=10))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1

    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: approved(order, record),
    )
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=15))
    assert record.sanitized_error is None
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1

    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: (_ for _ in ()).throw(HubUnavailableError("offline de novo")),
    )
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=20))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    process_payment_checks(db, get_settings(), now=opened + timedelta(minutes=25))
    mails = db.query(EmailOutbox).filter_by(kind="payment_sync_alert").order_by(EmailOutbox.created_at).all()
    assert len(mails) == 2
    assert mails[0].dedupe_key == first.dedupe_key
    assert mails[1].dedupe_key != first.dedupe_key
    assert db.query(OpsOwnerAlert).filter_by(event_key=first.dedupe_key).filter(
        OpsOwnerAlert.summary.contains("encerrada")
    ).count() >= 1
