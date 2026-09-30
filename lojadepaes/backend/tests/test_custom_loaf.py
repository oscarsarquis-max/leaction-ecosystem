from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.errors import CapacityError, ConfirmationError, PriceChangedError
from app.domain.orders import confirm_order
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.domain.storefront_orders import quote_lines, start_checkout, submit_order
from app.models.catalog import BreadShape, DoughIngredientCompatibility, DoughShapeCompatibility, DoughType, Ingredient
from app.models.enums import AdaptationStatus, OrderStatus
from app.models.orders import OrderItem, OrderItemAdaptation, OrderStatusHistory
from app.models.products import Product, ProductVariant
from app.models.enums import EditorialStatus
from sqlalchemy.orm import Session


def _wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta or 7)
    return day.isoformat()


def _catalog(db: Session, *, base_name: str = "Massa teste") -> dict:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name=base_name)
    dough = DoughType(
        name=base_name,
        slug=f"dough-{uuid4().hex[:8]}",
        short_description="massa de teste",
        sort_order=0,
        is_active=True,
        recipe_base_id=base.id,
        base_price_cents=1200,
    )
    shape = BreadShape(
        name="Cesto",
        slug=f"shape-{uuid4().hex[:8]}",
        description="formato",
        crust_crumb_notes="crosta",
        sort_order=0,
        is_active=True,
    )
    ingredient = Ingredient(
        name="Nozes",
        slug=f"ing-{uuid4().hex[:8]}",
        description="crocância",
        sort_order=0,
        is_active=True,
        surcharge_cents=200,
    )
    flour = Ingredient(
        name="Farinha branca italiana",
        slug=f"farinha-{uuid4().hex[:8]}",
        description="Propriedades ainda pendentes de configuração.",
        sort_order=1,
        is_active=True,
        surcharge_cents=None,
        assistant_role="flour",
    )
    db.add_all([dough, shape, ingredient, flour])
    db.flush()
    db.add_all(
        [
            DoughShapeCompatibility(dough_type_id=dough.id, bread_shape_id=shape.id),
            DoughIngredientCompatibility(dough_type_id=dough.id, ingredient_id=ingredient.id),
        ]
    )
    db.flush()
    settings = ensure_schedule_settings(db)
    return {"dough": dough, "shape": shape, "ingredient": ingredient, "flour": flour, "settings": settings, "base": base}


def _payload(catalog: dict, **overrides) -> dict:
    item = {
        "dough_type_id": str(catalog["dough"].id),
        "bread_shape_id": str(catalog["shape"].id),
        "ingredient_ids": [str(catalog["ingredient"].id)],
        "free_ingredient_text": "pepperoni",
        "quantity": 2,
        "unit_cents": 7000,
        "weight_grams": 500,
    }
    item.update(overrides.pop("item", {}))
    body = {
        "requested_date": _wednesday(),
        "items": [item],
        "quoted_cents": 14000,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "idempotency_key": f"custom-{uuid4().hex[:8]}",
    }
    body.update(overrides)
    return body


def test_assistant_dough_and_shape_are_ready(db: Session) -> None:
    from app.domain.custom_loaf import public_builder_catalog
    from app.models.catalog import DoughType, Ingredient

    catalog = public_builder_catalog(db)
    names = {item["name"] for item in catalog["doughs"]}
    assert names == {
        "Fermentação natural curta (Classic sourdough)",
        "Maturada (Long fermentation)",
        "Sovada (Kneaded dough)",
    }
    assert "Sourdough clássico" not in names
    assert "Integral" not in names
    assert "Multigrãos" not in names
    shapes = {item["name"] for item in catalog["shapes"]}
    assert {"Rústico de cesto", "Pão de forma"} <= shapes
    assert all(not item["recipe_base_pending"] for item in catalog["doughs"])
    italian = db.query(Ingredient).filter_by(slug="farinha-branca-italiana").one()
    assert italian.is_active is False
    assert italian.name == "Farinha branca italiana"


def test_catalog_splits_flour_from_inclusions(db: Session) -> None:
    from app.domain.custom_loaf import public_builder_catalog

    catalog = public_builder_catalog(db)
    flour_names = {item["name"] for item in catalog["flours"]}
    extra_names = {item["name"] for item in catalog["ingredients"]}
    assert flour_names == {
        "Branca (Strong white)",
        "Integral de trigo (Whole wheat)",
        "Integral de centeio (Whole rye)",
        "Fubá (Corn)",
    }
    assert "Farinha branca italiana" not in flour_names
    assert "Farinha branca italiana" not in extra_names
    assert {
        "Nozes",
        "Castanha de caju",
        "Granola",
        "Tomate seco",
        "Berinjela",
        "Queijo parmesão",
    } <= extra_names
    assert all(item["assistant_role"] == "flour" for item in catalog["flours"])
    assert all(item["assistant_role"] == "inclusion" for item in catalog["ingredients"])
    assert "24h" not in " ".join(item["description"] for item in catalog["doughs"])
    assert "glúten" not in " ".join(item["description"] for item in catalog["flours"]).lower()


def test_submit_keeps_flour_separate_from_inclusions(db: Session, monkeypatch) -> None:
    from app.domain.admin_orders import get_order_detail
    from app.domain.custom_loaf import public_builder_catalog
    from app.models.orders import OrderItemIngredient

    catalog = public_builder_catalog(db)
    dough = next(item for item in catalog["doughs"] if item["name"].startswith("Maturada"))
    shape = next(item for item in catalog["shapes"] if item["name"] == "Pão de forma")
    flour = next(item for item in catalog["flours"] if item["name"].startswith("Branca"))
    extras = [item for item in catalog["ingredients"] if item["name"] in {"Nozes", "Granola"}]
    inclusion_names = {item["name"] for item in extras}
    payload = {
        "requested_date": _wednesday(),
        "items": [
            {
                "dough_type_id": dough["id"],
                "bread_shape_id": shape["id"],
                "ingredient_ids": [flour["id"], extras[0]["id"], extras[1]["id"]],
                "free_ingredient_text": "pepperoni",
                "quantity": 1,
                "unit_cents": 7000,
                "weight_grams": 500,
            }
        ],
        "quoted_cents": 7000,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "idempotency_key": f"flour-{uuid4().hex[:8]}",
    }
    quote = quote_lines(db, get_settings(), payload)
    assert quote["total_cents"] == 7000
    roles = {item["assistant_role"] for item in quote["items"][0]["ingredients"]}
    assert roles == {"flour", "inclusion"}
    order, _ = submit_order(db, get_settings(), payload)
    rows = db.query(OrderItemIngredient).join(OrderItem).filter(OrderItem.order_id == order.id).all()
    names = {row.name_snapshot for row in rows}
    assert names == {flour["name"], extras[0]["name"], extras[1]["name"]}
    persisted = {db.get(Ingredient, row.ingredient_id).assistant_role for row in rows}
    assert persisted == {"flour", "inclusion"}
    detail = get_order_detail(db, order.id)
    admin_extras = detail.items[0].extras
    assert {extra.name for extra in admin_extras if extra.assistant_role == "flour"} == {flour["name"]}
    assert detail.items[0].dough_name == dough["name"]
    assert {extra.name for extra in admin_extras if extra.assistant_role == "inclusion"} == inclusion_names
    adaptations = [item.adaptation for item in detail.items if item.adaptation]
    assert len(adaptations) == 1
    assert adaptations[0]["status"] == AdaptationStatus.PENDING.value
    with pytest.raises(ConfirmationError, match="aceite"):
        start_checkout(db, get_settings(), order, "pix")
    confirm_order(db, order.id, actor_ref="padaria")
    db.refresh(order)
    assert order.holds_capacity is True
    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-flour",
            status="PENDING",
            checkout_url="https://checkout.example/pix",
            amount_cents=7000,
            reused=False,
            method=kwargs.get("method", "pix"),
        ),
    )
    monkeypatch.setattr("app.domain.storefront_orders.cancel_amount_checkout", lambda *_a, **_k: None)
    checkout = start_checkout(db, get_settings(), order, "pix")
    assert checkout["expected_cents"] == 7000
    db.refresh(order)
    assert order.status == OrderStatus.CONFIRMED.value


def test_custom_loaf_quotes_fixed_price_without_addons(db: Session) -> None:
    catalog = _catalog(db)
    quote = quote_lines(db, get_settings(), _payload(catalog))
    assert quote["total_cents"] == 14000
    assert quote["items"][0]["unit_cents"] == 7000
    assert quote["items"][0]["weight_grams"] == 500
    assert quote["items"][0]["physical_units"] == 2
    assert quote["items"][0]["ingredients"][0]["surcharge_cents"] is None


def test_browser_price_is_rejected(db: Session) -> None:
    catalog = _catalog(db)
    with pytest.raises(PriceChangedError):
        quote_lines(db, get_settings(), _payload(catalog, item={"unit_cents": 1}, quoted_cents=2))


def test_italian_flour_without_link_does_not_charge(db: Session) -> None:
    catalog = _catalog(db)
    quote = quote_lines(
        db,
        get_settings(),
        _payload(catalog, item={"quantity": 1, "ingredient_ids": [str(catalog["flour"].id)]}, quoted_cents=7000),
    )
    assert quote["total_cents"] == 7000
    assert quote["items"][0]["ingredients"][0]["surcharge_cents"] is None


def test_submit_keeps_distinct_free_text_and_blocks_payment_until_accept(db: Session, monkeypatch) -> None:
    catalog = _catalog(db)
    first = _payload(catalog, quoted_cents=7000, item={"quantity": 1, "free_ingredient_text": "pepperoni"})
    second_item = {
        "dough_type_id": str(catalog["dough"].id),
        "bread_shape_id": str(catalog["shape"].id),
        "quantity": 1,
        "free_ingredient_text": "tomate seco",
        "unit_cents": 7000,
        "weight_grams": 500,
    }
    first["items"].append(second_item)
    first["quoted_cents"] = 14000
    order, _token = submit_order(db, get_settings(), first)
    db.flush()
    assert order.status == OrderStatus.SUBMITTED.value
    assert order.holds_capacity is False
    assert order.total_cents == 14000
    items = db.query(OrderItem).filter_by(order_id=order.id).all()
    assert len(items) == 2
    assert {item.net_weight_grams for item in items} == {500}
    texts = {row.customer_text for row in db.query(OrderItemAdaptation).all()}
    assert texts == {"pepperoni", "tomate seco"}
    assert all(row.reason == "preference" for row in db.query(OrderItemAdaptation).all())
    with pytest.raises(ConfirmationError, match="aceite"):
        start_checkout(db, get_settings(), order, "pix")

    catalog["settings"].custom_loaf_price_cents = 9000
    db.flush()
    db.refresh(order)
    assert order.total_cents == 14000

    confirm_order(db, order.id, actor_ref="padaria")
    confirm_order(db, order.id, actor_ref="padaria")
    assert order.status == OrderStatus.CONFIRMED.value
    assert order.holds_capacity is True
    assert db.query(OrderStatusHistory).filter_by(order_id=order.id).count() == 1
    assert all(row.status == AdaptationStatus.ACCEPTED.value for row in db.query(OrderItemAdaptation).all())

    captured = {}

    def fake_checkout(*_args, **kwargs):
        captured.update(kwargs)
        return HubCheckoutResult(
            order_id=f"hub-custom-{kwargs.get('method', 'pix')}",
            status="PENDING",
            checkout_url="https://checkout.example/card",
            amount_cents=order.total_cents or 0,
            reused=False,
            method=kwargs.get("method", "pix"),
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    monkeypatch.setattr("app.domain.storefront_orders.cancel_amount_checkout", lambda *_a, **_k: None)
    pix = start_checkout(db, get_settings(), order, "pix")
    card = start_checkout(db, get_settings(), order, "card", replace=True)
    assert pix["expected_cents"] == 14000
    assert card["method"] == "card"
    assert "pepperoni" not in captured["description"]
    assert order.holds_capacity is True
    assert order.status == OrderStatus.CONFIRMED.value


def test_capacity_failure_does_not_partially_accept(db: Session) -> None:
    first = _catalog(db, base_name="Base um")
    second_base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Base dois")
    other = DoughType(
        name="Base dois",
        slug=f"dough-{uuid4().hex[:8]}",
        short_description="outra",
        sort_order=1,
        is_active=True,
        recipe_base_id=second_base.id,
    )
    db.add(other)
    db.flush()
    db.add(DoughShapeCompatibility(dough_type_id=other.id, bread_shape_id=first["shape"].id))
    db.flush()
    first["settings"].daily_base_limit = 5
    db.flush()
    order_a, _ = submit_order(db, get_settings(), _payload(first, item={"quantity": 1}, quoted_cents=7000))
    payload_b = _payload(
        first,
        item={"quantity": 1, "dough_type_id": str(other.id), "ingredient_ids": []},
        quoted_cents=7000,
    )
    order_b, _ = submit_order(db, get_settings(), payload_b)
    first["settings"].daily_base_limit = 1
    db.flush()
    confirm_order(db, order_a.id)
    nested = db.begin_nested()
    try:
        confirm_order(db, order_b.id)
        raise AssertionError("a reserva deveria falhar")
    except CapacityError:
        nested.rollback()
    db.expire_all()
    assert order_b.status == OrderStatus.SUBMITTED.value
    assert order_b.holds_capacity is False
    pending = db.query(OrderItemAdaptation).join(OrderItem).filter(OrderItem.order_id == order_b.id).one()
    assert pending.status == AdaptationStatus.PENDING.value


def test_mixed_cart_waits_for_accept(db: Session) -> None:
    catalog = _catalog(db)
    product = Product(
        name="Pão da vitrine",
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="vitrine",
        recipe_base_id=catalog["base"].id,
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
    payload = _payload(catalog, item={"quantity": 1}, quoted_cents=9490)
    payload["items"].append({"variant_id": str(variant.id), "quantity": 1})
    order, _ = submit_order(db, get_settings(), payload)
    assert order.total_cents == 9490
    with pytest.raises(ConfirmationError, match="aceite"):
        start_checkout(db, get_settings(), order, "pix")


def test_same_submit_key_does_not_duplicate(db: Session) -> None:
    catalog = _catalog(db)
    payload = _payload(catalog, item={"quantity": 1}, quoted_cents=7000)
    first, _ = submit_order(db, get_settings(), payload)
    second, _ = submit_order(db, get_settings(), payload)
    assert first.id == second.id


def test_dietary_restriction_still_blocks_accept(db: Session) -> None:
    catalog = _catalog(db)
    payload = _payload(
        catalog,
        item={
            "quantity": 1,
            "free_ingredient_text": None,
            "adaptation_text": "sem glúten",
            "adaptation_reason": "dietary_restriction",
        },
        quoted_cents=7000,
    )
    order, _ = submit_order(db, get_settings(), payload)
    with pytest.raises(ConfirmationError):
        confirm_order(db, order.id)
    db.refresh(order)
    assert order.status == OrderStatus.SUBMITTED.value
    assert order.holds_capacity is False


def test_retired_mass_asks_only_preparation_review(db: Session) -> None:
    from app.domain.custom_loaf import PREP_REVIEW_MESSAGE, public_builder_catalog

    leftover = DoughType(
        name="Integral",
        slug="integral",
        short_description="registro histórico",
        sort_order=9,
        is_active=True,
        recipe_base_id=create_recipe_base(db, code=f"old-{uuid4().hex[:6]}", name="Integral").id,
    )
    db.add(leftover)
    db.flush()
    public_builder_catalog(db)
    db.refresh(leftover)
    assert leftover.creator_kind == "retired_mass"
    assert leftover.is_active is False
    catalog = _catalog(db)
    with pytest.raises(ConfirmationError, match="fermentação e o preparo"):
        quote_lines(
            db,
            get_settings(),
            _payload(
                catalog,
                item={
                    "dough_type_id": str(leftover.id),
                    "ingredient_ids": [str(catalog["flour"].id), str(catalog["ingredient"].id)],
                },
            ),
        )
    assert "farinha" in PREP_REVIEW_MESSAGE


def test_inactive_italian_flour_asks_only_flour_review(db: Session) -> None:
    from app.domain.custom_loaf import FLOUR_REVIEW_MESSAGE, public_builder_catalog

    catalog = public_builder_catalog(db)
    dough = next(item for item in catalog["doughs"] if item["name"].startswith("Sovada"))
    shape = next(item for item in catalog["shapes"] if item["name"] == "Pão de forma")
    italian = db.query(Ingredient).filter_by(slug="farinha-branca-italiana").one()
    with pytest.raises(ConfirmationError, match="farinha desta seleção"):
        quote_lines(
            db,
            get_settings(),
            {
                "requested_date": _wednesday(),
                "items": [
                    {
                        "dough_type_id": dough["id"],
                        "bread_shape_id": shape["id"],
                        "ingredient_ids": [str(italian.id)],
                        "quantity": 1,
                        "unit_cents": 7000,
                        "weight_grams": 500,
                    }
                ],
            },
        )
    assert "preparo" in FLOUR_REVIEW_MESSAGE


def test_previous_order_keeps_original_mass_snapshot(db: Session) -> None:
    catalog = _catalog(db)
    catalog["dough"].name = "Integral"
    db.flush()
    order, _ = submit_order(db, get_settings(), _payload(catalog, item={"quantity": 1}, quoted_cents=7000))
    item = db.query(OrderItem).filter_by(order_id=order.id).one()
    assert item.dough_name_snapshot == "Integral"
