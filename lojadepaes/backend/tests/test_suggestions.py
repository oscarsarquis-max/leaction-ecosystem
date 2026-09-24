from datetime import date
from uuid import uuid4

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.orders import new_public_reference
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import save_date_override
from app.domain.suggestions import suggest_fornada
from app.models.catalog import BreadShape, DoughType
from app.models.enums import EditorialStatus
from app.models.orders import Order, OrderItem
from app.models.products import Product, ProductVariant
from app.schemas.suggestions import SuggestionsQuery
from sqlalchemy.orm import Session
from tests.test_schedule import _next_iso


def _today() -> date:
    return bakery_today(get_settings())


def _base(session: Session, name: str):
    return create_recipe_base(session, code=name, name=name)


def _product(session: Session, base, name: str, sort_order: int = 0, units: int = 1) -> Product:
    product = Product(
        name=name,
        slug=f"p-{uuid4().hex[:10]}",
        short_description="Pão de teste.",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
        recipe_base_id=base.id,
        sort_order=sort_order,
        featured_image_alt="Pão de teste",
    )
    session.add(product)
    session.flush()
    session.add(
        ProductVariant(
            product_id=product.id,
            display_name="500 g",
            presentation_type="weight",
            net_weight_grams=500,
            price_cents=2490,
            is_active=True,
            physical_units=units,
            sort_order=0,
        )
    )
    session.flush()
    session.refresh(product)
    return product


def _hold(session: Session, local_date: date, base, quantity: int = 1) -> None:
    dough = DoughType(
        name=base.name,
        slug=f"d-{uuid4().hex[:8]}",
        short_description="teste",
        is_active=True,
        recipe_base_id=base.id,
    )
    shape = BreadShape(
        name="Formato",
        slug=f"s-{uuid4().hex[:8]}",
        description="teste",
        crust_crumb_notes="crosta",
        is_active=True,
    )
    session.add_all([dough, shape])
    session.flush()
    order = Order(
        public_reference=new_public_reference(),
        status="confirmed",
        fulfillment_modality="pickup",
        production_local_date=local_date,
        customer_name="Teste",
        currency="BRL",
        holds_capacity=True,
    )
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.id,
            dough_type_id=dough.id,
            bread_shape_id=shape.id,
            recipe_base_id=base.id,
            quantity=quantity,
            physical_units=quantity,
            dough_name_snapshot=base.name,
            shape_name_snapshot="Formato",
            unit_price_cents=1000,
            line_total_cents=1000 * quantity,
        )
    )
    session.flush()


def test_new_base_suggested_and_sixth_blocked(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    occupied = [_base(db, f"base-{index}") for index in range(5)]
    extra = _base(db, "base-nova")
    for base in occupied[:4]:
        _hold(db, target, base)
    _product(db, extra, "Pão novo", sort_order=1)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.message is not None
    assert "1 tipo diferente" in result.message
    assert "Pão novo" not in result.message
    _hold(db, target, occupied[4])
    blocked = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert blocked.items == []
    assert blocked.message is not None
    assert "sem vaga para um tipo novo" in blocked.message


def test_date_exception_raises_base_limit(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(6)
    occupied = [_base(db, f"lim-{index}") for index in range(5)]
    extra = _base(db, "lim-nova")
    for base in occupied:
        _hold(db, target, base)
    _product(db, extra, "Pão da exceção", sort_order=1)
    before = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert before.items == []
    assert before.message is not None
    assert "sem vaga para um tipo novo" in before.message
    save_date_override(
        db,
        settings,
        local_date=target,
        open_state="inherit",
        daily_physical_limit=None,
        daily_base_limit=6,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    after = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert after.items == []
    assert after.message is not None
    assert "1 tipo diferente" in after.message
    assert "Pão da exceção" not in after.message


def test_physical_remaining_blocks_suggestion(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "fisica")
    other = _base(db, "outra")
    _hold(db, target, base, quantity=15)
    _product(db, other, "Pão pesado", units=1)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.message is not None
    assert "Não há vaga nesta fornada" in result.message


def test_same_base_inclusions_do_not_create_second_type(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "mesma")
    _product(db, base, "Pão A", sort_order=1)
    _product(db, base, "Pão B", sort_order=2)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.message is not None
    assert "vaga para" in result.message
    assert "Pão A" not in result.message
    assert "Pão B" not in result.message


def test_cart_bases_and_individual_alternatives(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(6)
    occupied = [_base(db, f"cart-{index}") for index in range(4)]
    for base in occupied:
        _hold(db, target, base)
    first_new = _base(db, "cart-a")
    second_new = _base(db, "cart-b")
    pao_a = _product(db, first_new, "Alternativa A", sort_order=1)
    _product(db, second_new, "Alternativa B", sort_order=2)
    empty = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert empty.items == []
    assert empty.message is not None
    assert "1 tipo diferente" in empty.message
    variant_a = next(iter(pao_a.variants))
    with_cart = suggest_fornada(
        db,
        settings,
        SuggestionsQuery(
            selected=target,
            lines=[{"kind": "product", "quantity": 1, "variant_id": variant_a.id}],
        ),
    )
    assert with_cart.items == []
    assert with_cart.message is not None
    assert "vaga para" in with_cart.message
    assert "Alternativa B" not in with_cart.message


def test_submitted_order_does_not_count_as_spare_capacity(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "pendente")
    dough = DoughType(
        name=base.name,
        slug=f"d-{uuid4().hex[:8]}",
        short_description="teste",
        is_active=True,
        recipe_base_id=base.id,
    )
    shape = BreadShape(
        name="Formato",
        slug=f"s-{uuid4().hex[:8]}",
        description="teste",
        crust_crumb_notes="crosta",
        is_active=True,
    )
    db.add_all([dough, shape])
    db.flush()
    order = Order(
        public_reference=new_public_reference(),
        status="submitted",
        fulfillment_modality="pickup",
        production_local_date=target,
        customer_name="Teste",
        currency="BRL",
        holds_capacity=False,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            dough_type_id=dough.id,
            bread_shape_id=shape.id,
            recipe_base_id=base.id,
            quantity=1,
            physical_units=1,
            dough_name_snapshot=base.name,
            shape_name_snapshot="Formato",
            unit_price_cents=1000,
            line_total_cents=1000,
        )
    )
    db.flush()
    from app.domain.schedule import evaluate_day, preview_calendar

    formal = evaluate_day(db, settings, target, [])
    assert formal.committed_physical == 0
    assert formal.remaining_physical == formal.daily_physical_limit
    preview = preview_calendar(db, settings, start=target, end=target, selected=target)
    assert preview.days[0].awaiting_review is True
    assert preview.days[0].committed_physical == 0
    assert preview.review_message is not None
    assert "pagamento não reserva" in preview.review_message.lower()
    _product(db, base, "Mais do mesmo", sort_order=1)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.title == "Vagas nesta fornada"
    assert result.message is not None
    assert f"vaga para {formal.daily_physical_limit} pães" in result.message
    assert "não está garantida" in result.message
    assert "Mais do mesmo" not in result.message


def test_pack_larger_than_remaining_is_not_offered(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "pacote")
    _hold(db, target, base, quantity=14)
    _product(db, base, "Pacote de seis", units=6)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.message is not None
    assert "vaga para 1 pão" in result.message
    assert "Pacote de seis" not in result.message


def test_cart_over_capacity_does_not_promise_room(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "excede")
    product = _product(db, base, "Pão único")
    variant = next(iter(product.variants))
    result = suggest_fornada(
        db,
        settings,
        SuggestionsQuery(
            selected=target,
            lines=[{"kind": "product", "quantity": 20, "variant_id": variant.id}],
        ),
    )
    assert result.items == []
    assert result.message is not None
    assert "Esta seleção não cabe" in result.message
    assert "vaga para" in result.message


def test_fallback_already_programmed(db: Session) -> None:
    settings = get_settings()
    target = _next_iso(3)
    base = _base(db, "ja-la")
    _hold(db, target, base, quantity=1)
    _product(db, base, "Mais do mesmo", sort_order=1)
    result = suggest_fornada(db, settings, SuggestionsQuery(selected=target))
    assert result.items == []
    assert result.title == "Vagas nesta fornada"
    assert result.message is not None
    assert "vaga para 14 pães" in result.message
    assert "Mais do mesmo" not in result.message
