from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.customer_mail import (
    CTA_FOLLOW,
    CTA_PAY,
    DELIVERY_NEED,
    official_logo_url,
    render_order_accepted_parts,
)
from app.domain.date_request_accept import date_request_access_token
from app.domain.email_outbox import enqueue_corrective_order_notice, process_due_outbox
from app.domain.storefront_orders import email_access_token, parse_delivery_address
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import FinancialStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_prompt68 import _accept, _create_date, _product, _wednesday

assert admin_client


def test_accept_email_has_payment_and_delivery_in_one_message(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-mail",
        name="Bia 70",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    assert accepted.status_code == 200, accepted.text
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert mail.dedupe_key == f"{order.id}:order_accepted"
    assert CTA_PAY in mail.body
    assert DELIVERY_NEED in mail.body
    assert "/pedido/" in mail.body
    assert "token=" in mail.body
    assert order.public_reference in mail.body
    assert "R$ 24,90" in mail.body
    assert "Focaccia Alta" in mail.body
    assert db.query(EmailOutbox).filter_by(
        date_request_id=created["id"], kind="date_request_complete"
    ).count() == 0
    subject, text, html = render_order_accepted_parts(db, get_settings(), order)
    assert CTA_PAY in subject or CTA_PAY in text
    assert official_logo_url(get_settings()) in html
    assert 'alt="Loja de Pães"' in html
    assert CTA_PAY in html
    assert DELIVERY_NEED in html
    assert "/images/lojadepaeslogo.png" in html
    assert "gigio" not in html.lower()


def test_protected_page_pays_then_saves_address_reload(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-save",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    token = email_access_token(get_settings(), order)
    headers = {"X-Order-Token": token}
    view = admin_client.get(f"/api/v1/storefront/orders/{order.public_reference}", headers=headers)
    assert view.json()["payment_available"] is True
    assert view.json()["delivery_pending"] is True

    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-70",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix70",
            pix_qr_code_base64="abc",
        ),
    )
    pay = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers=headers,
    )
    assert pay.status_code == 200, pay.text

    masked = {**NEW_ORDER_ADDRESS, "delivery_state": "CEARA", "delivery_postal_code": "60150-160"}
    saved = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/delivery-address",
        json=masked,
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["delivery_pending"] is False
    reloaded = admin_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}", headers=headers
    )
    address = reloaded.json()["delivery_address"]
    assert address["street"] == NEW_ORDER_ADDRESS["delivery_street"]
    assert address["state"] == "CE"
    assert address["postal_code"] == "60150160"
    db.refresh(order)
    assert order.total_cents == 2490
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1


def test_uf_and_cep_contract_and_validation_error(admin_client: TestClient, db: Session) -> None:
    parsed = parse_delivery_address({**NEW_ORDER_ADDRESS, "delivery_state": "ceará", "delivery_postal_code": "60150-160"})
    assert parsed["delivery_state"] == "CE"
    assert parsed["delivery_postal_code"] == "60150160"
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-valid",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    token = email_access_token(get_settings(), order)
    failed = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/delivery-address",
        json={**NEW_ORDER_ADDRESS, "delivery_state": "XX", "delivery_street": "Rua Ficticia 70"},
        headers={"X-Order-Token": token},
    )
    assert failed.status_code == 422
    assert "sigla do estado" in failed.json()["detail"]
    db.refresh(order)
    assert order.delivery_street is None


def test_old_converted_link_points_to_order_not_new_accept(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-oldlink",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    request_token = date_request_access_token(get_settings(), db.get(DateRequest, created["id"]))
    public = admin_client.get(
        f"/api/v1/schedule/date-requests/{created['id']}", params={"token": request_token}
    )
    assert public.status_code == 200
    href = public.json()["order_href"]
    assert order.public_reference in href
    assert "token=" in href
    assert href.startswith(get_settings().public_origin.rstrip("/"))
    denied = admin_client.get(
        f"/api/v1/schedule/date-requests/{created['id']}", params={"token": "invalido123"}
    )
    assert denied.status_code == 401
    other = admin_client.get(f"/api/v1/storefront/orders/{order.public_reference}")
    assert other.status_code == 401
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1


def test_corrective_notice_is_idempotent_and_skips_when_paid(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-recov",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    first = enqueue_corrective_order_notice(
        db, get_settings(), order, recovery_key="prompt70", actor_ref="admin:prompt70"
    )
    second = enqueue_corrective_order_notice(
        db, get_settings(), order, recovery_key="prompt70", actor_ref="admin:prompt70"
    )
    assert first.id == second.id
    assert first.dedupe_key == f"{order.id}:order_accepted:prompt70"
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 2
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = order.total_cents
    db.flush()
    _subject, text, html = render_order_accepted_parts(db, get_settings(), order)
    assert CTA_FOLLOW in text
    assert CTA_PAY not in text
    assert "pagamento já foi recebido" in text
    assert CTA_FOLLOW in html


def test_old_complete_link_saves_address_on_in_production_order(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-old-complete",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    order.status = "in_production"
    db.commit()
    request = db.get(DateRequest, created["id"])
    token = date_request_access_token(get_settings(), request)
    filled = admin_client.post(
        f"/api/v1/schedule/date-requests/{created['id']}/complete",
        json={"token": token, **NEW_ORDER_ADDRESS, "delivery_state": "CEARA"},
    )
    assert filled.status_code == 200, filled.text
    assert filled.json()["delivery_pending"] is False
    assert filled.json()["converted"] is True
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    assert order.delivery_state == "CE"
    assert order.status == "in_production"
    assert order.total_cents == 2490


def test_in_production_date_request_order_saves_address_and_can_pay(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-prod-addr",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    order.status = "in_production"
    db.commit()
    token = email_access_token(get_settings(), order)
    saved = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/delivery-address",
        json={**NEW_ORDER_ADDRESS, "delivery_state": "CEARA", "delivery_postal_code": "60150-160"},
        headers={"X-Order-Token": token},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["delivery_pending"] is False
    assert saved.json()["payment_available"] is True
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    assert order.delivery_state == "CE"
    assert order.status == "in_production"
    assert order.total_cents == 2490

    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-70-prod",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix70p",
            pix_qr_code_base64="abc",
        ),
    )
    pay = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout?token={token}",
        json={"method": "pix"},
    )
    assert pay.status_code == 200, pay.text


def test_paid_order_does_not_open_new_charge(admin_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p70-paid",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = order.total_cents
    db.commit()
    token = email_access_token(get_settings(), order)
    charged = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert charged.status_code == 422
    assert db.query(PaymentRecord).filter_by(order_id=order.id).count() == 1


def test_standard_checkout_and_outbox_retry(admin_client: TestClient, db: Session, monkeypatch) -> None:
    variant = _product(db)
    db.commit()
    standard = admin_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Auto 70",
            "customer_email": "auto-70@example.test",
            **NEW_ORDER_ADDRESS,
            "idempotency_key": "p70-auto-ok",
        },
    )
    assert standard.status_code == 200, standard.text
    order = db.query(Order).filter_by(public_reference=standard.json()["public_reference"]).one()
    assert order.status == "confirmed"
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()
    mail.status = "failed"
    mail.attempts = 1
    db.flush()

    def fake_send(_settings, **kwargs):
        from app.domain.ses_mailer import MailSendResult

        assert kwargs.get("html_body")
        assert "Loja de Pães" in kwargs["html_body"]
        return MailSendResult(True, "ses-70", None)

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", fake_send)
    processed = process_due_outbox(db, get_settings())
    assert processed
    db.refresh(mail)
    assert mail.status == "sent"
    get_settings.cache_clear()
