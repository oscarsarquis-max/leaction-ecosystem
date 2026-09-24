from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import WEEKDAY_SHORT, bakery_today
from app.domain.schedule import (
    STATUS_CLOSED,
    STATUS_FULL,
    STATUS_NEW_BASE_BLOCKED,
    STATUS_NOT_ELIGIBLE,
    STATUS_PAST,
    ProposedLine,
    dates_awaiting_review,
    ensure_schedule_settings,
    evaluate_day,
    resolve_proposed_lines,
)
from app.schemas.suggestions import SuggestionsOut, SuggestionsQuery


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


def _context_prefix(source: str, label: str) -> str:
    if source == "next_eligible":
        return f"Próxima fornada: {label}. Nada foi escolhido nem reservado. "
    return ""


def _with_next_date(
    session: Session,
    settings: Settings,
    lines: list[ProposedLine],
    after: date,
    message: str,
) -> str:
    following = next_eligible_date(session, settings, lines, after=after)
    if following is None:
        return message
    following_label = format_short_bake_date(following)
    return f"{message} A próxima data que comporta esta seleção é {following_label}."


def _count_phrase(count: int, singular: str, plural: str) -> str:
    word = singular if count == 1 else plural
    return f"{count} {word}"


def _vacancy_copy(day, *, pending: bool) -> tuple[str, str, bool]:
    title = "Vagas nesta fornada"
    if day.status == STATUS_CLOSED:
        return title, "Esse dia não tem produção. Que tal escolher outra data?", False
    if day.status == STATUS_PAST:
        return title, "Essa data não está aberta para encomenda.", False
    if day.status == STATUS_NOT_ELIGIBLE:
        return title, "Não dá para confirmar a vaga desta seleção nesta data.", False
    breads = day.remaining_physical
    if breads <= 0:
        return title, "Não há vaga nesta fornada. Que tal escolher outra data?", False
    bread_label = _count_phrase(breads, "pão", "pães")
    types_left = day.remaining_new_bases
    if types_left <= 0:
        room = f"Ainda há vaga para {bread_label}, sem vaga para um tipo novo."
    else:
        type_label = _count_phrase(types_left, "tipo diferente", "tipos diferentes")
        room = f"Ainda há vaga para {bread_label} e para {type_label}."
    if day.status == STATUS_FULL:
        room = f"Esta seleção não cabe. {room}"
    elif day.status == STATUS_NEW_BASE_BLOCKED:
        room = f"Esta seleção pede um tipo novo e não há vaga para isso. {room}"
    if pending:
        room += " Há pedido aguardando a avaliação da padaria, então essa folga não está garantida."
    else:
        room += " A vaga só fica reservada quando a padaria aceitar o pedido."
    return title, room, True


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
            message="Não há fornada disponível neste calendário. Você pode pedir outra data.",
            items=[],
        )

    label = format_short_bake_date(context_date)
    pending = context_date in dates_awaiting_review(session, context_date, context_date)
    empty_day = evaluate_day(
        session, settings, context_date, resolved_cart, awaiting_review=pending
    )
    prefix = _context_prefix(source, label)
    title, message, has_room = _vacancy_copy(empty_day, pending=pending)
    if not has_room:
        message = _with_next_date(session, settings, cart, context_date, message)
    return SuggestionsOut(
        context_date=context_date,
        context_source=source,
        context_label=label,
        mode="empty",
        title=title,
        message=f"{prefix}{message}",
        items=[],
    )
