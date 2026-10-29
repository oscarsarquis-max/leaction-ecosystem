"""Prompt 100 — aceite com quantidade informada e pão só na mensagem.

Dados fictícios. Não lê nem altera solicitação, pedido ou pagamento reais.
"""

from datetime import timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import save_date_override
from app.domain.storefront_orders import email_access_token
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, FinancialStatus
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from app.models.schedule import ScheduleClosure
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

assert admin_client


def _variant(db: Session, name: str, *, price_cents: int | None = 2490, label: str = "500 g") -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name=f"Massa {name[:12]}")
    product = Product(
        name=name,
        slug=f"p100-{uuid4().hex[:8]}",
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
        display_name=label,
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=price_cents,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _request(
    client: TestClient,
    key: str,
    desired: str,
    *,
    message: str,
    quantity: int | None = 1,
    lines: list[dict] | None = None,
) -> dict:
    payload = {
        "desired_date": desired,
        "customer_name": "Cliente 100",
        "customer_email": f"{key}@example.test",
        "message": message,
        "idempotency_key": key,
        "lines": lines or [],
    }
    if quantity is not None:
        payload["intended_quantity"] = quantity
    created = client.post("/api/v1/schedule/date-requests", json=payload)
    assert created.status_code == 200, created.text
    return created.json()


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def test_message_only_admin_confirms_product_then_accepts(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _variant(db, "Focaccia Alta")
    other = _variant(db, "Brioche Doce", price_cents=3100)
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=3)).isoformat()
    created = _request(
        admin_client,
        "p100-msg",
        desired,
        message="Quero Focaccia Alta com a quantidade combinada",
    )
    row = db.query(DateRequest).filter_by(id=created["id"]).one()
    assert row.intended_quantity == 1
    assert row.cart_context in (None, [])

    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["can_accept"] is False
    assert preview["needs_catalog_choice"] is True
    assert preview["informed_quantity"] == 1
    assert preview["ask_customer"] is False
    assert "faltam os pães" not in " ".join(preview["gaps"])
    assert "quantidade 1" in preview["gaps"][0]
    assert preview["suggestion"]["variant_id"] == str(variant.id)
    assert preview["suggestion"]["unit_cents"] == 2490
    assert "endereço de entrega" in preview["complementary_pending"]
    assert "telefone" in preview["complementary_pending"]

    quoted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}/commercial-preview",
        headers=_headers(csrf),
        json={"lines": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert quoted.status_code == 200, quoted.text
    body = quoted.json()
    assert body["can_accept"] is True
    assert body["items"][0]["product_name"] == "Focaccia Alta"
    assert body["items"][0]["quantity"] == 1
    assert body["items"][0]["unit_cents"] == 2490
    assert body["total_cents"] == 2490
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 0

    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert accepted.status_code == 200, accepted.text
    replay = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(other.id), "quantity": 1}]},
    )
    assert replay.status_code == 200, replay.text
    assert accepted.json()["converted_order_id"] == replay.json()["converted_order_id"]
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.delivery_street is None
    assert order.total_cents == 2490
    item = db.query(OrderItem).filter_by(order_id=order.id).one()
    assert item.product_variant_id == variant.id
    assert item.quantity == 1
    payment = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    assert payment.financial_status == FinancialStatus.PENDING.value
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert "Pagar e acompanhar" in mail.body
    assert "Focaccia Alta" in mail.body
    assert "R$ 24,90" in mail.body
    assert "endereço de entrega" in mail.body
    assert "telefone" in mail.body
    assert "faltam os pães" not in mail.body
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=created["id"], kind="date_request_complete")
        .count()
        == 0
    )
    converted = (
        db.query(DateRequestEvent)
        .filter_by(request_id=created["id"], action="converted")
        .one()
    )
    assert converted.actor_ref
    assert "produto confirmado na área de aceite" in (converted.detail or "")
    assert db.query(DateRequestEvent).filter_by(request_id=created["id"], action="created").count() == 1

    mail.status = "failed"
    mail.last_error = "transporte de teste"
    db.commit()
    failed_replay = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept"},
    )
    assert failed_replay.status_code == 200
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1

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
            order_id="hub-100",
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
    db.refresh(payment)
    assert payment.financial_status == FinancialStatus.PENDING.value


def test_structured_lines_accept_without_reconfirmation(admin_client: TestClient, db: Session) -> None:
    variant = _variant(db, "Focaccia Alta")
    decoy = _variant(db, "Pao de Forma", price_cents=1800)
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=4)).isoformat()
    created = _request(
        admin_client,
        "p100-struct",
        desired,
        message="já escolhi na seleção",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["can_accept"] is True
    assert preview["needs_catalog_choice"] is False
    assert preview["suggestion"] is None
    assert preview["items"][0]["quantity"] == 1
    assert preview["total_cents"] == 2490
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(decoy.id), "quantity": 2}]},
    )
    assert accepted.status_code == 200, accepted.text
    item = db.query(OrderItem).filter_by(order_id=accepted.json()["converted_order_id"]).one()
    assert item.product_variant_id == variant.id
    assert item.quantity == 1


def test_ambiguous_message_requires_explicit_distribution(admin_client: TestClient, db: Session) -> None:
    focaccia = _variant(db, "Focaccia Alta")
    brioche = _variant(db, "Brioche Doce", price_cents=3100)
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=5)).isoformat()
    created = _request(
        admin_client,
        "p100-amb",
        desired,
        quantity=2,
        message="Talvez Focaccia Alta ou Brioche Doce",
    )
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["suggestion"] is None
    assert preview["can_accept"] is False
    silent = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept"},
    )
    assert silent.status_code == 422
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 0
    uneven = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}/commercial-preview",
        headers=_headers(csrf),
        json={
            "lines": [
                {"variant_id": str(focaccia.id), "quantity": 1},
                {"variant_id": str(brioche.id), "quantity": 1},
            ]
        },
    )
    assert uneven.status_code == 200
    assert uneven.json()["can_accept"] is True
    assert uneven.json()["total_cents"] == 2490 + 3100
    mismatch = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}/commercial-preview",
        headers=_headers(csrf),
        json={
            "lines": [
                {"variant_id": str(focaccia.id), "quantity": 2},
                {"variant_id": str(brioche.id), "quantity": 2},
            ]
        },
    )
    assert mismatch.json()["can_accept"] is False
    assert "Distribua" in mismatch.json()["gaps"][0]
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={
            "action": "accept",
            "lines": [
                {"variant_id": str(focaccia.id), "quantity": 1},
                {"variant_id": str(brioche.id), "quantity": 1},
            ],
        },
    )
    assert accepted.status_code == 200, accepted.text
    items = db.query(OrderItem).filter_by(order_id=accepted.json()["converted_order_id"]).all()
    assert sorted(item.quantity for item in items) == [1, 1]
    assert {item.product_variant_id for item in items} == {focaccia.id, brioche.id}


def test_several_options_of_one_name_are_not_a_silent_sku(admin_client: TestClient, db: Session) -> None:
    first = _variant(db, "Focaccia Alta", label="500 g")
    db.add(
        ProductVariant(
            product_id=first.product_id,
            display_name="1 kg",
            presentation_type="weight",
            net_weight_grams=1000,
            physical_units=1,
            price_cents=4800,
            currency="BRL",
            is_active=True,
            sort_order=1,
        )
    )
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=6)).isoformat()
    created = _request(
        admin_client,
        "p100-opts",
        desired,
        message="Focaccia Alta, sem dizer o peso",
    )
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["suggestion"]["variant_id"] is None
    assert preview["suggestion"]["product_name"] == "Focaccia Alta"
    assert preview["can_accept"] is False


def test_missing_price_does_not_invent_one(admin_client: TestClient, db: Session) -> None:
    priced = _variant(db, "Focaccia Alta")
    unpriced = _variant(db, "Pao sem preco", price_cents=None)
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=7)).isoformat()
    created = _request(admin_client, "p100-price", desired, message="mensagem sem nome de catalogo")
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert all(choice["variant_id"] != str(unpriced.id) for choice in preview["catalog_choices"])
    assert any(choice["variant_id"] == str(priced.id) for choice in preview["catalog_choices"])
    quoted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}/commercial-preview",
        headers=_headers(csrf),
        json={"lines": [{"variant_id": str(unpriced.id), "quantity": 1}]},
    )
    assert quoted.json()["can_accept"] is False
    assert quoted.json()["total_cents"] is None
    refused = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(unpriced.id), "quantity": 1}]},
    )
    assert refused.status_code == 422
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 0


def test_explicit_closure_still_blocks_and_request_remains(admin_client: TestClient, db: Session) -> None:
    variant = _variant(db, "Focaccia Alta")
    db.commit()
    csrf = login(admin_client)
    target = bakery_today(get_settings()) + timedelta(days=8)
    created = _request(admin_client, "p100-closed", target.isoformat(), message="Focaccia Alta")
    db.add(
        ScheduleClosure(
            start_date=target,
            end_date=target,
            first_eligible_date=target + timedelta(days=1),
            pause_intake=False,
            internal_reason="fechamento de teste",
            created_by="test",
            updated_by="test",
        )
    )
    db.commit()
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["can_accept"] is False
    assert any("fechado" in gap for gap in preview["gaps"])
    refused = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert refused.status_code == 409
    assert db.query(DateRequest).filter_by(id=created["id"]).one().status == "pending"
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 0


def test_capacity_still_blocks_the_second_acceptance(admin_client: TestClient, db: Session) -> None:
    variant = _variant(db, "Focaccia Alta")
    crowded = bakery_today(get_settings()) + timedelta(days=9)
    save_date_override(
        db,
        get_settings(),
        crowded,
        open_state="open",
        daily_physical_limit=1,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    db.commit()
    csrf = login(admin_client)
    first = _request(admin_client, "p100-cap-a", crowded.isoformat(), message="Focaccia Alta")
    second = _request(admin_client, "p100-cap-b", crowded.isoformat(), message="Focaccia Alta")
    lines = {"action": "accept", "lines": [{"variant_id": str(variant.id), "quantity": 1}]}
    assert (
        admin_client.post(
            f"/api/v1/admin/date-requests/{first['id']}", headers=_headers(csrf), json=lines
        ).status_code
        == 200
    )
    blocked = admin_client.post(
        f"/api/v1/admin/date-requests/{second['id']}", headers=_headers(csrf), json=lines
    )
    assert blocked.status_code == 409
    assert db.query(Order).filter_by(source_date_request_id=second["id"]).count() == 0


def test_exceptional_date_without_address_still_reserves(admin_client: TestClient, db: Session) -> None:
    variant = _variant(db, "Focaccia Alta")
    db.commit()
    csrf = login(admin_client)
    today = bakery_today(get_settings()).isoformat()
    created = _request(admin_client, "p100-today", today, message="Focaccia Alta fora da rotina")
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert accepted.status_code == 200, accepted.text
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.delivery_street is None
    assert order.production_local_date.isoformat() == today
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert "/pedido/" in mail.body
