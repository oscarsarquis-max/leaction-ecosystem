"""Efeitos observáveis de aviso. CRM não tem tabela local."""

import pytest
from app.core.config import get_settings
from app.domain.orders import confirm_order
from app.domain.payment_alerts import review_sync_alert
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsPushDelivery
from app.models.payments import PaymentRecord
from datetime import UTC, datetime, timedelta
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, send_submitted

pytestmark = pytest.mark.contract


def _kinds(db: Session, order) -> dict[str, int]:
    rows = db.query(EmailOutbox).filter_by(order_id=order.id).all()
    found: dict[str, int] = {}
    for row in rows:
        found[row.kind] = found.get(row.kind, 0) + 1
    return found


def test_auto_accept_notifies_customer_and_ops_once(db: Session) -> None:
    # submit_order autoaceite: order_accepted + order_auto_accepted_admin
    order = send_confirmed(db, "fx-auto")
    assert _kinds(db, order) == {"order_accepted": 1, "order_auto_accepted_admin": 1}
    confirm_order(db, order.id, actor_ref="admin:contrato")
    assert _kinds(db, order)["order_accepted"] == 1


def test_reviewed_submit_notifies_submission_until_accept(db: Session) -> None:
    # submit com adaptação; confirm_order acrescenta order_accepted
    order = send_submitted(db, "fx-review")
    assert _kinds(db, order) == {"order_submitted": 1, "order_submitted_admin": 1}
    confirm_order(db, order.id, actor_ref="admin:contrato")
    db.flush()
    found = _kinds(db, order)
    assert found["order_submitted"] == 1
    assert found["order_accepted"] == 1
    assert found["order_submitted_admin"] == 1


def test_persistent_sync_alert_enqueues_one_ops_mail(db: Session, monkeypatch) -> None:
    # review_sync_alert após 90 s; dedupe pela ocorrência
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-contract@example.test")
    get_settings.cache_clear()
    order = send_confirmed(db, "fx-alert")
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.sanitized_error = "Verificação do pagamento indisponível."
    now = datetime.now(UTC)
    review_sync_alert(db, get_settings(), order, record, now)
    db.flush()
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    review_sync_alert(db, get_settings(), order, record, now + timedelta(seconds=90))
    db.flush()
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_sync_alert").count() == 1
    review_sync_alert(db, get_settings(), order, record, now + timedelta(seconds=180))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    assert db.query(OpsPushDelivery).count() == 0


def test_crm_fact_does_not_change_the_order_when_the_secret_is_absent(db: Session) -> None:
    # emit_order_fact no autoaceite; sem segredo não há linha local
    order = send_confirmed(db, "fx-crm")
    assert order.status == "confirmed"
    assert order.production_started_at is None
