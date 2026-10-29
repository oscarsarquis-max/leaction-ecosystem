from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.customer_mail import CTA_PAY, render_order_accepted_parts
from app.domain.storefront_orders import email_access_token
from app.models.enums import FinancialStatus, OrderStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.test_prompt68 import _accept, _create_date, _product

assert admin_client


def _accepted(admin_client: TestClient, db: Session, key: str) -> tuple[Order, str]:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        key,
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    return order, email_access_token(get_settings(), order)


def test_accepted_unpaid_email_points_to_order_pay_actions(
    admin_client: TestClient, db: Session
) -> None:
    order, token = _accepted(admin_client, db, "p71-mail")
    order.status = OrderStatus.IN_PRODUCTION.value
    db.commit()
    headers = {"X-Order-Token": token}
    view = admin_client.get(f"/api/v1/storefront/orders/{order.public_reference}", headers=headers)
    assert view.status_code == 200
    body = view.json()
    assert body["payment_available"] is True
    assert body["delivery_pending"] is True
    assert body["financially_settled"] is False
    assert not body.get("payment_unavailable_reason")
    _subject, text, html = render_order_accepted_parts(db, get_settings(), order)
    assert CTA_PAY in text
    assert f"/pedido/{order.public_reference}" in text
    assert "/solicitacao/" not in text
    assert f'href="' in html and f"/pedido/{order.public_reference}" in html
    assert CTA_PAY in html


def test_payments_disabled_explains_missing_action(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    order, token = _accepted(admin_client, db, "p71-off-ok")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        view = admin_client.get(
            f"/api/v1/storefront/orders/{order.public_reference}",
            headers={"X-Order-Token": token},
        )
        assert view.json()["payment_available"] is False
        assert "desativados" in (view.json().get("payment_unavailable_reason") or "")
    finally:
        monkeypatch.delenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", raising=False)
        get_settings.cache_clear()


def test_cancelled_and_paid_do_not_open_charge(admin_client: TestClient, db: Session) -> None:
    cancelled, token = _accepted(admin_client, db, "p71-cancel")
    cancelled.status = OrderStatus.CANCELLED.value
    db.commit()
    denied = admin_client.get(
        f"/api/v1/storefront/orders/{cancelled.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert denied.json()["payment_available"] is False
    assert "cancelado" in (denied.json().get("payment_unavailable_reason") or "")
    charged = admin_client.post(
        f"/api/v1/storefront/orders/{cancelled.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert charged.status_code == 422

    paid, pay_token = _accepted(admin_client, db, "p71-paid")
    record = db.query(PaymentRecord).filter_by(order_id=paid.id).one()
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = paid.total_cents
    db.commit()
    view = admin_client.get(
        f"/api/v1/storefront/orders/{paid.public_reference}",
        headers={"X-Order-Token": pay_token},
    )
    assert view.json()["financially_settled"] is True
    assert view.json()["payment_available"] is False
    again = admin_client.post(
        f"/api/v1/storefront/orders/{paid.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": pay_token},
    )
    assert again.status_code == 422


def test_in_production_checkout_is_idempotent(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    order, token = _accepted(admin_client, db, "p71-pix-ok")
    order.status = OrderStatus.IN_PRODUCTION.value
    db.commit()
    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-71",
            status="PENDING",
            checkout_url="https://pay.example.test/card-71" if kwargs.get("method") == "card" else None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix71",
            pix_qr_code_base64="abc",
        ),
    )
    headers = {"X-Order-Token": token}
    first = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    second = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["reused"] is True
    assert db.query(PaymentRecord).filter_by(order_id=order.id).count() == 1
    db.refresh(order)
    assert order.status == OrderStatus.IN_PRODUCTION.value
    assert order.total_cents == 2490
