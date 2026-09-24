from datetime import date
from uuid import uuid4

from app.core.config import get_settings
from app.domain.email_outbox import (
    TEMPLATES,
    enqueue_order_email,
    process_due_outbox,
)
from app.domain.ses_mailer import (
    formatted_mail_from,
    sanitize_mail_error,
    send_outbox_email,
)
from app.models.orders import Order
from sqlalchemy.orm import Session


def _order(db: Session) -> Order:
    order = Order(
        public_reference=f"LP{uuid4().hex[:10].upper()}",
        status="submitted",
        fulfillment_modality="pickup",
        customer_name="Cliente Teste",
        customer_email="loja-teste-outbox@example.com",
        currency="BRL",
        subtotal_cents=2490,
        delivery_fee_cents=0,
        discount_cents=0,
        total_cents=2490,
        holds_capacity=False,
        production_local_date=date(2026, 9, 23),
    )
    db.add(order)
    db.flush()
    return order


def test_enqueue_skips_without_sender(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.delenv("LOJADEPAES_MAIL_FROM", raising=False)
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    get_settings.cache_clear()
    order = _order(db)
    row = enqueue_order_email(db, get_settings(), order, "order_submitted")
    assert row.status == "skipped"
    assert "não enviada" in (row.last_error or "")
    assert "Data pedida" in row.body
    assert "23 de setembro de 2026" in row.body
    assert "/pedido/" in row.body
    assert "token=" in row.body
    second = enqueue_order_email(db, get_settings(), order, "order_submitted")
    assert second.id == row.id
    get_settings.cache_clear()


def test_templates_distinguish_requested_and_confirmed_dates() -> None:
    submitted = TEMPLATES["order_submitted"][1].format(
        ref="LPTEST",
        date="quarta-feira, 23 de setembro de 2026",
        link="https://lojadepaes.com.br/pedido/LPTEST?token=abc",
        address="Rua das Flores, 10",
    )
    accepted = TEMPLATES["order_accepted"][1].format(
        ref="LPTEST",
        date="sábado, 26 de setembro de 2026",
        link="https://lojadepaes.com.br/pedido/LPTEST?token=abc",
        address="Rua das Flores, 10",
    )
    assert "Data pedida" in submitted
    assert "ainda não está reservada" in submitted
    assert "endereço protegido" in submitted
    assert "23 de setembro de 2026" in submitted
    assert "Rua das Flores" in submitted
    assert "data confirmada" in accepted
    assert "26 de setembro de 2026" in accepted


def test_enqueue_skips_until_identity_verified(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM_NAME", "Loja de Pães")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    get_settings.cache_clear()
    order = _order(db)
    row = enqueue_order_email(db, get_settings(), order, "order_submitted")
    assert row.status == "skipped"
    assert "identidade SES" in (row.last_error or "")
    get_settings.cache_clear()


def test_process_marks_sent_with_message_id(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()
    order = _order(db)
    row = enqueue_order_email(db, get_settings(), order, "order_accepted")
    assert row.status == "pending"
    assert "data confirmada" in row.body

    def fake_send(_settings, **_kwargs):
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(True, "ses-message-test-1", None)

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", fake_send)
    processed = process_due_outbox(db, get_settings())
    assert len(processed) == 1
    db.refresh(row)
    assert row.status == "sent"
    assert row.provider_message_id == "ses-message-test-1"
    assert row.sent_at is not None
    get_settings.cache_clear()


def test_process_does_not_touch_skipped(db: Session, monkeypatch) -> None:
    get_settings.cache_clear()
    order = _order(db)
    row = enqueue_order_email(db, get_settings(), order, "payment_approved")
    assert row.status == "skipped"
    called = {"n": 0}

    def fake_send(_settings, **_kwargs):
        called["n"] += 1
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(True, "should-not", None)

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", fake_send)
    processed = process_due_outbox(db, get_settings())
    assert processed == []
    assert called["n"] == 0
    db.refresh(row)
    assert row.status == "skipped"


def test_process_records_sanitized_failure(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()
    order = _order(db)
    row = enqueue_order_email(db, get_settings(), order, "order_submitted")

    def fake_send(_settings, **_kwargs):
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(False, None, "SES recusou o envio (MessageRejected)")

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", fake_send)
    process_due_outbox(db, get_settings())
    db.refresh(row)
    assert row.status == "failed"
    assert row.attempts == 1
    assert row.last_error == "SES recusou o envio (MessageRejected)"
    get_settings.cache_clear()


def test_formatted_mail_from_includes_display_name(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM_NAME", "Loja de Pães")
    get_settings.cache_clear()
    assert formatted_mail_from(get_settings()) == '"Loja de Pães" <loja@lojadepaes.com.br>'
    get_settings.cache_clear()


def test_send_blocked_when_identity_not_ready(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    get_settings.cache_clear()
    result = send_outbox_email(
        get_settings(),
        to_address="dest@example.com",
        subject="assunto",
        body="corpo",
    )
    assert result.accepted is False
    assert result.message_id is None
    assert "identidade SES" in (result.error or "")
    get_settings.cache_clear()


def test_pytest_never_calls_real_ses(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()
    result = send_outbox_email(
        get_settings(),
        to_address="dest@example.com",
        subject="assunto",
        body="corpo",
    )
    assert result.accepted is False
    assert result.message_id is None
    assert "transporte de teste" in (result.error or "")
    get_settings.cache_clear()


def test_send_requires_ses_backend(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "smtp")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    get_settings.cache_clear()
    result = send_outbox_email(
        get_settings(),
        to_address="dest@example.com",
        subject="assunto",
        body="corpo",
    )
    assert result.accepted is False
    assert result.message_id is None
    assert "não é SES" in (result.error or "")
    get_settings.cache_clear()


def test_sanitize_hides_unknown_codes() -> None:
    class Dummy(Exception):
        response = {"Error": {"Code": "SecretLeakX", "Message": "internal"}}

    text = sanitize_mail_error(Dummy())
    assert "SecretLeakX" not in text
    assert text == "SES recusou o envio (ses_error)"
