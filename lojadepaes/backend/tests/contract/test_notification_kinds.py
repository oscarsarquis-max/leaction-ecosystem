"""Kinds que não saem do submit comum: identidade, resumo, proposta de data sem comando, aceite."""

import pytest
from app.core.config import get_settings
from app.domain.adaptations import client_respond_adaptation, evaluate_adaptation
from app.domain.customer_identity import start_resume, start_signup
from app.domain.date_requests import create_date_request
from app.domain.email_outbox import enqueue_date_request_email, enqueue_ops_attendance_summary
from app.domain.owner_alerts import notify_acceptance
from app.domain.web_push import enqueue_test_push
from app.models.customers import CustomerAccount
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import OrderItem
from app.schemas.suggestions import DateRequestCreateIn
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, send_submitted
from tests.test_schedule import _next_iso
from datetime import UTC, datetime, timedelta

pytestmark = pytest.mark.contract


def test_signup_enqueues_customer_verify_once_per_challenge(db: Session) -> None:
    # start_signup → customer_verify
    start_signup(db, get_settings(), "Ana Contrato", "ana.contrato.107@example.com", "390.533.447-05")
    rows = db.query(EmailOutbox).filter_by(kind="customer_verify").all()
    assert len(rows) == 1
    assert rows[0].status == "skipped"
    assert "390" not in rows[0].body


def test_date_request_available_has_template_but_no_command(db: Session) -> None:
    # enqueue_date_request_email aceita o kind; nenhum comando de apply_date_request_action o usa
    settings = get_settings()
    created = create_date_request(
        db,
        settings,
        DateRequestCreateIn(
            desired_date=_next_iso(3) + timedelta(days=14),
            customer_name="Lia Contrato",
            customer_email="lia.contrato@example.com",
            intended_quantity=1,
            idempotency_key="kind-available",
        ),
        client_host="127.0.0.1",
    )
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="date_request_available").count() == 0
    enqueue_date_request_email(db, settings, created, "date_request_available")
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="date_request_available").count() == 1
    enqueue_date_request_email(db, settings, created, "date_request_available")
    assert db.query(EmailOutbox).filter_by(kind="date_request_available").count() == 1


def test_attendance_summary_and_acceptance_admin_mail(db: Session) -> None:
    # enqueue_ops_attendance_summary e notify_acceptance
    settings = get_settings()
    order = send_confirmed(db, "kind-accept")
    request = DateRequest(
        desired_date=order.production_local_date,
        customer_name="Lia Contrato",
        customer_email="lia.contrato@example.com",
        intended_quantity=1,
        status="converted",
        idempotency_key="kind-accept-req",
        client_host="127.0.0.1",
    )
    db.add(request)
    db.flush()
    notify_acceptance(db, settings, order, request)
    db.flush()
    admin = db.query(EmailOutbox).filter_by(kind="acceptance_update_admin").one()
    assert admin.order_id == order.id
    assert admin.status == "skipped"
    notify_acceptance(db, settings, order, request)
    assert db.query(EmailOutbox).filter_by(kind="acceptance_update_admin").count() == 1
    enqueue_ops_attendance_summary(
        db,
        settings,
        {"date_requests_awaiting": 0, "orders_awaiting_evaluation": 0, "priority": []},
        dedupe_key="ops-summary:107",
    )
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="ops_attendance_summary").count() == 1
    enqueue_ops_attendance_summary(db, settings, {}, dedupe_key="ops-summary:107")
    assert db.query(EmailOutbox).filter_by(kind="ops_attendance_summary").count() == 1


def test_push_test_is_refused_without_vapid(db: Session) -> None:
    # enqueue_test_push; VAPID desligado na suíte
    from uuid import uuid4

    with pytest.raises(ValueError, match="indisponíveis"):
        enqueue_test_push(db, get_settings(), actor_ref="admin:contrato", device_id=uuid4())
    assert db.query(EmailOutbox).filter_by(kind="test").count() == 0


def test_adaptation_messages_and_verified_resume(db: Session) -> None:
    # evaluate_adaptation propose_alternative; client_respond decline; start_resume verificado
    order = send_submitted(db, "kind-adapt")
    item = db.query(OrderItem).filter_by(order_id=order.id).one()
    evaluate_adaptation(
        db,
        order.id,
        item.id,
        decision="propose_alternative",
        response="podemos sem girassol",
        actor_ref="admin:contrato",
    )
    db.flush()
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="adaptation_proposed").count() == 1
    client_respond_adaptation(db, order, item.id, "decline")
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="adaptation_customer_replied_admin").count() == 1
    start_signup(db, get_settings(), "Bia Contrato", "bia.contrato.107@example.com", "529.982.247-25")
    account = db.query(CustomerAccount).filter_by(email="bia.contrato.107@example.com").one()
    account.email_verified_at = datetime.now(UTC)
    from app.models.customers import CustomerChallenge

    challenge = db.query(CustomerChallenge).filter_by(email=account.email).one()
    challenge.created_at = datetime.now(UTC) - timedelta(minutes=10)
    db.flush()
    start_resume(db, get_settings(), "bia.contrato.107@example.com")
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="customer_resume").count() == 1
