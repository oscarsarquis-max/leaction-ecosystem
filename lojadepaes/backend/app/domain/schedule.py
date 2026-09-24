from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import (
    WEEKDAY_SHORT,
    bakery_now,
    bakery_today,
    dates_in_week,
    format_long_date,
    local_date_of,
    week_monday,
    week_sunday,
)
from app.domain.errors import (
    CapacityError,
    ConfirmationError,
    ConflictError,
    NotFoundError,
    ProductError,
)
from app.models.catalog import DoughType
from app.models.enums import OrderStatus
from app.models.orders import Order, OrderItem
from app.models.production import FulfillmentSlot, ProductionBatch
from app.models.products import Product, ProductVariant
from app.models.schedule import (
    RecipeBase,
    ScheduleDateOverride,
    ScheduleEligibleBase,
    ScheduleSettings,
    ScheduleWeekOverride,
)

BOOTSTRAP_WEEKDAYS = (3, 6)
BOOTSTRAP_PHYSICAL_LIMIT = 15
BOOTSTRAP_BASE_LIMIT = 5
BOOTSTRAP_HORIZON_DAYS = 56

ORIGIN_DEFAULT = "default"
ORIGIN_WEEK = "week"
ORIGIN_DATE = "date"

STATUS_AVAILABLE = "available"
STATUS_FULL = "full"
STATUS_CLOSED = "closed"
STATUS_PAST = "past"
STATUS_NOT_ELIGIBLE = "not_eligible"
STATUS_NEW_BASE_BLOCKED = "new_base_blocked"

REASON_PHYSICAL = "physical"
REASON_NEW_BASE = "new_base"
REASON_CLOSED = "closed"
REASON_PAST = "past"
REASON_INELIGIBLE_BASE = "ineligible_base"
REASON_UNKNOWN_UNITS = "unknown_units"
REASON_UNKNOWN_BASE = "unknown_base"
REASON_NONE = "none"


@dataclass(frozen=True)
class ProposedLine:
    kind: str
    quantity: int
    variant_id: UUID | None = None
    dough_type_id: UUID | None = None


@dataclass(frozen=True)
class ResolvedLine:
    physical_units: int | None
    recipe_base_id: UUID | None
    unknown_physical: bool = False
    unknown_base: bool = False


@dataclass
class EffectiveDay:
    local_date: date
    is_open: bool
    daily_physical_limit: int
    daily_base_limit: int
    origin: str
    eligible_base_ids: frozenset[UUID] | None
    eligibility_origin: str
    week_start: date
    week_end: date


@dataclass
class DayAvailability:
    local_date: date
    status: str
    origin: str
    daily_physical_limit: int
    daily_base_limit: int
    committed_physical: int
    remaining_physical: int
    committed_base_ids: list[str]
    remaining_new_bases: int
    reason: str
    accessible_label: str
    weekday_name: str
    eligible_for_selection: bool
    awaiting_review: bool = False
    windows: list[dict] = field(default_factory=list)


@dataclass
class SchedulePreview:
    occupancy_enabled: bool
    reservation_policy: str
    timezone: str
    selected_date: date | None
    selected_status: str | None
    full_message: str | None
    alternatives: list[dict]
    days: list[DayAvailability]
    notice: str | None
    review_message: str | None = None


def ensure_schedule_settings(session: Session) -> ScheduleSettings:
    row = session.get(ScheduleSettings, 1)
    if row is not None:
        return row
    row = ScheduleSettings(
        id=1,
        production_weekdays=list(BOOTSTRAP_WEEKDAYS),
        daily_physical_limit=BOOTSTRAP_PHYSICAL_LIMIT,
        daily_base_limit=BOOTSTRAP_BASE_LIMIT,
        horizon_days=BOOTSTRAP_HORIZON_DAYS,
        min_advance_hours=0,
        eligibility_mode="inherit",
        occupancy_enabled=True,
        reservation_policy="admin_accept",
    )
    session.add(row)
    session.flush()
    return row


def eligible_ids(
    session: Session, kind: str, scope_id: UUID | None
) -> frozenset[UUID] | None:
    rows = session.scalars(
        select(ScheduleEligibleBase.recipe_base_id).where(
            ScheduleEligibleBase.scope_kind == kind,
            ScheduleEligibleBase.scope_id == scope_id,
        )
    ).all()
    if not rows:
        return None
    return frozenset(rows)


def resolve_effective_day(
    session: Session,
    settings: Settings,
    local_date: date,
    *,
    week_override: ScheduleWeekOverride | None | object = ...,
    date_override: ScheduleDateOverride | None | object = ...,
) -> EffectiveDay:
    del settings
    defaults = ensure_schedule_settings(session)
    week_start = week_monday(local_date)
    if week_override is ...:
        week_row = session.scalar(
            select(ScheduleWeekOverride).where(ScheduleWeekOverride.week_start == week_start)
        )
    else:
        week_row = week_override  # type: ignore[assignment]
    if date_override is ...:
        date_row = session.scalar(
            select(ScheduleDateOverride).where(ScheduleDateOverride.local_date == local_date)
        )
    else:
        date_row = date_override  # type: ignore[assignment]

    weekdays = list(defaults.production_weekdays)
    physical = defaults.daily_physical_limit
    bases = defaults.daily_base_limit
    origin = ORIGIN_DEFAULT
    eligible = None
    eligibility_origin = ORIGIN_DEFAULT
    if defaults.eligibility_mode == "explicit":
        eligible = eligible_ids(session, "default", None) or frozenset()

    if week_row is not None:
        if week_row.production_weekdays is not None:
            weekdays = list(week_row.production_weekdays)
            origin = ORIGIN_WEEK
        if week_row.daily_physical_limit is not None:
            physical = week_row.daily_physical_limit
            origin = ORIGIN_WEEK
        if week_row.daily_base_limit is not None:
            bases = week_row.daily_base_limit
            origin = ORIGIN_WEEK
        if week_row.eligibility_mode == "explicit":
            eligible = eligible_ids(session, "week", week_row.id) or frozenset()
            eligibility_origin = ORIGIN_WEEK

    is_open = local_date.isoweekday() in weekdays
    if date_row is not None:
        if date_row.open_state == "open":
            is_open = True
            origin = ORIGIN_DATE
        elif date_row.open_state == "closed":
            is_open = False
            origin = ORIGIN_DATE
        if date_row.daily_physical_limit is not None:
            physical = date_row.daily_physical_limit
            origin = ORIGIN_DATE
        if date_row.daily_base_limit is not None:
            bases = date_row.daily_base_limit
            origin = ORIGIN_DATE
        if date_row.eligibility_mode == "explicit":
            eligible = eligible_ids(session, "date", date_row.id) or frozenset()
            eligibility_origin = ORIGIN_DATE

    return EffectiveDay(
        local_date=local_date,
        is_open=is_open,
        daily_physical_limit=physical,
        daily_base_limit=bases,
        origin=origin,
        eligible_base_ids=eligible,
        eligibility_origin=eligibility_origin,
        week_start=week_start,
        week_end=week_sunday(local_date),
    )


def resolve_proposed_lines(session: Session, lines: list[ProposedLine]) -> list[ResolvedLine]:
    resolved: list[ResolvedLine] = []
    for line in lines:
        if line.quantity < 1:
            raise ProductError("quantidade da seleção deve ser maior que zero")
        if line.kind == "product":
            if line.variant_id is None:
                raise ProductError("informe a variação do produto")
            variant = session.get(ProductVariant, line.variant_id)
            if variant is None:
                raise NotFoundError("variação não encontrada")
            product = session.get(Product, variant.product_id)
            base_id = product.recipe_base_id if product is not None else None
            units = variant.physical_units
            resolved.append(
                ResolvedLine(
                    physical_units=None if units is None else units * line.quantity,
                    recipe_base_id=base_id,
                    unknown_physical=units is None,
                    unknown_base=base_id is None,
                )
            )
            continue
        if line.kind == "custom":
            if line.dough_type_id is None:
                raise ProductError("informe a massa do pão personalizado")
            dough = session.get(DoughType, line.dough_type_id)
            if dough is None:
                raise NotFoundError("massa não encontrada")
            resolved.append(
                ResolvedLine(
                    physical_units=line.quantity,
                    recipe_base_id=dough.recipe_base_id,
                    unknown_physical=False,
                    unknown_base=dough.recipe_base_id is None,
                )
            )
            continue
        raise ProductError("tipo de item da seleção não reconhecido")
    return resolved


def proposed_physical(resolved: list[ResolvedLine]) -> tuple[int | None, bool]:
    if any(row.unknown_physical for row in resolved):
        return None, True
    return sum(row.physical_units or 0 for row in resolved), False


def proposed_bases(resolved: list[ResolvedLine]) -> set[UUID]:
    return {row.recipe_base_id for row in resolved if row.recipe_base_id is not None}


def committed_for_date(
    session: Session, settings: Settings, local_date: date
) -> tuple[int, set[UUID]]:
    holding = (
        select(Order.id)
        .where(Order.holds_capacity.is_(True))
        .subquery()
    )
    physical_stmt: Select[tuple[int]] = (
        select(func.coalesce(func.sum(func.coalesce(OrderItem.physical_units, OrderItem.quantity)), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.holds_capacity.is_(True))
    )
    items = session.scalars(
        select(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.holds_capacity.is_(True))
    ).all()
    physical = 0
    bases: set[UUID] = set()
    for item in items:
        order = session.get(Order, item.order_id)
        if order is None:
            continue
        item_date = order.production_local_date
        if item_date is None and order.production_batch_id is not None:
            batch = session.get(ProductionBatch, order.production_batch_id)
            if batch is not None:
                item_date = local_date_of(batch.breads_available_at, settings)
        if item_date != local_date:
            continue
        physical += int(item.physical_units if item.physical_units is not None else item.quantity)
        if item.recipe_base_id is not None:
            bases.add(item.recipe_base_id)
        elif item.dough_type_id is not None:
            dough = session.get(DoughType, item.dough_type_id)
            if dough is not None and dough.recipe_base_id is not None:
                bases.add(dough.recipe_base_id)
    del holding, physical_stmt
    return physical, bases


def dates_awaiting_review(session: Session, start: date, end: date) -> set[date]:
    """Pedidos enviados que ainda não reservam a fornada. Não altera o saldo formal."""
    rows = session.scalars(
        select(Order.production_local_date).where(
            Order.production_local_date.is_not(None),
            Order.production_local_date >= start,
            Order.production_local_date <= end,
            Order.holds_capacity.is_(False),
            Order.status == OrderStatus.SUBMITTED.value,
        )
    ).all()
    return {row for row in rows if row is not None}


def _windows_for_date(session: Session, settings: Settings, local_date: date) -> list[dict]:
    slots = session.scalars(select(FulfillmentSlot).where(FulfillmentSlot.is_active.is_(True))).all()
    found: list[dict] = []
    for slot in slots:
        if local_date_of(slot.starts_at, settings) != local_date:
            continue
        found.append(
            {
                "id": str(slot.id),
                "starts_at": slot.starts_at.isoformat(),
                "ends_at": slot.ends_at.isoformat(),
                "modality": slot.modality,
            }
        )
    return found


def evaluate_day(
    session: Session,
    settings: Settings,
    local_date: date,
    resolved: list[ResolvedLine],
    *,
    include_windows: bool = False,
    awaiting_review: bool = False,
) -> DayAvailability:
    effective = resolve_effective_day(session, settings, local_date)
    today = bakery_today(settings)
    now = bakery_now(settings)
    row = ensure_schedule_settings(session)
    too_soon = (now + timedelta(hours=row.min_advance_hours)).date() > local_date
    committed_physical, committed_bases = committed_for_date(session, settings, local_date)
    remaining = max(effective.daily_physical_limit - committed_physical, 0)
    asked_physical, unknown_physical = proposed_physical(resolved)
    asked_bases = proposed_bases(resolved)
    unknown_base = any(item.unknown_base for item in resolved)
    union_bases = set(committed_bases) | asked_bases
    remaining_new = max(effective.daily_base_limit - len(committed_bases), 0)
    reason = REASON_NONE
    status = STATUS_AVAILABLE
    eligible = True

    if local_date < today or too_soon:
        status = STATUS_PAST
        reason = REASON_PAST
        eligible = False
    elif not effective.is_open:
        status = STATUS_CLOSED
        reason = REASON_CLOSED
        eligible = False
    elif effective.daily_physical_limit == 0 or remaining <= 0:
        status = STATUS_FULL
        reason = REASON_PHYSICAL
        eligible = False
    else:
        ineligible = False
        if effective.eligible_base_ids is not None:
            ineligible = any(base_id not in effective.eligible_base_ids for base_id in asked_bases)
        if ineligible:
            status = STATUS_NOT_ELIGIBLE
            reason = REASON_INELIGIBLE_BASE
            eligible = False
        elif asked_physical is not None and asked_physical > remaining:
            status = STATUS_FULL
            reason = REASON_PHYSICAL
            eligible = False
        elif len(union_bases) > effective.daily_base_limit:
            status = STATUS_NEW_BASE_BLOCKED
            reason = REASON_NEW_BASE
            eligible = False
        elif unknown_physical and resolved:
            reason = REASON_UNKNOWN_UNITS
            eligible = False
            status = STATUS_NOT_ELIGIBLE
        elif unknown_base and resolved:
            reason = REASON_UNKNOWN_BASE
            eligible = False
            status = STATUS_NOT_ELIGIBLE

    if status == STATUS_AVAILABLE and awaiting_review:
        accessible = (
            f"{format_long_date(local_date)}: dia de produção sujeito à avaliação da padaria"
        )
    elif status == STATUS_AVAILABLE and not resolved:
        accessible = f"{format_long_date(local_date)}: dia de produção aberto"
    elif status == STATUS_AVAILABLE:
        accessible = (
            f"{format_long_date(local_date)}: cabe nesta seleção; a confirmação depende do aceite"
        )
    elif status == STATUS_FULL:
        accessible = f"{format_long_date(local_date)}: fornada completa"
    elif status == STATUS_CLOSED:
        accessible = f"{format_long_date(local_date)}: sem produção"
    elif status == STATUS_PAST:
        accessible = f"{format_long_date(local_date)}: data passada"
    elif status == STATUS_NEW_BASE_BLOCKED:
        accessible = (
            f"{format_long_date(local_date)}: não comporta um tipo de pão novo neste pedido"
        )
    else:
        accessible = f"{format_long_date(local_date)}: indisponível para esta seleção"

    return DayAvailability(
        local_date=local_date,
        status=status,
        origin=effective.origin,
        daily_physical_limit=effective.daily_physical_limit,
        daily_base_limit=effective.daily_base_limit,
        committed_physical=committed_physical,
        remaining_physical=remaining,
        committed_base_ids=[str(item) for item in sorted(committed_bases, key=str)],
        remaining_new_bases=remaining_new,
        reason=reason,
        accessible_label=accessible,
        weekday_name=WEEKDAY_SHORT[local_date.isoweekday()],
        eligible_for_selection=eligible,
        awaiting_review=awaiting_review and status == STATUS_AVAILABLE,
        windows=_windows_for_date(session, settings, local_date) if include_windows else [],
    )


def preview_calendar(
    session: Session,
    settings: Settings,
    *,
    start: date | None = None,
    end: date | None = None,
    selected: date | None = None,
    lines: list[ProposedLine] | None = None,
) -> SchedulePreview:
    row = ensure_schedule_settings(session)
    today = bakery_today(settings)
    first = start or today
    last = end or (today + timedelta(days=row.horizon_days))
    if last < first:
        raise ProductError("o intervalo do calendário está invertido")
    if (last - first).days > 120:
        raise ProductError("o intervalo do calendário é longo demais")
    resolved = resolve_proposed_lines(session, lines or [])
    pending = dates_awaiting_review(session, first, last)
    days = [
        evaluate_day(
            session,
            settings,
            first + timedelta(days=offset),
            resolved,
            include_windows=selected == first + timedelta(days=offset),
            awaiting_review=(first + timedelta(days=offset)) in pending,
        )
        for offset in range((last - first).days + 1)
    ]
    selected_day = next((item for item in days if item.local_date == selected), None)
    alternatives: list[dict] = []
    full_message = None
    if selected_day is not None and not selected_day.eligible_for_selection:
        if selected_day.status == STATUS_FULL:
            full_message = "Essa fornada já está completa. Que tal escolher outra data?"
        elif selected_day.status == STATUS_NEW_BASE_BLOCKED:
            full_message = (
                f"A fornada de {selected_day.weekday_name} ainda tem espaço, "
                "mas não comporta um tipo de pão novo neste pedido. "
                "Que tal escolher outra data disponível?"
            )
        elif selected_day.status == STATUS_CLOSED:
            full_message = (
                f"{format_long_date(selected_day.local_date)} não tem produção. "
                "Que tal escolher a próxima data disponível?"
            )
        alternatives = [
            {
                "date": item.local_date.isoformat(),
                "accessible_label": item.accessible_label,
                "weekday_name": item.weekday_name,
            }
            for item in days
            if item.eligible_for_selection and item.local_date != selected
        ][:3]
        if not alternatives:
            full_message = (
                (full_message + " ")
                if full_message
                else ""
            ) + "Nenhuma data à frente comporta este pedido agora. A seleção foi mantida."
    notice = None
    if not resolved:
        notice = (
            "O ícone de pão marca um dia de produção aberto. "
            "Isso não garante que qualquer combinação caiba. "
            "A vaga só fica reservada quando a padaria aceitar o pedido."
        )
    review_message = None
    if (
        selected_day is not None
        and selected_day.awaiting_review
        and selected_day.eligible_for_selection
    ):
        review_message = (
            "Esta data está sujeita à avaliação da padaria. O pagamento não reserva a fornada."
        )
    return SchedulePreview(
        occupancy_enabled=row.occupancy_enabled,
        reservation_policy=row.reservation_policy,
        timezone=settings.bakery_timezone,
        selected_date=selected,
        selected_status=selected_day.status if selected_day else None,
        full_message=full_message,
        alternatives=alternatives,
        days=days,
        notice=notice,
        review_message=review_message,
    )


def occupy_capacity(session: Session, settings: Settings, order: Order) -> None:
    row = session.execute(
        select(ScheduleSettings).where(ScheduleSettings.id == 1).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        ensure_schedule_settings(session)
        row = session.execute(
            select(ScheduleSettings).where(ScheduleSettings.id == 1).with_for_update()
        ).scalar_one()
    if row.reservation_policy != "admin_accept" or not row.occupancy_enabled:
        raise ConfirmationError("ocupação só ocorre no aceite administrativo")
    if order.holds_capacity:
        return
    local_date = order.production_local_date
    if local_date is None:
        raise ConfirmationError("data da fornada ausente")
    items = session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    if not items:
        raise ConfirmationError("pedido sem itens")
    proposed: list[ProposedLine] = []
    for item in items:
        if item.product_variant_id is not None:
            proposed.append(
                ProposedLine(
                    kind="product",
                    quantity=item.quantity,
                    variant_id=item.product_variant_id,
                )
            )
        else:
            proposed.append(
                ProposedLine(
                    kind="custom",
                    quantity=item.quantity,
                    dough_type_id=item.dough_type_id,
                )
            )
    resolved = resolve_proposed_lines(session, proposed)
    day = evaluate_day(session, settings, local_date, resolved)
    if not day.eligible_for_selection:
        raise CapacityError(
            day.accessible_label
            or "esta data não comporta o pedido com a composição atual"
        )
    order.holds_capacity = True
    session.flush()


def assert_config_fits_commitments(
    session: Session,
    settings: Settings,
    local_date: date,
    effective: EffectiveDay,
) -> list[str]:
    physical, bases = committed_for_date(session, settings, local_date)
    conflicts: list[str] = []
    if not effective.is_open and physical > 0:
        conflicts.append(
            f"{format_long_date(local_date)} tem pedidos comprometidos e não pode ser fechada"
        )
    if effective.daily_physical_limit < physical:
        conflicts.append(
            f"{format_long_date(local_date)} já tem {physical} pães comprometidos"
        )
    if effective.daily_base_limit < len(bases):
        conflicts.append(
            f"{format_long_date(local_date)} já usa {len(bases)} receitas-base comprometidas"
        )
    if effective.eligible_base_ids is not None:
        missing = bases - effective.eligible_base_ids
        if missing:
            conflicts.append(
                f"{format_long_date(local_date)} já tem receita-base comprometida fora da lista"
            )
    return conflicts


def replace_eligible_bases(
    session: Session, kind: str, scope_id: UUID | None, base_ids: list[UUID] | None
) -> None:
    existing = session.scalars(
        select(ScheduleEligibleBase).where(
            ScheduleEligibleBase.scope_kind == kind,
            ScheduleEligibleBase.scope_id == scope_id,
        )
    ).all()
    for row in existing:
        session.delete(row)
    if not base_ids:
        session.flush()
        return
    seen: set[UUID] = set()
    for base_id in base_ids:
        if base_id in seen:
            continue
        if session.get(RecipeBase, base_id) is None:
            raise NotFoundError("receita-base não encontrada")
        session.add(
            ScheduleEligibleBase(scope_kind=kind, scope_id=scope_id, recipe_base_id=base_id)
        )
        seen.add(base_id)
    session.flush()


def save_defaults(
    session: Session,
    settings: Settings,
    *,
    production_weekdays: list[int],
    daily_physical_limit: int,
    daily_base_limit: int,
    horizon_days: int,
    min_advance_hours: int,
    eligibility_mode: str,
    eligible_base_ids: list[UUID] | None,
) -> ScheduleSettings:
    _validate_weekdays(production_weekdays)
    _validate_positive(daily_physical_limit, "limite diário de pães")
    _validate_positive(daily_base_limit, "limite diário de receitas-base")
    _validate_positive(horizon_days, "horizonte da agenda")
    if min_advance_hours < 0:
        raise ProductError("a antecedência não pode ser negativa")
    if eligibility_mode not in {"inherit", "explicit"}:
        raise ProductError("modo de disponibilidade das receitas inválido")
    row = ensure_schedule_settings(session)
    row.production_weekdays = production_weekdays
    row.daily_physical_limit = daily_physical_limit
    row.daily_base_limit = daily_base_limit
    row.horizon_days = horizon_days
    row.min_advance_hours = min_advance_hours
    row.eligibility_mode = eligibility_mode
    replace_eligible_bases(
        session, "default", None, eligible_base_ids if eligibility_mode == "explicit" else None
    )
    conflicts = _conflicts_for_horizon(session, settings)
    if conflicts:
        raise ConflictError(conflicts[0])
    session.flush()
    return row


def preview_week_change(
    session: Session,
    settings: Settings,
    week_start: date,
    *,
    production_weekdays: list[int] | None,
    daily_physical_limit: int | None,
    daily_base_limit: int | None,
    eligibility_mode: str,
    eligible_base_ids: list[UUID] | None,
) -> dict:
    start = week_monday(week_start)
    if production_weekdays is not None:
        _validate_weekdays(production_weekdays)
    _validate_optional_limit(daily_physical_limit, "limite diário de pães")
    _validate_optional_limit(daily_base_limit, "limite diário de receitas-base")
    existing = session.scalar(
        select(ScheduleWeekOverride).where(ScheduleWeekOverride.week_start == start)
    )
    draft = ScheduleWeekOverride(
        id=existing.id if existing else None,
        week_start=start,
        production_weekdays=production_weekdays,
        daily_physical_limit=daily_physical_limit,
        daily_base_limit=daily_base_limit,
        eligibility_mode=eligibility_mode,
    )
    dates = dates_in_week(start)
    affected = []
    conflicts: list[str] = []
    for local_date in dates:
        effective = resolve_effective_day(session, settings, local_date, week_override=draft)
        day_conflicts = assert_config_fits_commitments(session, settings, local_date, effective)
        conflicts.extend(day_conflicts)
        committed_physical, committed_bases = committed_for_date(session, settings, local_date)
        affected.append(
            {
                "date": local_date.isoformat(),
                "origin": effective.origin,
                "is_open": effective.is_open,
                "daily_physical_limit": effective.daily_physical_limit,
                "daily_base_limit": effective.daily_base_limit,
                "committed_physical": committed_physical,
                "committed_bases": len(committed_bases),
                "conflicts": day_conflicts,
            }
        )
    return {
        "week_start": start.isoformat(),
        "week_end": week_sunday(start).isoformat(),
        "dates": affected,
        "conflicts": conflicts,
    }


def save_week_override(
    session: Session,
    settings: Settings,
    week_start: date,
    *,
    production_weekdays: list[int] | None,
    daily_physical_limit: int | None,
    daily_base_limit: int | None,
    eligibility_mode: str,
    eligible_base_ids: list[UUID] | None,
) -> ScheduleWeekOverride:
    preview = preview_week_change(
        session,
        settings,
        week_start,
        production_weekdays=production_weekdays,
        daily_physical_limit=daily_physical_limit,
        daily_base_limit=daily_base_limit,
        eligibility_mode=eligibility_mode,
        eligible_base_ids=eligible_base_ids,
    )
    if preview["conflicts"]:
        raise ConflictError(preview["conflicts"][0])
    start = week_monday(week_start)
    row = session.scalar(
        select(ScheduleWeekOverride).where(ScheduleWeekOverride.week_start == start)
    )
    if row is None:
        row = ScheduleWeekOverride(week_start=start)
        session.add(row)
        session.flush()
    row.production_weekdays = production_weekdays
    row.daily_physical_limit = daily_physical_limit
    row.daily_base_limit = daily_base_limit
    row.eligibility_mode = eligibility_mode
    replace_eligible_bases(
        session, "week", row.id, eligible_base_ids if eligibility_mode == "explicit" else None
    )
    session.flush()
    return row


def delete_week_override(session: Session, settings: Settings, week_start: date) -> None:
    start = week_monday(week_start)
    row = session.scalar(
        select(ScheduleWeekOverride).where(ScheduleWeekOverride.week_start == start)
    )
    if row is None:
        raise NotFoundError("esta semana não tem exceção")
    conflicts: list[str] = []
    for local_date in dates_in_week(start):
        effective = resolve_effective_day(session, settings, local_date, week_override=None)
        conflicts.extend(assert_config_fits_commitments(session, settings, local_date, effective))
    if conflicts:
        raise ConflictError(conflicts[0])
    replace_eligible_bases(session, "week", row.id, None)
    session.delete(row)
    session.flush()


def save_date_override(
    session: Session,
    settings: Settings,
    local_date: date,
    *,
    open_state: str,
    daily_physical_limit: int | None,
    daily_base_limit: int | None,
    eligibility_mode: str,
    eligible_base_ids: list[UUID] | None,
) -> ScheduleDateOverride:
    if open_state not in {"inherit", "open", "closed"}:
        raise ProductError("estado de abertura inválido")
    _validate_optional_limit(daily_physical_limit, "limite diário de pães")
    _validate_optional_limit(daily_base_limit, "limite diário de receitas-base")
    draft = ScheduleDateOverride(
        local_date=local_date,
        open_state=open_state,
        daily_physical_limit=daily_physical_limit,
        daily_base_limit=daily_base_limit,
        eligibility_mode=eligibility_mode,
    )
    effective = resolve_effective_day(session, settings, local_date, date_override=draft)
    conflicts = assert_config_fits_commitments(session, settings, local_date, effective)
    if conflicts:
        raise ConflictError(conflicts[0])
    row = session.scalar(
        select(ScheduleDateOverride).where(ScheduleDateOverride.local_date == local_date)
    )
    if row is None:
        row = ScheduleDateOverride(local_date=local_date)
        session.add(row)
        session.flush()
    row.open_state = open_state
    row.daily_physical_limit = daily_physical_limit
    row.daily_base_limit = daily_base_limit
    row.eligibility_mode = eligibility_mode
    replace_eligible_bases(
        session, "date", row.id, eligible_base_ids if eligibility_mode == "explicit" else None
    )
    session.flush()
    return row


def delete_date_override(session: Session, settings: Settings, local_date: date) -> None:
    row = session.scalar(
        select(ScheduleDateOverride).where(ScheduleDateOverride.local_date == local_date)
    )
    if row is None:
        raise NotFoundError("esta data não tem exceção")
    effective = resolve_effective_day(session, settings, local_date, date_override=None)
    conflicts = assert_config_fits_commitments(session, settings, local_date, effective)
    if conflicts:
        raise ConflictError(conflicts[0])
    replace_eligible_bases(session, "date", row.id, None)
    session.delete(row)
    session.flush()


def admin_day_view(session: Session, settings: Settings, local_date: date) -> dict:
    effective = resolve_effective_day(session, settings, local_date)
    physical, bases = committed_for_date(session, settings, local_date)
    return {
        "date": local_date.isoformat(),
        "week_start": effective.week_start.isoformat(),
        "week_end": effective.week_end.isoformat(),
        "origin": effective.origin,
        "is_open": effective.is_open,
        "daily_physical_limit": effective.daily_physical_limit,
        "daily_base_limit": effective.daily_base_limit,
        "eligibility_origin": effective.eligibility_origin,
        "eligible_base_ids": (
            [str(item) for item in sorted(effective.eligible_base_ids, key=str)]
            if effective.eligible_base_ids is not None
            else None
        ),
        "committed_physical": physical,
        "committed_base_ids": [str(item) for item in sorted(bases, key=str)],
        "occupancy_enabled": ensure_schedule_settings(session).occupancy_enabled,
        "reservation_policy": ensure_schedule_settings(session).reservation_policy,
    }


def _conflicts_for_horizon(session: Session, settings: Settings) -> list[str]:
    today = bakery_today(settings)
    row = ensure_schedule_settings(session)
    conflicts: list[str] = []
    for offset in range(row.horizon_days + 1):
        local_date = today + timedelta(days=offset)
        effective = resolve_effective_day(session, settings, local_date)
        conflicts.extend(assert_config_fits_commitments(session, settings, local_date, effective))
        if len(conflicts) >= 5:
            break
    return conflicts


def _validate_weekdays(values: list[int]) -> None:
    if any(day < 1 or day > 7 for day in values):
        raise ProductError("dia da semana inválido")
    if len(set(values)) != len(values):
        raise ProductError("há dias de produção repetidos")


def _validate_positive(value: int, label: str) -> None:
    if value < 1:
        raise ProductError(f"{label} deve ser maior que zero")


def _validate_optional_limit(value: int | None, label: str) -> None:
    if value is not None and value < 0:
        raise ProductError(f"{label} não pode ser negativo")
