import base64
import hashlib
import hmac
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.orders import confirm_order
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import submit_order
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _next_wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta)
    if day < today:
        day += timedelta(days=7)
    return day.isoformat()


def _product(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa teste")
    product = Product(
        name="Pão teste",
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=2490,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _sign(payload: dict, secret: str) -> str:
    def b64(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64({"alg": "HS256", "typ": "JWT"})
    body = b64(payload)
    signature = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


@pytest.fixture
def shop_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    del db
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "loja-test-secret")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_quote_and_submit_are_idempotent(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    day = _next_wednesday()
    items = [{"variant_id": str(variant.id), "quantity": 1}]
    quote = shop_client.post("/api/v1/storefront/quote", json={"requested_date": day, "items": items})
    assert quote.status_code == 200, quote.text
    assert quote.json()["occupies_capacity"] is False
    assert quote.json()["total_cents"] == 2490
    payload = {
        "requested_date": day,
        "items": items,
        "quoted_cents": 2490,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "idempotency_key": "submit-key-1234",
    }
    first = shop_client.post("/api/v1/storefront/orders", json=payload)
    second = shop_client.post("/api/v1/storefront/orders", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json()["public_reference"] == second.json()["public_reference"]
    assert first.json()["holds_capacity"] is False
    assert first.json()["visitor_state"] == "awaiting_payment"
    assert db.query(Order).count() == 1
    from app.domain.storefront_orders import email_access_token
    from app.models.email_outbox import EmailOutbox

    order = db.query(Order).one()
    mail = db.query(EmailOutbox).filter_by(order_id=order.id).one()
    assert "Data pedida" in mail.body
    assert "23 de setembro" in mail.body
    assert "/pedido/" in mail.body
    assert "token=" in mail.body
    email_token = email_access_token(get_settings(), order)
    opened = shop_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": email_token},
    )
    assert opened.status_code == 200, opened.text


def test_price_change_rejects_stale_quote(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    day = _next_wednesday()
    items = [{"variant_id": str(variant.id), "quantity": 1}]
    stale = {
        "requested_date": day,
        "items": items,
        "quoted_cents": 1000,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "idempotency_key": "stale-quote-999",
    }
    response = shop_client.post("/api/v1/storefront/orders", json=stale)
    assert response.status_code == 409
    assert response.json()["code"] == "price_changed"


def test_payment_does_not_occupy_admin_accept_does(
    shop_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    variant = _product(db)
    db.commit()
    day = _next_wednesday()
    order, token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": day,
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "pay-no-occupy",
        },
    )
    db.commit()

    def fake_checkout(*_args, **kwargs):
        return HubCheckoutResult(
            order_id="hub-order-1",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix",
            pix_qr_code_base64="abc",
            pix_ticket_url=None,
            pix_date_of_expiration="2026-09-20T18:00:00-03:00",
            mp_payment_id="999",
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    pay = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert pay.status_code == 200, pay.text
    assert pay.json()["method"] == "pix"
    assert pay.json()["pix"]["qr_code"] == "00020126pix"
    db.refresh(order)
    assert order.holds_capacity is False
    confirm_order(db, order.id, actor_ref="admin")
    db.commit()
    db.refresh(order)
    assert order.holds_capacity is True
    assert order.status == "confirmed"


def test_webhook_marks_paid_without_confirming_bake(
    shop_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    order, token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "webhook-paid",
        },
    )
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.external_reference = "hub-paid-1"
    db.commit()
    token_jwt = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "PAYMENT_CONFIRMED",
            "app_id": "lojadepaes",
            "outbox_id": "outbox-1",
            "payload": {
                "order_reference": order.public_reference,
                "order_id": "hub-paid-1",
                "financial_status": "paid",
                "paid_amount_cents": 2490,
                "mp_status": "approved",
            },
        },
        "loja-test-secret",
    )
    hooked = shop_client.post("/api/v1/webhooks/actionhub", json={"token": token_jwt})
    assert hooked.status_code == 200, hooked.text
    view = shop_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert view.json()["financially_settled"] is True
    assert view.json()["holds_capacity"] is False
    assert view.json()["visitor_state"] == "paid_awaiting_accept"
    assert view.json()["confirmed"] is False


def test_bad_order_token_is_rejected(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    order, _token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "bad-token",
        },
    )
    db.commit()
    denied = shop_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": "nope"},
    )
    assert denied.status_code == 401


def test_webhook_duplicate_and_out_of_order_are_ignored(
    shop_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    order, token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "webhook-order-dup",
        },
    )
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.external_reference = "hub-paid-dup"
    db.commit()
    paid = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "PAYMENT_CONFIRMED",
            "app_id": "lojadepaes",
            "outbox_id": "outbox-dup-1",
            "payload": {
                "order_reference": order.public_reference,
                "order_id": "hub-paid-dup",
                "financial_status": "paid",
                "paid_amount_cents": 2490,
                "mp_status": "approved",
            },
        },
        "loja-test-secret",
    )
    first = shop_client.post("/api/v1/webhooks/actionhub", json={"token": paid})
    second = shop_client.post("/api/v1/webhooks/actionhub", json={"token": paid})
    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    stale = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "PAYMENT_UPDATED",
            "app_id": "lojadepaes",
            "outbox_id": "outbox-dup-stale",
            "payload": {
                "order_reference": order.public_reference,
                "order_id": "hub-paid-dup",
                "financial_status": "pending",
                "mp_status": "pending",
            },
        },
        "loja-test-secret",
    )
    late = shop_client.post("/api/v1/webhooks/actionhub", json={"token": stale})
    assert late.status_code == 200
    assert late.json()["process_status"] == "ignored"
    view = shop_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert view.json()["financially_settled"] is True
    assert view.json()["holds_capacity"] is False


def test_pix_checkout_is_reused_and_method_switch_needs_replace(
    shop_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    variant = _product(db)
    db.commit()
    order, token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "pix-reuse",
        },
    )
    db.commit()
    calls = {"n": 0}

    def fake_checkout(*_args, **kwargs):
        calls["n"] += 1
        return HubCheckoutResult(
            order_id=f"hub-pix-{calls['n']}",
            status="PENDING",
            checkout_url="http://127.0.0.1:4000/dashboard?checkout=x&client=lojadepaes",
            amount_cents=2490,
            reused=calls["n"] > 1,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix-reused",
            pix_qr_code_base64="abc",
            pix_ticket_url=None,
            pix_date_of_expiration="2026-09-20T18:00:00-03:00",
            mp_payment_id="888",
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    monkeypatch.setattr("app.domain.storefront_orders.cancel_amount_checkout", lambda *_a, **_k: None)
    first = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert first.status_code == 200, first.text
    recovered = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert recovered.status_code == 200
    assert recovered.json()["reused"] is True
    assert recovered.json()["pix"]["qr_code"] == "00020126pix-reused"
    blocked = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "card"},
        headers={"X-Order-Token": token},
    )
    assert blocked.status_code == 422
    swapped = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "card", "replace": True},
        headers={"X-Order-Token": token},
    )
    assert swapped.status_code == 200, swapped.text
    assert swapped.json()["method"] == "card"
    assert swapped.json()["pix"] is None
    assert calls["n"] == 2
