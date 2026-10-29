from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.custom_loaf import public_builder_catalog
from app.domain.date_requests import create_date_request
from app.domain.errors import ConfirmationError
from app.domain.gigio.rules import PROCESS_RULES
from app.domain.orders import new_public_reference, transition_order
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import (
    NEW_ORDER_PICKUP_ERROR,
    quote_lines,
    set_delivery_address,
    submit_order,
)
from app.models.enums import EditorialStatus, OrderStatus
from app.models.orders import Order
from app.models.products import Product, ProductVariant
from app.schemas.suggestions import DateRequestCreateIn
from sqlalchemy.orm import Session
from tests.db_fixtures import NEW_ORDER_ADDRESS


def _next_wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta)
    if day <= today:
        day += timedelta(days=7)
    return day.isoformat()


def _product(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 63")
    product = Product(
        name="Pão 63",
        slug=f"pao-63-{uuid4().hex[:8]}",
        short_description="crosta",
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


def _submit_body(variant: ProductVariant, **overrides) -> dict:
    body = {
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(variant.id), "quantity": 1}],
        "quoted_cents": 2490,
        "customer_name": "Ana",
        "customer_email": "ana63@example.com",
        **NEW_ORDER_ADDRESS,
        "idempotency_key": f"p63-{uuid4().hex[:8]}",
    }
    body.update(overrides)
    return body


def test_catalog_and_gigio_say_delivery_only() -> None:
    assert "somente entregas" in PROCESS_RULES
    assert "não há retirada" in PROCESS_RULES.casefold()
    assert "não invente área atendida" in PROCESS_RULES.casefold()


def test_new_order_is_delivery_and_requires_address(db: Session) -> None:
    variant = _product(db)
    quoted = quote_lines(db, get_settings(), {"requested_date": _next_wednesday(), "items": [{"variant_id": str(variant.id), "quantity": 1}]})
    assert quoted["total_cents"] == 2490
    with pytest.raises(ConfirmationError, match="rua"):
        submit_order(db, get_settings(), _submit_body(variant, delivery_street=""))
    with pytest.raises(ConfirmationError, match=NEW_ORDER_PICKUP_ERROR.split(".")[0]):
        submit_order(db, get_settings(), _submit_body(variant, fulfillment_modality="pickup"))
    order, token = submit_order(
        db,
        get_settings(),
        _submit_body(variant, delivery_number="S/N", delivery_complement="", preferred_time="16:30"),
    )
    assert token
    assert order.fulfillment_modality == "delivery"
    assert order.delivery_number == "S/N"
    assert order.delivery_complement is None
    assert order.preferred_time.hour == 16
    assert order.total_cents == 2490
    again, empty = submit_order(db, get_settings(), _submit_body(variant, idempotency_key=order.submit_idempotency_key))
    assert again.id == order.id
    assert empty == ""
    assert again.total_cents == 2490


def test_alphanumeric_number_and_incomplete_keeps_totals(db: Session) -> None:
    variant = _product(db)
    with pytest.raises(ConfirmationError, match="CEP"):
        submit_order(db, get_settings(), _submit_body(variant, delivery_postal_code="60150"))
    order, _ = submit_order(db, get_settings(), _submit_body(variant, delivery_number="10A"))
    assert order.delivery_number == "10A"
    assert order.fulfillment_modality == "delivery"
    assert order.total_cents == 2490


def test_date_request_does_not_require_address(db: Session) -> None:
    created = create_date_request(
        db,
        get_settings(),
        DateRequestCreateIn(
            desired_date=bakery_today(get_settings()),
            customer_name="Ana",
            customer_email="data63@example.com",
            intended_quantity=2,
            idempotency_key=f"date-63-{uuid4().hex[:8]}",
        ),
        client_host="127.0.0.1",
    )
    assert created.status == "pending"
    assert created.desired_date is not None


def test_historical_pickup_stays_operable_without_address(db: Session) -> None:
    variant = _product(db)
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.READY.value,
        fulfillment_modality="pickup",
        customer_name="Pedido antigo",
        customer_email="antigo@example.test",
        currency="BRL",
        subtotal_cents=2490,
        delivery_fee_cents=0,
        discount_cents=0,
        total_cents=2490,
        holds_capacity=False,
    )
    db.add(order)
    db.flush()
    from app.models.orders import OrderItem

    db.add(
        OrderItem(
            order_id=order.id,
            product_id=variant.product_id,
            product_variant_id=variant.id,
            quantity=1,
            physical_units=1,
            dough_name_snapshot="Pão 63",
            shape_name_snapshot="500 g",
            unit_price_cents=2490,
            line_total_cents=2490,
        )
    )
    db.flush()
    with pytest.raises(ConfirmationError, match="histórico"):
        set_delivery_address(db, get_settings(), order, NEW_ORDER_ADDRESS)
    db.refresh(order)
    assert order.fulfillment_modality == "pickup"
    assert order.delivery_street is None
    completed = transition_order(db, order.id, OrderStatus.COMPLETED.value, actor_ref="admin")
    assert completed.fulfillment_modality == "pickup"
    assert completed.status == OrderStatus.COMPLETED.value
    assert completed.total_cents == 2490


def test_builder_catalog_is_delivery(db: Session) -> None:
    catalog = public_builder_catalog(db)
    assert catalog["fulfillment"] == "delivery"
