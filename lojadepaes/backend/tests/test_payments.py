from datetime import UTC, datetime

import pytest
from app.domain.orders import confirm_order
from app.domain.payments import order_is_financially_settled
from app.models.enums import FinancialStatus, PaymentProvider
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.db_fixtures import draft_order, priced_catalog


def test_external_reference_unique_per_provider(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            external_reference="ext-1",
            expected_cents=1400,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
        )
    )
    db.flush()
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            external_reference="ext-1",
            expected_cents=1400,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_event_dedup_and_unknown_amounts(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    record = PaymentRecord(
        order_id=order.id,
        provider=PaymentProvider.ACTIONHUB.value,
        expected_cents=1400,
        currency="BRL",
        financial_status=FinancialStatus.PAID.value,
        amount_paid_cents=None,
    )
    db.add(record)
    db.flush()
    assert order_is_financially_settled(order, [record]) is False
    record.amount_paid_cents = 1400
    assert order_is_financially_settled(order, [record]) is True
    event = PaymentIntegrationEvent(
        provider=PaymentProvider.ACTIONHUB.value,
        external_event_id="evt-1",
        payment_record_id=record.id,
        received_at=datetime.now(UTC),
        process_status="received",
    )
    db.add(event)
    db.flush()
    db.add(
        PaymentIntegrationEvent(
            provider=PaymentProvider.ACTIONHUB.value,
            external_event_id="evt-1",
            received_at=datetime.now(UTC),
            process_status="received",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_refund_cannot_exceed_paid(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=1400,
            currency="BRL",
            financial_status=FinancialStatus.PAID.value,
            amount_paid_cents=100,
            amount_refunded_cents=200,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_operational_status_is_not_financial(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    assert order.status == "confirmed"
    assert order_is_financially_settled(order, []) is False
