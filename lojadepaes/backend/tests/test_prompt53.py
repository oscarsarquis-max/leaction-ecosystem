from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import get_settings
from app.domain.admin_orders import list_orders
from app.domain.email_outbox import enqueue_admin_order_email
from app.domain.errors import ConfirmationError
from app.domain.orders import confirm_order
from app.domain.storefront_orders import start_checkout, submit_order
from app.models.email_outbox import EmailOutbox
from app.models.enums import OrderStatus
from app.schemas.admin import OrderListQuery
from sqlalchemy.orm import Session
from tests.test_custom_loaf import _catalog, _payload


def test_submit_requires_name_and_email(db: Session) -> None:
    catalog = _catalog(db)
    with pytest.raises(ConfirmationError, match="nome"):
        submit_order(db, get_settings(), _payload(catalog, customer_name=""))
    with pytest.raises(ConfirmationError):
        submit_order(db, get_settings(), _payload(catalog, customer_email="sem-arroba"))


def test_custom_submit_enqueues_customer_and_skipped_admin(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    get_settings.cache_clear()
    catalog = _catalog(db)
    payload = _payload(catalog, quoted_cents=14000)
    order, token = submit_order(db, get_settings(), payload)
    again, token_again = submit_order(db, get_settings(), payload)
    assert order.id == again.id
    assert token_again == ""
    assert token
    rows = db.query(EmailOutbox).filter_by(order_id=order.id).all()
    kinds = {row.kind: row for row in rows}
    assert kinds["order_submitted"].to_address == "ana@example.com"
    assert "ainda vai avaliar" in kinds["order_submitted"].body
    assert "reservada" not in kinds["order_submitted"].body
    assert kinds["order_submitted_admin"].status == "skipped"
    assert "destinatário administrativo" in (kinds["order_submitted_admin"].last_error or "")
    assert kinds["order_submitted_admin"].status != "sent"
    listing = list_orders(db, get_settings(), OrderListQuery())
    match = next(item for item in listing.items if item.id == order.id)
    assert match.has_custom is True
    assert match.custom_awaiting is True
    get_settings.cache_clear()


def test_admin_notice_pending_when_ops_configured(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "padaria@example.test")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    get_settings.cache_clear()
    catalog = _catalog(db)
    order, _token = submit_order(db, get_settings(), _payload(catalog))
    row = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_submitted_admin").one()
    assert row.status == "pending"
    assert row.to_address == "padaria@example.test"
    assert order.public_reference in row.subject
    assert str(order.id) in row.body
    assert "ana@" not in row.body
    assert "pepperoni" not in row.body
    again = enqueue_admin_order_email(db, get_settings(), order)
    assert again.id == row.id
    get_settings.cache_clear()


def test_accept_sends_payment_mail_and_opens_checkout_once(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    get_settings.cache_clear()
    catalog = _catalog(db)
    order, _token = submit_order(db, get_settings(), _payload(catalog, quoted_cents=14000, item={"quantity": 2}))
    with pytest.raises(ConfirmationError, match="aceite"):
        start_checkout(db, get_settings(), order, "pix")
    confirmed = confirm_order(db, order.id, actor_ref="padaria")
    assert confirmed.status == OrderStatus.CONFIRMED.value
    assert confirmed.holds_capacity is True
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert mail.subject.startswith("Seu pão foi aceito")
    assert "prossiga para o pagamento" in mail.body.lower() or "Prossiga" in mail.body
    again = confirm_order(db, order.id, actor_ref="padaria")
    assert again.id == confirmed.id
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1
    get_settings.cache_clear()


def test_old_custom_request_stays_in_queue(db: Session) -> None:
    catalog = _catalog(db)
    order, _token = submit_order(db, get_settings(), _payload(catalog))
    order.created_at = datetime.now(UTC) - timedelta(hours=30)
    db.flush()
    listing = list_orders(db, get_settings(), OrderListQuery())
    assert any(item.id == order.id for item in listing.items)


def test_activation_recipient_is_not_ops_default() -> None:
    settings = get_settings()
    assert settings.mail_ops_to == ""
    assert "oscar@" not in (settings.mail_ops_to or "").lower()


def test_authorized_ops_to_routes_without_promoting_skipped(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM_NAME", "Loja de Pães")
    get_settings.cache_clear()
    catalog = _catalog(db)
    skipped_order, _token = submit_order(db, get_settings(), _payload(catalog))
    skipped = db.query(EmailOutbox).filter_by(order_id=skipped_order.id, kind="order_submitted_admin").one()
    assert skipped.status == "skipped"

    captured: list[dict] = []

    def fake_send(settings, *, to_address, subject, body):
        from app.domain.ses_mailer import MailSendResult

        captured.append({"to": to_address, "from": settings.mail_from, "subject": subject, "body": body})
        return MailSendResult(accepted=True, message_id="ses-captured-53a", error=None)

    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "oscar@oscarsarquis.com.br")
    get_settings.cache_clear()
    from app.domain.email_outbox import process_due_outbox

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", fake_send)
    process_due_outbox(db, get_settings())
    db.refresh(skipped)
    assert skipped.status == "skipped"
    assert skipped.to_address == "ops-unconfigured"
    assert all(item["to"] != "oscar@oscarsarquis.com.br" for item in captured)

    fresh, _again = submit_order(db, get_settings(), _payload(catalog, idempotency_key="ops-53a-fresh"))
    pending = db.query(EmailOutbox).filter_by(order_id=fresh.id, kind="order_submitted_admin").one()
    assert pending.status == "pending"
    assert pending.to_address == "oscar@oscarsarquis.com.br"
    assert "ana@" not in pending.body
    assert "pepperoni" not in pending.body
    process_due_outbox(db, get_settings())
    db.refresh(pending)
    assert pending.status == "sent"
    ops = [item for item in captured if item["to"] == "oscar@oscarsarquis.com.br"]
    assert len(ops) == 1
    assert ops[0]["from"] == "loja@lojadepaes.com.br"
    assert enqueue_admin_order_email(db, get_settings(), fresh).id == pending.id
    get_settings.cache_clear()
