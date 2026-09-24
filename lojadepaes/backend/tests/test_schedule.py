from datetime import date, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today, week_monday
from app.domain.errors import ConflictError
from app.domain.orders import new_public_reference
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import (
    ProposedLine,
    delete_date_override,
    delete_week_override,
    evaluate_day,
    preview_calendar,
    resolve_effective_day,
    resolve_proposed_lines,
    save_date_override,
    save_defaults,
    save_week_override,
)
from app.models.catalog import BreadShape, DoughType
from app.models.orders import Order, OrderItem
from app.models.products import Product, ProductVariant
from app.models.schedule import ScheduleSettings
from sqlalchemy.orm import Session


def _today() -> date:
    return bakery_today(get_settings())


def _next_iso(iso_weekday: int, after: date | None = None) -> date:
    start = after or _today()
    delta = (iso_weekday - start.isoweekday()) % 7
    candidate = start + timedelta(days=delta)
    if candidate < _today():
        candidate += timedelta(days=7)
    return candidate


def _base(session: Session, name: str):
    return create_recipe_base(session, code=name, name=name)


def _dough(session: Session, base, name: str | None = None) -> DoughType:
    row = DoughType(
        name=name or base.name,
        slug=f"d-{uuid4().hex[:8]}",
        short_description="teste",
        is_active=True,
        recipe_base_id=base.id,
    )
    session.add(row)
    session.flush()
    return row


def _shape(session: Session) -> BreadShape:
    row = BreadShape(
        name="Formato",
        slug=f"s-{uuid4().hex[:8]}",
        description="teste",
        crust_crumb_notes="crosta",
        is_active=True,
    )
    session.add(row)
    session.flush()
    return row


def _hold(
    session: Session,
    local_date: date,
    dough: DoughType,
    shape: BreadShape,
    quantity: int = 1,
    inclusions: int = 0,
) -> Order:
    del inclusions
    order = Order(
        public_reference=new_public_reference(),
        status="confirmed",
        holds_capacity=True,
        production_local_date=local_date,
        customer_name="Teste",
        currency="BRL",
    )
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.id,
            dough_type_id=dough.id,
            bread_shape_id=shape.id,
            quantity=quantity,
            recipe_base_id=dough.recipe_base_id,
            physical_units=quantity,
        )
    )
    session.flush()
    return order


def test_bootstrap_defaults_are_editable(db: Session) -> None:
    settings = get_settings()
    wednesday = _next_iso(3)
    effective = resolve_effective_day(db, settings, wednesday)
    assert effective.is_open is True
    save_defaults(
        db,
        settings,
        production_weekdays=[2, 5],
        daily_physical_limit=9,
        daily_base_limit=3,
        horizon_days=21,
        min_advance_hours=0,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    changed = resolve_effective_day(db, settings, wednesday)
    assert changed.is_open is False
    friday = _next_iso(5)
    assert resolve_effective_day(db, settings, friday).daily_physical_limit == 9
    assert resolve_effective_day(db, settings, friday).daily_base_limit == 3


def test_same_base_different_inclusions_count_as_one_type(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(3)
    base = _base(db, "levain")
    dough = _dough(db, base)
    shape = _shape(db)
    _hold(db, day, dough, shape, 1)
    _hold(db, day, dough, shape, 1)
    result = evaluate_day(db, settings, day, [])
    assert result.committed_physical == 2
    assert len(result.committed_base_ids) == 1


def test_weight_and_pack_share_base_only_with_explicit_physical(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(6)
    base = _base(db, "branco")
    product = Product(name="Pão", slug=f"p-{uuid4().hex[:8]}", recipe_base_id=base.id)
    db.add(product)
    db.flush()
    loose = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        is_active=True,
    )
    pack = ProductVariant(
        product_id=product.id,
        display_name="Pacote",
        presentation_type="pack",
        units_per_pack=6,
        physical_units=6,
        is_active=True,
    )
    db.add_all([loose, pack])
    db.flush()
    preview = preview_calendar(
        db,
        settings,
        start=day,
        end=day,
        selected=day,
        lines=[
            ProposedLine(kind="product", quantity=1, variant_id=loose.id),
            ProposedLine(kind="product", quantity=1, variant_id=pack.id),
        ],
    )
    chosen = preview.days[0]
    assert chosen.status == "available"
    unnamed = ProductVariant(
        product_id=product.id,
        display_name="Caixa",
        presentation_type="pack",
        units_per_pack=4,
        physical_units=None,
        is_active=True,
        sort_order=2,
    )
    db.add(unnamed)
    db.flush()
    unknown = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(db, [ProposedLine(kind="product", quantity=1, variant_id=unnamed.id)]),
    )
    assert unknown.status == "not_eligible"
    assert unknown.reason == "unknown_units"
    unbound = DoughType(
        name="Sem tipo",
        slug=f"d-{uuid4().hex[:8]}",
        short_description="teste",
        is_active=True,
        recipe_base_id=None,
    )
    db.add(unbound)
    db.flush()
    missing_base = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(
            db, [ProposedLine(kind="custom", quantity=1, dough_type_id=unbound.id)]
        ),
    )
    assert missing_base.eligible_for_selection is False
    assert missing_base.reason == "unknown_base"


def test_standard_and_custom_share_base(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(3)
    base = _base(db, "comum")
    dough = _dough(db, base)
    product = Product(name="Casa", slug=f"c-{uuid4().hex[:8]}", recipe_base_id=base.id)
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        is_active=True,
    )
    db.add(variant)
    db.flush()
    resolved = resolve_proposed_lines(
        db,
        [
            ProposedLine(kind="custom", quantity=1, dough_type_id=dough.id),
            ProposedLine(kind="product", quantity=2, variant_id=variant.id),
        ],
    )
    result = evaluate_day(db, settings, day, resolved)
    assert result.status == "available"
    assert result.reason == "none"


def test_sixth_base_blocked_until_limit_is_raised(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(3)
    shape = _shape(db)
    doughs = []
    for index in range(5):
        base = _base(db, f"base{index}")
        doughs.append(_dough(db, base, f"massa{index}"))
        _hold(db, day, doughs[-1], shape, 1)
    extra = _dough(db, _base(db, "sexta"), "sexta")
    blocked = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(db, [ProposedLine(kind="custom", quantity=1, dough_type_id=extra.id)]),
    )
    assert blocked.status == "new_base_blocked"
    more_of_same = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(db, [ProposedLine(kind="custom", quantity=1, dough_type_id=doughs[0].id)]),
    )
    assert more_of_same.status == "available"
    save_week_override(
        db,
        settings,
        week_monday(day),
        production_weekdays=None,
        daily_physical_limit=None,
        daily_base_limit=6,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    allowed = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(db, [ProposedLine(kind="custom", quantity=1, dough_type_id=extra.id)]),
    )
    assert allowed.status == "available"


def test_date_override_beats_week_and_can_open_extra_day(db: Session) -> None:
    settings = get_settings()
    monday = _next_iso(1)
    save_week_override(
        db,
        settings,
        week_monday(monday),
        production_weekdays=[1, 3, 6],
        daily_physical_limit=8,
        daily_base_limit=4,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    week_view = resolve_effective_day(db, settings, monday)
    assert week_view.is_open is True
    assert week_view.daily_base_limit == 4
    save_date_override(
        db,
        settings,
        monday,
        open_state="closed",
        daily_physical_limit=2,
        daily_base_limit=2,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    day_view = resolve_effective_day(db, settings, monday)
    assert day_view.is_open is False
    assert day_view.daily_physical_limit == 2
    assert day_view.origin == "date"
    tuesday = monday + timedelta(days=1)
    save_date_override(
        db,
        settings,
        tuesday,
        open_state="open",
        daily_physical_limit=None,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    assert resolve_effective_day(db, settings, tuesday).is_open is True


def test_cannot_reduce_below_committed(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(6)
    base = _base(db, "cheia")
    dough = _dough(db, base)
    shape = _shape(db)
    _hold(db, day, dough, shape, 4)
    try:
        save_date_override(
            db,
            settings,
            day,
            open_state="inherit",
            daily_physical_limit=3,
            daily_base_limit=None,
            eligibility_mode="inherit",
            eligible_base_ids=None,
        )
        raised = False
    except ConflictError:
        raised = True
    assert raised is True


def test_calendar_uses_configured_limits_and_does_not_occupy(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(3)
    preview = preview_calendar(db, settings, start=day, end=day, selected=day)
    assert preview.occupancy_enabled is True
    assert preview.reservation_policy == "admin_accept"
    assert preview.days[0].daily_physical_limit == db.get(ScheduleSettings, 1).daily_physical_limit
    assert preview.days[0].committed_physical == 0


def test_timezone_groups_commitment_on_bakery_date(db: Session) -> None:
    settings = get_settings()
    assert settings.bakery_timezone == "America/Sao_Paulo"
    day = _next_iso(3)
    base = _base(db, "fuso")
    dough = _dough(db, base)
    shape = _shape(db)
    _hold(db, day, dough, shape, 1)
    other = evaluate_day(db, settings, day + timedelta(days=1), [])
    assert other.committed_physical == 0
    same = evaluate_day(db, settings, day, [])
    assert same.committed_physical == 1


def test_eligible_list_can_exceed_daily_limit_and_blocks_unlisted(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(6)
    listed = [_base(db, f"lista{index}") for index in range(6)]
    extra = _base(db, "fora")
    save_date_override(
        db,
        settings,
        day,
        open_state="inherit",
        daily_physical_limit=None,
        daily_base_limit=None,
        eligibility_mode="explicit",
        eligible_base_ids=[row.id for row in listed],
    )
    allowed = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(
            db, [ProposedLine(kind="custom", quantity=1, dough_type_id=_dough(db, listed[0]).id)]
        ),
    )
    assert allowed.status == "available"
    blocked = evaluate_day(
        db,
        settings,
        day,
        resolve_proposed_lines(
            db, [ProposedLine(kind="custom", quantity=1, dough_type_id=_dough(db, extra).id)]
        ),
    )
    assert blocked.status == "not_eligible"
    assert blocked.reason == "ineligible_base"


def test_same_week_days_keep_independent_daily_limits(db: Session) -> None:
    settings = get_settings()
    wednesday = _next_iso(3)
    saturday = _next_iso(6, after=wednesday)
    save_week_override(
        db,
        settings,
        week_monday(wednesday),
        production_weekdays=[3, 6],
        daily_physical_limit=10,
        daily_base_limit=4,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    save_date_override(
        db,
        settings,
        saturday,
        open_state="inherit",
        daily_physical_limit=7,
        daily_base_limit=2,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    wed = resolve_effective_day(db, settings, wednesday)
    sat = resolve_effective_day(db, settings, saturday)
    assert wed.daily_physical_limit == 10
    assert sat.daily_physical_limit == 7
    assert sat.daily_base_limit == 2
    assert wed.origin == "week"
    assert sat.origin == "date"


def test_removing_overrides_returns_to_default(db: Session) -> None:
    settings = get_settings()
    monday = _next_iso(1)
    save_week_override(
        db,
        settings,
        week_monday(monday),
        production_weekdays=[1, 3, 6],
        daily_physical_limit=8,
        daily_base_limit=4,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    save_date_override(
        db,
        settings,
        monday,
        open_state="open",
        daily_physical_limit=3,
        daily_base_limit=2,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    delete_date_override(db, settings, monday)
    after_date = resolve_effective_day(db, settings, monday)
    assert after_date.is_open is True
    assert after_date.daily_physical_limit == 8
    assert after_date.origin == "week"
    delete_week_override(db, settings, week_monday(monday))
    restored = resolve_effective_day(db, settings, monday)
    assert restored.is_open is False
    assert restored.origin == "default"


def test_cannot_close_day_or_drop_committed_base(db: Session) -> None:
    settings = get_settings()
    day = _next_iso(3)
    base = _base(db, "fixa")
    dough = _dough(db, base)
    shape = _shape(db)
    _hold(db, day, dough, shape, 2)
    try:
        save_date_override(
            db,
            settings,
            day,
            open_state="closed",
            daily_physical_limit=None,
            daily_base_limit=None,
            eligibility_mode="inherit",
            eligible_base_ids=None,
        )
        closed = True
    except ConflictError:
        closed = False
    assert closed is False
    other = _base(db, "outra")
    try:
        save_date_override(
            db,
            settings,
            day,
            open_state="inherit",
            daily_physical_limit=None,
            daily_base_limit=None,
            eligibility_mode="explicit",
            eligible_base_ids=[other.id],
        )
        removed = True
    except ConflictError:
        removed = False
    assert removed is False
