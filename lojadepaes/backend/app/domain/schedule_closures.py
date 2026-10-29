from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import MONTH_NAMES, bakery_today, format_long_date
from app.domain.errors import ConfirmationError, NotFoundError, ProductError
from app.models.date_requests import DateRequest
from app.models.enums import OrderStatus
from app.models.orders import Order
from app.models.schedule import ScheduleClosure, ScheduleClosureEvent

STATUS_SCHEDULED = "scheduled"
STATUS_IN_FORCE = "in_force"
STATUS_CONCLUDED = "concluded"
STATUS_CANCELLED = "cancelled"
REASON_PERIOD = "period_closed"
REASON_INTAKE = "intake_paused"
ORIGIN_CLOSURE = "closure"
OPEN_DATE_REQUESTS = ("pending", "alternative_proposed", "awaiting_details")
ACTIVE_ORDERS = (
    OrderStatus.SUBMITTED.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
    OrderStatus.READY.value,
    OrderStatus.COMPLETED.value,
)


def block_end_of(row: ScheduleClosure) -> date:
    return row.first_eligible_date - timedelta(days=1)


def default_public_notice(first_eligible: date) -> str:
    return (
        "Recebemos pedidos para as fornadas disponíveis a partir de "
        f"{first_eligible.day} de {MONTH_NAMES[first_eligible.month]}."
    )


def public_notice_of(row: ScheduleClosure) -> str:
    text = (row.public_notice or "").strip()
    return text or default_public_notice(row.first_eligible_date)


def derived_status(row: ScheduleClosure, today: date) -> str:
    if row.cancelled_at is not None:
        return STATUS_CANCELLED
    if today < row.start_date:
        return STATUS_SCHEDULED
    if today < row.first_eligible_date or (
        row.pause_intake and row.start_date <= today <= row.end_date
    ):
        return STATUS_IN_FORCE
    return STATUS_CONCLUDED


def date_blocked_message(local_date: date, row: ScheduleClosure) -> str:
    return (
        f"{format_long_date(local_date)} não está disponível para novas encomendas. "
        f"{public_notice_of(row)} Escolha outra data; a seleção de pães permanece."
    )


def intake_paused_message() -> str:
    return "Neste momento não estamos recebendo novos pedidos."


def accept_block_message(local_date: date) -> str:
    return (
        f"{format_long_date(local_date)} está em um período fechado na Agenda. "
        "Reabra o bloqueio ou escolha outra data antes de reservar. "
        "A solicitação permanece."
    )


def _validate_payload(
    *,
    start_date: date,
    end_date: date,
    first_eligible_date: date,
    internal_reason: str,
) -> str:
    if end_date < start_date:
        raise ProductError("a data final não pode ser anterior à inicial")
    if first_eligible_date <= start_date:
        raise ProductError("a primeira fornada elegível precisa ser depois do início do período")
    reason = internal_reason.strip()
    if not reason or len(reason) > 120:
        raise ProductError("informe um motivo interno de até 120 caracteres")
    return reason


def load_active_closures(session: Session) -> list[ScheduleClosure]:
    return list(
        session.scalars(
            select(ScheduleClosure)
            .where(ScheduleClosure.cancelled_at.is_(None))
            .order_by(ScheduleClosure.start_date)
        )
    )


def matching_date_block(
    session: Session, local_date: date, *, rows: list[ScheduleClosure] | None = None
) -> ScheduleClosure | None:
    for row in rows if rows is not None else load_active_closures(session):
        if row.start_date <= local_date <= block_end_of(row):
            return row
    return None


def intake_paused_now(
    session: Session, settings: Settings, *, rows: list[ScheduleClosure] | None = None
) -> ScheduleClosure | None:
    today = bakery_today(settings)
    for row in rows if rows is not None else load_active_closures(session):
        if row.pause_intake and row.start_date <= today <= row.end_date:
            return row
    return None


def public_closure_notice(session: Session, settings: Settings) -> str | None:
    today = bakery_today(settings)
    notices: list[str] = []
    for row in load_active_closures(session):
        if derived_status(row, today) in {STATUS_SCHEDULED, STATUS_IN_FORCE}:
            text = public_notice_of(row)
            if text not in notices:
                notices.append(text)
    return notices[0] if notices else None


def _append_event(
    session: Session, row: ScheduleClosure, action: str, actor_ref: str, detail: dict | None
) -> None:
    session.add(
        ScheduleClosureEvent(
            closure_id=row.id,
            action=action,
            actor_ref=actor_ref,
            detail=detail,
        )
    )


def _snapshot(row: ScheduleClosure) -> dict:
    return {
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "first_eligible_date": row.first_eligible_date.isoformat(),
        "pause_intake": row.pause_intake,
        "internal_reason": row.internal_reason,
        "public_notice": row.public_notice,
    }


def commitments_in_range(
    session: Session, start: date, end: date
) -> dict:
    orders = session.scalars(
        select(Order)
        .where(
            Order.production_local_date >= start,
            Order.production_local_date <= end,
            Order.status.in_(ACTIVE_ORDERS),
        )
        .order_by(Order.production_local_date, Order.created_at)
    ).all()
    requests = session.scalars(
        select(DateRequest)
        .where(
            DateRequest.desired_date >= start,
            DateRequest.desired_date <= end,
            DateRequest.status.in_(OPEN_DATE_REQUESTS),
        )
        .order_by(DateRequest.desired_date, DateRequest.created_at)
    ).all()
    return {
        "orders": [
            {
                "id": str(item.id),
                "reference": item.public_reference,
                "date": item.production_local_date.isoformat() if item.production_local_date else None,
                "status": item.status,
                "href": "/admin/pedidos",
            }
            for item in orders
        ],
        "date_requests": [
            {
                "id": str(item.id),
                "date": item.desired_date.isoformat(),
                "status": item.status,
                "href": "/admin/pedidos",
            }
            for item in requests
        ],
        "order_count": len(orders),
        "date_request_count": len(requests),
    }


def serialize_closure(session: Session, settings: Settings, row: ScheduleClosure) -> dict:
    today = bakery_today(settings)
    blocked_until = block_end_of(row)
    commitments = commitments_in_range(session, row.start_date, blocked_until)
    return {
        "id": str(row.id),
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "first_eligible_date": row.first_eligible_date.isoformat(),
        "blocked_until": blocked_until.isoformat(),
        "pause_intake": row.pause_intake,
        "internal_reason": row.internal_reason,
        "public_notice": public_notice_of(row),
        "status": derived_status(row, today),
        "created_by": row.created_by,
        "updated_by": row.updated_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "cancelled_at": row.cancelled_at.isoformat() if row.cancelled_at else None,
        "cancelled_by": row.cancelled_by,
        "commitments": commitments,
    }


def list_closures(session: Session, settings: Settings) -> dict:
    rows = list(
        session.scalars(select(ScheduleClosure).order_by(ScheduleClosure.start_date.desc()))
    )
    today = bakery_today(settings)
    current = [row for row in rows if derived_status(row, today) != STATUS_CANCELLED]
    history = [row for row in rows if derived_status(row, today) == STATUS_CANCELLED]
    return {
        "items": [serialize_closure(session, settings, row) for row in current],
        "history": [serialize_closure(session, settings, row) for row in history],
    }


def _existing_active(session: Session, start_date: date, end_date: date) -> ScheduleClosure | None:
    return session.execute(
        select(ScheduleClosure)
        .where(
            ScheduleClosure.start_date == start_date,
            ScheduleClosure.end_date == end_date,
            ScheduleClosure.cancelled_at.is_(None),
        )
        .with_for_update()
    ).scalar_one_or_none()


def upsert_closure(
    session: Session,
    settings: Settings,
    *,
    start_date: date,
    end_date: date,
    first_eligible_date: date,
    pause_intake: bool,
    internal_reason: str,
    public_notice: str | None,
    actor_ref: str,
) -> ScheduleClosure:
    reason = _validate_payload(
        start_date=start_date,
        end_date=end_date,
        first_eligible_date=first_eligible_date,
        internal_reason=internal_reason,
    )
    notice = (public_notice or "").strip() or None
    actor = actor_ref.strip() or "admin:desconhecido"
    existing = _existing_active(session, start_date, end_date)
    if existing is not None:
        same = (
            existing.first_eligible_date == first_eligible_date
            and existing.pause_intake is pause_intake
            and existing.internal_reason == reason
            and (existing.public_notice or None) == notice
        )
        if same:
            return existing
        before = _snapshot(existing)
        existing.first_eligible_date = first_eligible_date
        existing.pause_intake = pause_intake
        existing.internal_reason = reason
        existing.public_notice = notice
        existing.updated_by = actor
        session.flush()
        _append_event(session, existing, "updated", actor, {"before": before, "after": _snapshot(existing)})
        session.flush()
        return existing
    row = ScheduleClosure(
        start_date=start_date,
        end_date=end_date,
        first_eligible_date=first_eligible_date,
        pause_intake=pause_intake,
        internal_reason=reason,
        public_notice=notice,
        created_by=actor,
        updated_by=actor,
    )
    session.add(row)
    session.flush()
    _append_event(session, row, "created", actor, _snapshot(row))
    session.flush()
    return row


def update_closure(
    session: Session,
    settings: Settings,
    closure_id: UUID,
    *,
    start_date: date,
    end_date: date,
    first_eligible_date: date,
    pause_intake: bool,
    internal_reason: str,
    public_notice: str | None,
    actor_ref: str,
) -> ScheduleClosure:
    del settings
    row = session.execute(
        select(ScheduleClosure).where(ScheduleClosure.id == closure_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("fechamento não encontrado")
    if row.cancelled_at is not None:
        raise ConfirmationError("este fechamento já foi reaberto; grave outro período se precisar")
    reason = _validate_payload(
        start_date=start_date,
        end_date=end_date,
        first_eligible_date=first_eligible_date,
        internal_reason=internal_reason,
    )
    other = session.scalar(
        select(ScheduleClosure).where(
            ScheduleClosure.id != row.id,
            ScheduleClosure.start_date == start_date,
            ScheduleClosure.end_date == end_date,
            ScheduleClosure.cancelled_at.is_(None),
        )
    )
    if other is not None:
        raise ConfirmationError("já existe um fechamento ativo com este intervalo de viagem")
    before = _snapshot(row)
    actor = actor_ref.strip() or row.updated_by
    row.start_date = start_date
    row.end_date = end_date
    row.first_eligible_date = first_eligible_date
    row.pause_intake = pause_intake
    row.internal_reason = reason
    row.public_notice = (public_notice or "").strip() or None
    row.updated_by = actor
    session.flush()
    _append_event(session, row, "updated", actor, {"before": before, "after": _snapshot(row)})
    session.flush()
    return row


def cancel_closure(
    session: Session, closure_id: UUID, *, actor_ref: str
) -> ScheduleClosure:
    row = session.execute(
        select(ScheduleClosure).where(ScheduleClosure.id == closure_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("fechamento não encontrado")
    if row.cancelled_at is not None:
        return row
    actor = actor_ref.strip() or row.updated_by
    row.cancelled_at = datetime.now(UTC)
    row.cancelled_by = actor
    row.updated_by = actor
    session.flush()
    _append_event(
        session,
        row,
        "cancelled",
        actor,
        {
            "effect": (
                "Remove só este bloqueio. A rotina e as outras exceções voltam a valer "
                "nos dias do intervalo. Isso não abre todos os dias nem apaga o histórico."
            )
        },
    )
    session.flush()
    return row


def list_closure_events(session: Session, closure_id: UUID) -> list[dict]:
    if session.get(ScheduleClosure, closure_id) is None:
        raise NotFoundError("fechamento não encontrado")
    rows = session.scalars(
        select(ScheduleClosureEvent)
        .where(ScheduleClosureEvent.closure_id == closure_id)
        .order_by(ScheduleClosureEvent.created_at.desc())
    ).all()
    return [
        {
            "id": str(item.id),
            "action": item.action,
            "actor_ref": item.actor_ref,
            "detail": item.detail,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in rows
    ]


def assert_new_entry_allowed(
    session: Session, settings: Settings, desired: date
) -> None:
    paused = intake_paused_now(session, settings)
    if paused is not None:
        raise ConfirmationError(intake_paused_message())
    blocked = matching_date_block(session, desired)
    if blocked is not None:
        raise ConfirmationError(date_blocked_message(desired, blocked))


def ensure_authorized_closure(
    session: Session,
    settings: Settings,
    *,
    start_date: date,
    end_date: date,
    first_eligible_date: date,
    pause_intake: bool,
    internal_reason: str,
    actor_ref: str,
) -> ScheduleClosure:
    """Idempotente: reusa ou corrige o fechamento do mesmo intervalo de viagem."""
    return upsert_closure(
        session,
        settings,
        start_date=start_date,
        end_date=end_date,
        first_eligible_date=first_eligible_date,
        pause_intake=pause_intake,
        internal_reason=internal_reason,
        public_notice=None,
        actor_ref=actor_ref,
    )
