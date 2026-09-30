from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import WEEKDAY_SHORT, bakery_today, local_date_of
from app.domain.capacity import occupied_slot_units
from app.domain.schedule import (
    STATUS_CLOSED,
    STATUS_FULL,
    STATUS_NEW_BASE_BLOCKED,
    STATUS_NOT_ELIGIBLE,
    STATUS_PAST,
    ProposedLine,
    ensure_schedule_settings,
    evaluate_day,
    resolve_proposed_lines,
)
from app.models.production import FulfillmentSlot
from app.schemas.suggestions import SuggestionsOut, SuggestionsQuery, VacancySlotOut


def format_short_bake_date(value: date) -> str:
    return f"{WEEKDAY_SHORT[value.isoweekday()]}, {value.strftime('%d/%m')}"


def next_eligible_date(
    session: Session,
    settings: Settings,
    lines: list[ProposedLine],
    *,
    after: date | None = None,
) -> date | None:
    resolved = resolve_proposed_lines(session, lines)
    today = bakery_today(settings)
    horizon_end = today + timedelta(days=ensure_schedule_settings(session).horizon_days)
    local_date = today if after is None else after + timedelta(days=1)
    while local_date <= horizon_end:
        day = evaluate_day(session, settings, local_date, resolved)
        if day.eligible_for_selection:
            return local_date
        local_date += timedelta(days=1)
    return None


def _notice(source: str, label: str, day) -> str:
    when = f"Próxima fornada: {label}." if source == "next_eligible" else f"{label}."
    if day.status == STATUS_CLOSED:
        return f"{when} Esse dia não tem produção."
    if day.status == STATUS_PAST:
        return f"{when} Essa data não está aberta para encomenda."
    if day.status in {STATUS_FULL, STATUS_NEW_BASE_BLOCKED}:
        return f"{when} Não há vaga nesta data."
    if day.status == STATUS_NOT_ELIGIBLE:
        return f"{when} Esta seleção não cabe nesta data."
    return when


def vacancy_slots(session: Session, settings: Settings, local_date: date) -> list[VacancySlotOut]:
    rows = session.scalars(
        select(FulfillmentSlot).where(FulfillmentSlot.is_active.is_(True)).order_by(FulfillmentSlot.starts_at)
    ).all()
    found: list[VacancySlotOut] = []
    for slot in rows:
        if local_date_of(slot.starts_at, settings) != local_date:
            continue
        remaining = max(slot.capacity_units - occupied_slot_units(session, slot.id), 0)
        found.append(
            VacancySlotOut(
                id=str(slot.id),
                starts_at=slot.starts_at.isoformat(),
                ends_at=slot.ends_at.isoformat(),
                remaining=remaining,
            )
        )
    return found


def suggest_fornada(
    session: Session, settings: Settings, payload: SuggestionsQuery
) -> SuggestionsOut:
    cart = [
        ProposedLine(
            kind=line.kind,
            quantity=line.quantity,
            variant_id=line.variant_id,
            dough_type_id=line.dough_type_id,
        )
        for line in payload.lines
    ]
    resolved_cart = resolve_proposed_lines(session, cart)
    source: Literal["selected", "next_eligible", "none"]
    if payload.selected is not None:
        context_date = payload.selected
        source = "selected"
    else:
        context_date = next_eligible_date(session, settings, cart)
        source = "next_eligible" if context_date is not None else "none"

    if context_date is None:
        return SuggestionsOut(
            context_date=None,
            context_source="none",
            context_label=None,
            mode="empty",
            title="Vagas nesta fornada",
            message="Não há fornada disponível neste calendário.",
            items=[],
            slots=[],
        )

    label = format_short_bake_date(context_date)
    empty_day = evaluate_day(session, settings, context_date, resolved_cart)
    return SuggestionsOut(
        context_date=context_date,
        context_source=source,
        context_label=label,
        mode="empty",
        title="Vagas nesta fornada",
        message=_notice(source, label, empty_day),
        items=[],
        slots=vacancy_slots(session, settings, context_date),
    )
