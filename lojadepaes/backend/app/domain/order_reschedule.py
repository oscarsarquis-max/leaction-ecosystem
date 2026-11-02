"""Muda a data operacional da fornada. A data solicitada fica como nasceu."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import bakery_today, format_short_day
from app.domain.errors import CapacityError, ConflictError, NotFoundError
from app.domain.schedule import (
    _accept_block_message,
    _resolve_submitted_lines,
    evaluate_day,
    proposed_physical,
)
from app.models.orders import Order, OrderItem, OrderStatusHistory

MUTABLE = {"confirmed", "in_production", "ready"}
ORIGINS = {"customer": "a pedido do cliente", "store": "pela loja"}


def production_gap_notice(order: Order, today: date) -> str | None:
    day = order.production_local_date
    if day is None or abs((day - today).days) <= 2:
        return None
    return (
        f"A fornada registrada é {format_short_day(day)}. "
        "Se a entrega mudou de dia, use Mudar a data da fornada."
    )


def schedule_exception_of(order: Order) -> dict | None:
    requested = getattr(order, "requested_date", None)
    operational = getattr(order, "production_local_date", None)
    if requested is None or operational is None or requested == operational:
        return None
    origin = getattr(order, "date_change_origin", None) or "store"
    early = operational < requested
    if origin == "customer":
        label = "Antecipada a pedido do cliente" if early else "Adiada a pedido do cliente"
    else:
        label = "Antecipada pela loja" if early else "Adiada pela loja"
    return {
        "requested_date": requested.isoformat(),
        "operational_date": operational.isoformat(),
        "origin": origin,
        "label": label,
        "short_label": "antecipada" if early else "adiada",
        "reason": getattr(order, "date_change_reason", None),
        "actor": getattr(order, "date_change_actor", None),
    }


def direction_of(requested: date | None, new_day: date) -> str:
    if requested is not None and new_day > requested:
        return "adiada"
    return "antecipada"


def reschedule_order(
    session: Session,
    settings: Settings,
    order_id,
    *,
    new_date: date,
    reason: str,
    origin: str,
    actor_ref: str | None,
    notify_customer: bool = False,
    allow_closed_day: bool = False,
    record_correction: bool | None = None,
    reason_prefix: str = "",
) -> tuple[Order, str | None]:
    """Devolve o pedido e um aviso quando o e-mail foi ignorado."""
    if origin not in ORIGINS:
        raise ConflictError("informe a origem da mudança")
    text = " ".join((reason or "").split())
    if not text or len(text) > 280:
        raise ConflictError("informe o motivo, com até 280 caracteres")
    order = session.get(Order, order_id, with_for_update=True)
    if order is None:
        raise NotFoundError("pedido não encontrado")
    if order.status == "submitted":
        raise ConflictError("Pedido ainda não aceito: use Propor outra data")
    if order.status == "cancelled":
        raise ConflictError("pedido cancelado não muda de data")
    if order.status not in MUTABLE | {"completed"}:
        raise ConflictError("este pedido não muda de data")
    correction = order.status == "completed" if record_correction is None else record_correction
    if not correction and order.status not in MUTABLE:
        raise ConflictError("este pedido não muda de data")
    previous = order.production_local_date
    if previous == new_date:
        raise ConflictError("a fornada já está nesta data")
    today = bakery_today(settings)
    if not correction and new_date < today:
        raise ConflictError("a data nova não pode ser anterior a hoje")
    closed_note = ""
    if not correction:
        closed_note = _assert_capacity(session, settings, order, new_date, allow_closed_day)
        if closed_note:
            text = f"{text}{closed_note}".strip()[:280]
    notice = None
    notified = False
    if correction:
        if notify_customer:
            notice = "Pedido concluído: correção de registro, sem aviso ao cliente."
        notify_customer = False
    elif notify_customer:
        _enqueue_date_change(session, settings, order, previous, new_date, origin)
        notified = True
    order.production_local_date = new_date
    order.proposed_production_date = None
    order.date_change_origin = origin
    order.date_change_reason = text[:280]
    order.date_change_actor = (actor_ref or "")[:120] or None
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            reason=_history_reason(
                order,
                previous,
                new_date,
                origin,
                text,
                notified,
                closed_note,
                reason_prefix,
                correction,
            ),
            actor_ref=actor_ref,
        )
    )
    session.flush()
    return order, notice


def _assert_capacity(
    session: Session,
    settings: Settings,
    order: Order,
    new_date: date,
    allow_closed_day: bool,
) -> str:
    from app.domain.schedule import resolve_effective_day

    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    if not items:
        raise ConflictError("pedido sem itens")
    effective = resolve_effective_day(session, settings, new_date)
    if not effective.is_open and not allow_closed_day:
        raise CapacityError(
            f"{format_short_day(new_date)} não tem produção nesta agenda. "
            "Abra o dia na agenda ou combine outra data com a cliente."
        )
    resolved = _resolve_submitted_lines(session, items)
    day = evaluate_day(
        session,
        settings,
        new_date,
        resolved,
        ignore_advance=True,
        allow_catalog_gaps=True,
        operator_exception=True,
        ignore_intake=True,
    )
    if not day.eligible_for_selection and day.reason not in {"same_day", "closed"}:
        raise CapacityError(_accept_block_message(day))
    asked, _unknown = proposed_physical(resolved)
    if asked is not None and day.committed_physical + asked > day.daily_physical_limit:
        raise CapacityError(f"{format_short_day(new_date)}: a fornada já está completa.")
    if not effective.is_open:
        return " Reservado fora dos dias de produção."
    return ""


def _history_reason(
    order: Order,
    previous: date | None,
    new_date: date,
    origin: str,
    reason: str,
    notified: bool,
    closed_note: str,
    reason_prefix: str,
    correction: bool,
) -> str:
    requested = order.requested_date
    sense = direction_of(requested, new_date)
    lead = reason_prefix.strip()
    if correction and not lead:
        lead = "Correção de registro."
    body = (
        f"{lead + ' ' if lead else ''}"
        f"Exceção de data. Solicitado {requested.isoformat() if requested else '—'}. "
        f"Operacional {previous.isoformat() if previous else '—'} → {new_date.isoformat()}. "
        f"Origem: {ORIGINS[origin]}. Sentido: {sense}. "
        f"Aviso ao cliente: {'sim' if notified else 'não'}.{closed_note} "
        f"Motivo: {reason}"
    )
    return body[:280]


def _enqueue_date_change(
    session: Session,
    settings: Settings,
    order: Order,
    previous: date | None,
    new_date: date,
    origin: str,
) -> None:
    from app.domain.customer_mail import render_order_date_changed
    from app.models.email_outbox import EmailOutbox

    to_address = (order.customer_email or "").strip()
    if not to_address or "@" not in to_address:
        raise ConflictError("pedido sem e-mail para avisar o cliente")
    subject, body = render_order_date_changed(
        session,
        settings,
        order,
        previous=previous,
        new_date=new_date,
        origin=origin,
    )
    dedupe_key = f"{order.id}:order_date_changed:{new_date.isoformat()}"
    existing = session.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key))
    if existing is not None:
        return
    ready = settings.mail_transport_ready
    last_error = (
        None
        if ready
        else "identidade SES ainda não verificada; mensagem não enviada"
        if settings.mail_from.strip()
        else "serviço de e-mail não configurado; mensagem não enviada"
    )
    session.add(
        EmailOutbox(
            order_id=order.id,
            kind="order_date_changed",
            to_address=to_address,
            subject=subject,
            body=body,
            status="pending" if ready else "skipped",
            attempts=0,
            last_error=last_error,
            dedupe_key=dedupe_key,
        )
    )
    session.flush()
