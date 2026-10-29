"""C01–C12: compra completa a partir do envio do carrinho, sem pedido pré-fabricado."""

from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.errors import CapacityError, PriceChangedError
from app.domain.orders import confirm_order
from app.domain.owner_alerts import order_summary
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.domain.storefront_orders import public_order_view, quote_lines, reconcile_checkout, submit_order
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_prompt105a_payments import approved
from tests.test_storefront import _next_wednesday, _product


def _named(db: Session, name: str, price: int, *, weight: int = 500, units: int = 1) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name=f"Massa {name}")
    product = Product(
        name=name,
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
        display_name=f"{weight} g",
        presentation_type="weight",
        net_weight_grams=weight,
        physical_units=units,
        price_cents=price,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _second_variant(db: Session, product: Product, price: int, weight: int) -> ProductVariant:
    variant = ProductVariant(
        product_id=product.id,
        display_name=f"{weight} g",
        presentation_type="weight",
        net_weight_grams=weight,
        physical_units=1,
        price_cents=price,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _send(db: Session, items: list[dict], quoted: int, key: str, **extra) -> Order:
    payload = {
        "requested_date": _next_wednesday(),
        "items": items,
        "quoted_cents": quoted,
        "customer_name": extra.pop("customer_name", "Cliente Jornada"),
        "customer_email": extra.pop("customer_email", "jornada@example.com"),
        "idempotency_key": key,
        **NEW_ORDER_ADDRESS,
        **extra,
    }
    order, _token = submit_order(db, get_settings(), payload)
    return order


def _lines(db: Session, order: Order) -> list[OrderItem]:
    return list(db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))


def test_c01_joint_purchase_is_one_order_one_payment(db: Session) -> None:
    first = _named(db, "Pão A", 2490)
    second = _named(db, "Pão B", 2490)
    order = _send(
        db,
        [
            {"variant_id": str(first.id), "quantity": 1},
            {"variant_id": str(second.id), "quantity": 2},
        ],
        7470,
        "c01-joint",
    )
    items = _lines(db, order)
    assert db.query(Order).count() == 1
    assert len(items) == 2
    assert sum(item.quantity for item in items) == 3
    assert order.total_cents == 7470
    records = db.query(PaymentRecord).filter_by(order_id=order.id).all()
    assert len(records) == 1
    assert records[0].expected_cents == 7470
    assert order.production_started_at is None


def test_c02_distinct_variants_stay_separate(db: Session) -> None:
    light = _named(db, "Pão único", 2490, weight=500)
    heavy = _second_variant(db, db.get(Product, light.product_id), 4800, 1000)
    order = _send(
        db,
        [
            {"variant_id": str(light.id), "quantity": 1},
            {"variant_id": str(heavy.id), "quantity": 1},
        ],
        7290,
        "c02-variants",
    )
    items = _lines(db, order)
    assert len(items) == 2
    weights = {item.net_weight_grams for item in items}
    prices = {item.unit_price_cents for item in items}
    assert weights == {500, 1000}
    assert prices == {2490, 4800}
    assert order.total_cents == 7290


def test_c03_server_receives_the_edited_cart(db: Session) -> None:
    kept = _named(db, "Pão que fica", 2490)
    removed = _named(db, "Pão removido", 3100)
    draft = {
        "requested_date": _next_wednesday(),
        "items": [
            {"variant_id": str(kept.id), "quantity": 1},
            {"variant_id": str(removed.id), "quantity": 1},
        ],
    }
    before = quote_lines(db, get_settings(), draft)
    final_items = [{"variant_id": str(kept.id), "quantity": 3}]
    after = quote_lines(db, get_settings(), {**draft, "items": final_items})
    assert before["total_cents"] == 5590
    assert after["total_cents"] == 7470
    order = _send(db, final_items, after["total_cents"], "c03-edited")
    items = _lines(db, order)
    assert len(items) == 1
    assert items[0].quantity == 3
    assert items[0].dough_name_snapshot == "Pão que fica"
    assert order.total_cents == 7470


def test_c04_manual_accept_releases_one_payment_for_the_set(db: Session) -> None:
    plain = _named(db, "Pão comum", 2490)
    reviewed = _named(db, "Pão com nota", 2490)
    order = _send(
        db,
        [
            {"variant_id": str(plain.id), "quantity": 1},
            {
                "variant_id": str(reviewed.id),
                "quantity": 2,
                "adaptation": {"text": "sem sementes", "reason": "preference"},
            },
        ],
        7470,
        "c04-review",
    )
    assert order.status == "submitted"
    assert order.holds_capacity is False
    view = public_order_view(db, order)
    assert view["payment_available"] is False
    assert "aceite" in (view["payment_unavailable_reason"] or "").lower()
    confirm_order(db, order.id, actor_ref="admin:jornada")
    db.refresh(order)
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.production_started_at is None
    view = public_order_view(db, order)
    assert view["payment_available"] is True
    assert view["total_cents"] == 7470
    assert sum(item["quantity"] for item in view["items"]) == 3
    accepted = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert "Pão comum" in accepted.body
    assert "2×" in accepted.body
    assert order.public_reference in accepted.body
    assert db.query(PaymentRecord).filter_by(order_id=order.id).count() == 1


def test_c05_regular_set_auto_accepts_once(db: Session) -> None:
    first = _named(db, "Pão regular A", 2000)
    second = _named(db, "Pão regular B", 1500)
    order = _send(
        db,
        [
            {"variant_id": str(first.id), "quantity": 1},
            {"variant_id": str(second.id), "quantity": 1},
        ],
        3500,
        "c05-auto",
    )
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.production_started_at is None
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    assert record.expected_cents == 3500
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1
    admin = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_auto_accepted_admin").one()
    assert "Pão regular A" in admin.body
    assert "Pão regular B" in admin.body
    assert "R$ 35,00" in admin.body


def test_c06_incompatible_date_or_quantity_keeps_the_cart(db: Session) -> None:
    bread = _named(db, "Pão da data", 2490)
    past = (bakery_today(get_settings()) - timedelta(days=2)).isoformat()
    payload = {
        "requested_date": past,
        "items": [{"variant_id": str(bread.id), "quantity": 1}],
        "quoted_cents": 2490,
        "customer_name": "Cliente Jornada",
        "customer_email": "jornada@example.com",
        "idempotency_key": "c06-past",
        **NEW_ORDER_ADDRESS,
    }
    with pytest.raises(CapacityError, match="Pão da data") as past_error:
        submit_order(db, get_settings(), payload)
    assert "nenhum pedido foi criado" in str(past_error.value)
    assert db.query(Order).count() == 0

    settings_row = ensure_schedule_settings(db)
    settings_row.daily_physical_limit = 1
    db.flush()
    too_many = {
        **payload,
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(bread.id), "quantity": 2}],
        "quoted_cents": 4980,
        "idempotency_key": "c06-qty",
    }
    with pytest.raises(CapacityError, match="Pão da data"):
        submit_order(db, get_settings(), too_many)
    assert db.query(Order).count() == 0
    quote = quote_lines(
        db,
        get_settings(),
        {"requested_date": _next_wednesday(), "items": [{"variant_id": str(bread.id), "quantity": 1}]},
    )
    kept = _send(db, [{"variant_id": str(bread.id), "quantity": 1}], quote["total_cents"], "c06-kept")
    assert kept.total_cents == 2490
    assert _lines(db, kept)[0].quantity == 1


def test_c07_repeat_submit_returns_the_same_order(db: Session) -> None:
    bread = _product(db)
    payload = {
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(bread.id), "quantity": 2}],
        "quoted_cents": 4980,
        "customer_name": "Cliente Jornada",
        "customer_email": "jornada@example.com",
        "idempotency_key": "c07-repeat",
        **NEW_ORDER_ADDRESS,
    }
    first, _ = submit_order(db, get_settings(), payload)
    second, _ = submit_order(db, get_settings(), payload)
    assert first.id == second.id
    assert db.query(Order).count() == 1
    assert db.query(PaymentRecord).count() == 1
    assert first.holds_capacity is True


def test_c08_intentional_second_purchase_stays_independent(db: Session, monkeypatch) -> None:
    bread = _named(db, "Pão repetido", 2490)
    items = [{"variant_id": str(bread.id), "quantity": 1}]
    first = _send(db, items, 2490, "c08-first", customer_email="mesmo@example.com")
    second = _send(db, items, 2490, "c08-second", customer_email="mesmo@example.com")
    assert first.id != second.id
    assert first.total_cents == second.total_cents == 2490
    record = db.query(PaymentRecord).filter_by(order_id=first.id).one()
    record.idempotency_key = str(uuid4())
    record.external_reference = str(uuid4())
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: approved(first, record),
    )
    reconcile_checkout(db, get_settings(), first)
    other = db.query(PaymentRecord).filter_by(order_id=second.id).one()
    assert record.financial_status == "paid"
    assert other.financial_status == "pending"
    assert other.order_id != record.order_id


def test_c09_interrupted_return_recovers_the_same_charge(db: Session, monkeypatch) -> None:
    first = _named(db, "Pão conjunto A", 2490)
    second = _named(db, "Pão conjunto B", 2490)
    order = _send(
        db,
        [
            {"variant_id": str(first.id), "quantity": 1},
            {"variant_id": str(second.id), "quantity": 2},
        ],
        7470,
        "c09-recover",
    )
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.idempotency_key = str(uuid4())
    record.external_reference = str(uuid4())
    calls = {"n": 0}

    def lookup(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("retorno interrompido")
        return approved(order, record)

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup)
    with pytest.raises(TimeoutError):
        reconcile_checkout(db, get_settings(), order)
    assert record.financial_status == "pending"
    reconcile_checkout(db, get_settings(), order)
    assert record.financial_status == "paid"
    assert record.amount_paid_cents == 7470
    assert db.query(PaymentRecord).count() == 1
    assert order.status == "confirmed"
    assert order.production_started_at is None


def test_c10_paid_order_does_not_invite_another_payment(db: Session, monkeypatch) -> None:
    bread = _named(db, "Pão quitado", 2490)
    order = _send(db, [{"variant_id": str(bread.id), "quantity": 1}], 2490, "c10-paid")
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.idempotency_key = str(uuid4())
    record.external_reference = str(uuid4())
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: approved(order, record),
    )
    reconcile_checkout(db, get_settings(), order)
    view = public_order_view(db, order)
    assert view["financially_settled"] is True
    assert view["payment_available"] is False
    assert "pagamento foi recebido" in view["notice"].lower()
    paid = db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").one()
    assert "Pão quitado" in paid.body
    assert order.public_reference in paid.body
    assert "não inicia a produção" in paid.body


def test_c11_server_refuses_a_tampered_total(db: Session) -> None:
    bread = _named(db, "Pão tabelado", 2490)
    payload = {
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(bread.id), "quantity": 2}],
        "quoted_cents": 100,
        "customer_name": "Cliente Jornada",
        "customer_email": "jornada@example.com",
        "idempotency_key": "c11-tamper",
        **NEW_ORDER_ADDRESS,
    }
    with pytest.raises(PriceChangedError):
        submit_order(db, get_settings(), payload)
    assert db.query(Order).count() == 0
    quote = quote_lines(
        db,
        get_settings(),
        {"requested_date": payload["requested_date"], "items": payload["items"]},
    )
    assert quote["total_cents"] == 4980
    assert quote["discount_cents"] == 0
    order = _send(db, payload["items"], quote["total_cents"], "c11-valid")
    assert order.total_cents == 4980
    assert order.delivery_fee_cents == 0


def test_c12_same_reference_items_and_total_across_surfaces(db: Session, monkeypatch) -> None:
    first = _named(db, "Pão vitrine", 2490)
    second = _named(db, "Pão da casa", 1800)
    order = _send(
        db,
        [
            {"variant_id": str(first.id), "quantity": 1},
            {"variant_id": str(second.id), "quantity": 2},
        ],
        6090,
        "c12-surfaces",
    )
    view = public_order_view(db, order)
    names = {item["product_name"] for item in view["items"]}
    assert names == {"Pão vitrine", "Pão da casa"}
    assert sum(item["quantity"] for item in view["items"]) == 3
    assert view["total_cents"] == 6090
    accepted = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    admin = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_auto_accepted_admin").one()
    summary = order_summary(db, get_settings(), order, "Pedido aceito")
    for text in (accepted.body, admin.body, summary):
        assert order.public_reference in text
        assert "Pão vitrine" in text
        assert "Pão da casa" in text
    assert "R$ 60,90" in accepted.body
    assert "R$ 60,90" in admin.body
    assert order.holds_capacity is True
    assert db.query(Order).count() == 1
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    record.idempotency_key = str(uuid4())
    record.external_reference = str(uuid4())
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *args, **kwargs: approved(order, record),
    )
    reconcile_checkout(db, get_settings(), order)
    paid = db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").one()
    assert "Pão vitrine" in paid.body
    assert "2×" in paid.body
    assert "R$ 60,90" in paid.body
    assert order.public_reference in paid.body
    assert db.query(PaymentRecord).filter_by(order_id=order.id).count() == 1
