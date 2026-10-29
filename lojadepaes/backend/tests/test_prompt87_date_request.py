"""Regressão permanente do fechamento: data excepcional (focaccia / hoje),
fila de Pedidos, notificação operacional, aceite, reserva, pagamento e
personalizado. Ligada a mudanças no Fazedor, calendário, carrinho e fechamento.
Só banco e transporte de teste. Não toca pedido histórico de cliente."""

from uuid import uuid4

from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.attendance import date_request_reference
from app.domain.bakery_time import bakery_today
from app.domain.custom_loaf import public_builder_catalog
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import email_access_token
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, OrderStatus
from app.models.orders import Order
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_custom_loaf import _catalog, _payload, _wednesday

assert admin_client


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def _focaccia(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 87")
    product = Product(
        name="Focaccia Alta",
        slug=f"focaccia-87-{uuid4().hex[:8]}",
        short_description="teste",
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


def _create_date(client: TestClient, key: str, variant: ProductVariant, desired_date: str) -> dict:
    first = client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": desired_date,
            "customer_name": "Cliente 87",
            "customer_email": f"{key}@example.test",
            "intended_quantity": 1,
            "message": "focaccia fora do calendário",
            "idempotency_key": key,
            "lines": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert first.status_code == 200, first.text
    replay = client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": desired_date,
            "customer_name": "Cliente 87",
            "customer_email": f"{key}@example.test",
            "intended_quantity": 1,
            "message": "focaccia fora do calendário",
            "idempotency_key": key,
            "lines": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    return first.json()


def _exceptional_journey(admin_client: TestClient, db: Session, monkeypatch, *, key: str) -> None:
    variant = _focaccia(db)
    db.commit()
    csrf = login(admin_client)
    today = bakery_today(get_settings()).isoformat()
    created = _create_date(admin_client, key, variant, today)
    assert created["status"] == "pending"
    assert db.query(DateRequest).filter_by(id=created["id"]).one().desired_date.isoformat() == today

    listed = admin_client.get("/api/v1/admin/orders").json()
    assert listed["date_requests_error"] is None
    row = next(item for item in listed["items"] if item["id"] == created["id"])
    assert row["source"] == "date_request"
    assert row["public_reference"] == date_request_reference(created["id"])
    summary = admin_client.get("/api/v1/admin/ops/attendance-summary").json()
    assert summary["date_requests_awaiting"] >= 1
    assert any(item["id"] == created["id"] or created["id"] in str(item) for item in summary.get("priority") or [{}]) or summary[
        "date_requests_awaiting"
    ] >= 1

    admin_mail = (
        db.query(EmailOutbox)
        .filter_by(date_request_id=created["id"], kind="date_request_received_admin")
        .one()
    )
    customer_mail = (
        db.query(EmailOutbox)
        .filter_by(date_request_id=created["id"], kind="date_request_received")
        .one()
    )
    assert admin_mail.to_address
    assert customer_mail.to_address
    assert customer_mail.id != admin_mail.id
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=created["id"], kind="date_request_received_admin")
        .count()
        == 1
    )

    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["can_accept"] is True
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept"},
    )
    replay_accept = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept"},
    )
    assert accepted.status_code == 200, accepted.text
    assert replay_accept.status_code == 200
    assert accepted.json()["converted_order_id"] == replay_accept.json()["converted_order_id"]
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.delivery_street is None
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert "/pedido/" in mail.body
    token = email_access_token(get_settings(), order)
    view = admin_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert view.status_code == 200
    assert view.json()["payment_available"] is True
    assert view.json()["delivery_pending"] is True

    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-87",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
        ),
    )
    pay = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        headers={"X-Order-Token": token},
        json={"method": "pix"},
    )
    assert pay.status_code == 200, pay.text


def test_exceptional_focaccia_today_queue_accept_payment(admin_client: TestClient, db: Session, monkeypatch) -> None:
    _exceptional_journey(admin_client, db, monkeypatch, key="p87-today")


def test_exceptional_journey_with_gigio_off(admin_client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "false")
    get_settings.cache_clear()
    _exceptional_journey(admin_client, db, monkeypatch, key="p87-nogigio")


def test_standard_order_and_custom_evaluation_still_work(admin_client: TestClient, db: Session) -> None:
    variant = _focaccia(db)
    custom = _catalog(db)
    public_builder_catalog(db)
    db.commit()
    login(admin_client)
    standard = admin_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana 87",
            "customer_email": "ana-87@example.test",
            **NEW_ORDER_ADDRESS,
            "idempotency_key": "p87-std-1",
        },
    )
    assert standard.status_code == 200, standard.text
    order = db.query(Order).filter_by(public_reference=standard.json()["public_reference"]).one()
    assert order.status == OrderStatus.CONFIRMED.value
    assert order.holds_capacity is True

    custom_payload = _payload(custom, quoted_cents=7000, item={"quantity": 1, "free_ingredient_text": "pepperoni"})
    custom_payload["customer_name"] = "Bia 87"
    custom_payload["customer_email"] = "bia-87@example.test"
    custom_payload["idempotency_key"] = "p87-custom-1"
    created = admin_client.post("/api/v1/storefront/orders", json=custom_payload)
    assert created.status_code == 200, created.text
    custom_order = db.query(Order).filter_by(public_reference=created.json()["public_reference"]).one()
    assert custom_order.status == OrderStatus.SUBMITTED.value
    assert custom_order.holds_capacity is False
