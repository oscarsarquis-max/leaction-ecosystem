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
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _next_wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta)
    if day <= today:
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
    asked = first.json()["requested_date"]
    assert asked
    asked_day = int(asked.split("-")[2])
    assert f"{asked_day} de setembro" in mail.body
    assert "/pedido/" in mail.body
    assert "token=" in mail.body
    email_token = email_access_token(get_settings(), order)
    opened = shop_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": email_token},
    )
    assert opened.status_code == 200, opened.text


def test_one_loaf_without_physical_units_quotes_its_own_price(shop_client: TestClient, db: Session) -> None:
    product = Product(
        name="Rolled Bread de teste",
        slug=f"rolled-{uuid4().hex[:8]}",
        short_description="teste",
        recipe_base_id=None,
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
        physical_units=None,
        price_cents=7000,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.commit()
    day = _next_wednesday()
    one = shop_client.post(
        "/api/v1/storefront/quote",
        json={"requested_date": day, "items": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert one.status_code == 200, one.text
    body = one.json()
    assert body["total_cents"] == 7000
    assert body["items"][0]["quantity"] == 1
    assert body["items"][0]["unit_cents"] == 7000
    assert body["items"][0]["physical_units"] is None
    assert "pães físicos" in body["notice"]
    assert "tipo de pão" in body["notice"]
    two = shop_client.post(
        "/api/v1/storefront/quote",
        json={"requested_date": day, "items": [{"variant_id": str(variant.id), "quantity": 2}]},
    )
    assert two.status_code == 200, two.text
    assert two.json()["total_cents"] == 14000
    assert two.json()["items"][0]["quantity"] == 2
    past = (bakery_today(get_settings()) - timedelta(days=1)).isoformat()
    blocked = shop_client.post(
        "/api/v1/storefront/quote",
        json={"requested_date": past, "items": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert blocked.status_code == 409
    today = bakery_today(get_settings()).isoformat()
    same_day = shop_client.post(
        "/api/v1/storefront/quote",
        json={"requested_date": today, "items": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert same_day.status_code == 409
    assert "próximos dias" in same_day.text or "data passada" in same_day.text or "sem produção" in same_day.text
    submitted = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 7000,
            "customer_name": "Ana Teste",
            "customer_email": "ana@example.com",
            "idempotency_key": "one-loaf-7000",
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["total_cents"] == 7000
    order = db.query(Order).one()
    stored = db.query(OrderItem).filter_by(order_id=order.id).one()
    assert order.total_cents == 7000
    assert stored.quantity == 1
    assert stored.unit_price_cents == 7000
    assert stored.physical_units is None
    assert order.holds_capacity is False


def test_preferred_time_is_optional_and_persisted(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    day = _next_wednesday()
    items = [{"variant_id": str(variant.id), "quantity": 1}]
    quote = shop_client.post("/api/v1/storefront/quote", json={"requested_date": day, "items": items})
    assert quote.status_code == 200, quote.text
    invalid = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": items,
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "preferred_time": "25:99",
            "idempotency_key": "pref-time-bad",
        },
    )
    assert invalid.status_code == 422
    empty = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": items,
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "pref-time-empty",
        },
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["preferred_time"] is None
    assert empty.json()["total_cents"] == 2490
    filled = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": items,
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "preferred_time": "16:30",
            "idempotency_key": "pref-time-1630",
        },
    )
    assert filled.status_code == 200, filled.text
    assert filled.json()["preferred_time"] == "16:30"
    assert filled.json()["total_cents"] == 2490
    stored = db.query(Order).filter_by(public_reference=filled.json()["public_reference"]).one()
    assert stored.preferred_time.hour == 16
    assert stored.preferred_time.minute == 30
    from app.models.email_outbox import EmailOutbox

    mail = db.query(EmailOutbox).filter_by(order_id=stored.id).one()
    assert "Horário solicitado: 16:30 (preferência; ainda não confirmado)" in mail.body
    old = db.query(Order).filter_by(public_reference=empty.json()["public_reference"]).one()
    assert old.preferred_time is None


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


def test_paid_catalog_gap_can_be_accepted_once(db: Session) -> None:
    from app.domain.schedule import ensure_schedule_settings
    from app.models.enums import FinancialStatus

    product = Product(
        name="Pepperoni teste",
        slug=f"pep-{uuid4().hex[:8]}",
        short_description="teste",
        recipe_base_id=None,
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
        physical_units=None,
        price_cents=7000,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    order, _token = submit_order(
        db,
        get_settings(),
        {
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 7000,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": f"gap-accept-{uuid4().hex[:8]}",
        },
    )
    paid = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    paid.financial_status = FinancialStatus.PAID.value
    paid.amount_paid_cents = 7000
    paid.method = "pix"
    db.flush()
    settings = ensure_schedule_settings(db)
    settings.min_advance_hours = 72
    db.flush()
    assert order.holds_capacity is False
    first = confirm_order(db, order.id, actor_ref="admin")
    second = confirm_order(db, order.id, actor_ref="admin")
    assert first.id == second.id
    db.refresh(order)
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.fulfillment_modality == "pickup"
    paid = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    assert paid.financial_status == FinancialStatus.PAID.value
    assert paid.amount_paid_cents == 7000


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


def test_submit_creates_pix_when_hub_answers(
    shop_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    variant = _product(db)
    db.commit()

    def fake_checkout(*_args, **kwargs):
        return HubCheckoutResult(
            order_id="hub-auto-1",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126auto",
            pix_qr_code_base64="auto",
            pix_ticket_url=None,
            pix_date_of_expiration="2026-09-26T18:00:00-03:00",
            mp_payment_id="111",
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    payload = {
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(variant.id), "quantity": 1}],
        "quoted_cents": 2490,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "idempotency_key": "auto-pix-1",
    }
    created = shop_client.post("/api/v1/storefront/orders", json=payload)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["payment"]["method"] == "pix"
    assert body["payment"]["external_reference"] == "hub-auto-1"
    assert body["payment"]["pix"]["qr_code"] == "00020126auto"
    assert body["payment"]["sanitized_error"] is None


def test_submit_keeps_order_when_hub_refuses(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "auto-pix-fail",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["visitor_state"] == "awaiting_payment"
    assert body["payment"]["external_reference"] is None
    assert body["payment"]["sanitized_error"]
    assert "ActionHub" in body["payment"]["sanitized_error"]
