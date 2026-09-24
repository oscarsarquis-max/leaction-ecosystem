from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.errors import ConfirmationError
from app.domain.orders import confirm_order
from app.domain.recipe_bases import create_recipe_base
from app.main import create_app
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, FinancialStatus
from app.models.orders import Order, OrderItem, OrderItemAdaptation
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
    login,
)

assert TEST_ADMIN_PASSWORD


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


@pytest.fixture
def shop_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    del db
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "loja-test-secret")
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_order_without_adaptation_keeps_current_flow(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    items = [{"variant_id": str(variant.id), "quantity": 1}]
    quote = shop_client.post(
        "/api/v1/storefront/quote", json={"requested_date": _next_wednesday(), "items": items}
    )
    assert quote.status_code == 200
    assert "adaptation" not in quote.text
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": items,
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "plain-order-1",
        },
    )
    assert created.status_code == 200, created.text
    order = db.scalar(select(Order).where(Order.public_reference == created.json()["public_reference"]))
    assert order is not None
    assert db.scalar(select(OrderItemAdaptation)) is None
    confirm_order(db, order.id, actor_ref="admin")
    db.commit()
    db.refresh(order)
    assert order.status == "confirmed"


def test_adaptation_persists_on_item_and_blocks_client_self_approval(
    shop_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    product = db.get(Product, variant.product_id)
    assert product is not None
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "adaptation_text": "retirar gergelim <b>agora</b>",
                    "adaptation_reason": "dietary_restriction",
                    "status": "accepted",
                    "bakery_response": "ok",
                }
            ],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "adapt-self-1",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    adaptation = body["items"][0]["adaptation"]
    assert adaptation["status"] == "pending"
    assert adaptation["customer_text"] == "retirar gergelim agora"
    mail = db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "order_submitted"))
    assert mail is not None
    assert "Há uma solicitação de adaptação pendente" in mail.body
    assert "gergelim" not in mail.subject
    public = shop_client.get(f"/api/v1/catalog/products/{product.slug}")
    assert public.status_code == 200
    assert "retirar gergelim" not in public.text
    assert "adaptation" not in public.text
    csrf = login(shop_client)
    listed = shop_client.get("/api/v1/admin/orders")
    assert listed.json()["items"][0]["adaptation_attention"] is True
    assert "gergelim" not in listed.text
    order = db.scalar(select(Order).where(Order.public_reference == body["public_reference"]))
    assert order is not None
    with pytest.raises(ConfirmationError, match="adaptação pendente"):
        confirm_order(db, order.id, actor_ref="admin")
    db.rollback()
    blocked = shop_client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers={"X-CSRF-Token": csrf})
    assert blocked.status_code == 422
    item_id = body["items"][0]["id"]
    accepted = shop_client.post(
        f"/api/v1/admin/orders/{order.id}/items/{item_id}/adaptation",
        headers={"X-CSRF-Token": csrf},
        json={"decision": "accept", "response": "vamos retirar o gergelim por cima"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["items"][0]["adaptation"]["status"] == "accepted"
    assert accepted.json()["items"][0]["adaptation"]["customer_text"] == "retirar gergelim agora"
    confirm = shop_client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers={"X-CSRF-Token": csrf})
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"


def test_same_variant_keeps_distinct_lines_and_price(shop_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": [
                {"variant_id": str(variant.id), "quantity": 1},
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "adaptation_text": "sem gergelim",
                    "adaptation_reason": "preference",
                },
            ],
            "quoted_cents": 4980,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "two-lines-1",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["total_cents"] == 4980
    assert len(body["items"]) == 2
    assert body["items"][0]["adaptation"] is None
    assert body["items"][1]["adaptation"]["customer_text"] == "sem gergelim"
    order = db.scalar(select(Order).where(Order.public_reference == body["public_reference"]))
    stored = list(db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    assert len(stored) == 2
    assert sum(item.physical_units or 0 for item in stored) == 2


def test_alternative_is_not_confirmation_and_paid_decline_does_not_fake_refund(
    shop_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "adaptation_text": "sem leite",
                    "adaptation_reason": "dietary_restriction",
                }
            ],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "paid-decline-1",
        },
    )
    token = created.json()["access_token"]
    order = db.scalar(select(Order).where(Order.public_reference == created.json()["public_reference"]))
    assert order is not None
    record = db.scalar(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
    assert record is not None
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = 2490
    record.expected_cents = 2490
    db.commit()
    csrf = login(shop_client)
    item_id = created.json()["items"][0]["id"]
    proposed = shop_client.post(
        f"/api/v1/admin/orders/{order.id}/items/{item_id}/adaptation",
        headers={"X-CSRF-Token": csrf},
        json={"decision": "propose_alternative", "response": "podemos assar sem cobertura láctea visível"},
    )
    assert proposed.status_code == 200
    assert proposed.json()["items"][0]["adaptation"]["status"] == "alternative_proposed"
    mail = db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "adaptation_proposed"))
    assert mail is not None
    assert "sem leite" not in mail.body
    assert mail.status == "skipped"
    with pytest.raises(ConfirmationError, match="concordância explícita"):
        confirm_order(db, order.id, actor_ref="admin")
    db.rollback()
    declined_alt = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/items/{item_id}/adaptation",
        headers={"X-Order-Token": token},
        json={"decision": "decline"},
    )
    assert declined_alt.status_code == 200
    assert declined_alt.json()["items"][0]["adaptation"]["client_decision"] == "declined"
    with pytest.raises(ConfirmationError, match="concordância explícita"):
        confirm_order(db, order.id, actor_ref="admin")
    db.rollback()
    bakery_decline = shop_client.post(
        f"/api/v1/admin/orders/{order.id}/items/{item_id}/adaptation",
        headers={"X-CSRF-Token": csrf},
        json={"decision": "decline", "response": "há contato cruzado com leite na bancada"},
    )
    assert bakery_decline.status_code == 200
    assert bakery_decline.json()["items"][0]["adaptation"]["status"] == "declined"
    with pytest.raises(ConfirmationError, match="não pode ser aceito como pão sem alteração"):
        confirm_order(db, order.id, actor_ref="admin")
    db.rollback()
    db.refresh(record)
    assert record.expected_cents == 2490
    assert record.amount_paid_cents == 2490
    assert record.amount_refunded_cents in {None, 0}
    denied = shop_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert denied.status_code == 422


def test_hub_checkout_description_omits_restriction(
    shop_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    variant = _product(db)
    db.commit()
    created = shop_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _next_wednesday(),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "adaptation_text": "sem gergelim",
                    "adaptation_reason": "preference",
                }
            ],
            "quoted_cents": 2490,
            "customer_name": "Ana",
            "customer_email": "ana@example.com",
            "idempotency_key": "hub-desc-1",
        },
    )
    token = created.json()["access_token"]
    captured: dict = {}

    def fake_checkout(*_args, **kwargs):
        captured.update(kwargs)
        return HubCheckoutResult(
            order_id="hub-adapt",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method="pix",
            pix_qr_code="000201",
            pix_qr_code_base64=None,
            pix_ticket_url=None,
            pix_date_of_expiration=None,
            mp_payment_id=None,
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    paid = shop_client.post(
        f"/api/v1/storefront/orders/{created.json()['public_reference']}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert paid.status_code == 200, paid.text
    assert captured["description"] == f"Pedido Loja de Pães {created.json()['public_reference']}"
    assert "gergelim" not in str(captured)
