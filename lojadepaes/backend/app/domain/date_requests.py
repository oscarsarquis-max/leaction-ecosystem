from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.bakery_time import bakery_today
from app.domain.capacity import utc_now
from app.domain.email_outbox import enqueue_admin_date_request_email, enqueue_date_request_email
from app.domain.errors import ConfirmationError, NotFoundError, RateLimitError
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.products import Product, ProductVariant
from app.schemas.suggestions import (
    QUANTITY_REQUIRED_MESSAGE,
    DateRequestActionIn,
    DateRequestCreateIn,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUS_PENDING = "pending"
STATUS_PROPOSED = "alternative_proposed"
STATUS_CLOSED = "closed"
STATUS_AWAITING = "awaiting_details"
STATUS_CONVERTED = "converted"
MAX_PER_EMAIL = 5
MAX_PER_HOST = 12
WINDOW_MINUTES = 30


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if not EMAIL_RE.fullmatch(cleaned) or len(cleaned) > 254:
        raise ConfirmationError("informe um e-mail válido")
    return cleaned


def _name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 160:
        raise ConfirmationError("informe o nome de quem devemos responder")
    return cleaned


def _append_event(
    session: Session, request: DateRequest, action: str, actor_ref: str | None, detail: str | None
) -> None:
    session.add(
        DateRequestEvent(request_id=request.id, action=action, actor_ref=actor_ref, detail=detail)
    )


def _rate_limit(session: Session, email: str, host: str) -> None:
    since = utc_now() - timedelta(minutes=WINDOW_MINUTES)
    by_email = session.scalar(
        select(func.count())
        .select_from(DateRequest)
        .where(DateRequest.customer_email == email, DateRequest.created_at >= since)
    )
    if int(by_email or 0) >= MAX_PER_EMAIL:
        raise RateLimitError("muitas solicitações deste e-mail; aguarde um pouco")
    by_host = session.scalar(
        select(func.count())
        .select_from(DateRequest)
        .where(DateRequest.client_host == host, DateRequest.created_at >= since)
    )
    if int(by_host or 0) >= MAX_PER_HOST:
        raise RateLimitError("muitas solicitações neste momento; aguarde um pouco")


def _cart_snapshot(session: Session, lines: list) -> tuple[list[dict], int]:
    snapshot: list[dict] = []
    physical = 0
    for line in lines:
        variant = session.get(ProductVariant, line.variant_id)
        if variant is None:
            raise ConfirmationError("uma variação da seleção não existe mais")
        product = session.get(Product, variant.product_id)
        if product is None:
            raise ConfirmationError("um pão da seleção não existe mais")
        units = variant.physical_units if variant.physical_units is not None else 1
        physical += units * line.quantity
        snapshot.append(
            {
                "product_id": str(product.id),
                "variant_id": str(variant.id),
                "product_name": product.name,
                "variant_name": variant.display_name,
                "quantity": line.quantity,
            }
        )
    return snapshot, physical


def create_date_request(
    session: Session,
    settings: Settings,
    payload: DateRequestCreateIn,
    *,
    client_host: str,
) -> DateRequest:
    existing = session.scalar(
        select(DateRequest).where(DateRequest.idempotency_key == payload.idempotency_key.strip())
    )
    if existing is not None:
        return existing
    today = bakery_today(settings)
    if payload.desired_date < today:
        raise ConfirmationError("data passada não pode ser solicitada")
    from app.domain.schedule_closures import assert_new_entry_allowed

    assert_new_entry_allowed(session, settings, payload.desired_date)
    name = _name(payload.customer_name)
    email = _email(payload.customer_email)
    message = (payload.message or "").strip() or None
    if message and len(message) > 2000:
        raise ConfirmationError("a mensagem é longa demais")
    snapshot: list[dict] = []
    quantity = payload.intended_quantity
    if payload.lines:
        snapshot, derived = _cart_snapshot(session, payload.lines)
        if quantity is None:
            quantity = derived
    elif quantity is None or quantity < 1:
        raise ConfirmationError(QUANTITY_REQUIRED_MESSAGE)
    _rate_limit(session, email, client_host[:80])
    request = DateRequest(
        desired_date=payload.desired_date,
        customer_name=name,
        customer_email=email,
        intended_quantity=quantity,
        message=message,
        status=STATUS_PENDING,
        cart_context=snapshot or None,
        idempotency_key=payload.idempotency_key.strip(),
        client_host=client_host[:80],
    )
    session.add(request)
    session.flush()
    _append_event(
        session,
        request,
        "created",
        None,
        f"data desejada {payload.desired_date.isoformat()}",
    )
    enqueue_date_request_email(session, settings, request, "date_request_received")
    enqueue_admin_date_request_email(session, settings, request)
    session.flush()
    return request


def list_date_requests(session: Session) -> list[DateRequest]:
    return list(
        session.scalars(
            select(DateRequest)
            .options(selectinload(DateRequest.events))
            .order_by(DateRequest.created_at.desc())
        )
    )


def apply_date_request_action(
    session: Session,
    settings: Settings,
    request_id: UUID,
    payload: DateRequestActionIn,
    *,
    actor_ref: str,
) -> DateRequest:
    request = session.execute(
        select(DateRequest).where(DateRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()
    if request is None:
        raise NotFoundError("solicitação não encontrada")
    if request.status == STATUS_CONVERTED and payload.action == "accept":
        return get_date_request(session, request.id)
    if request.status in {STATUS_CLOSED, STATUS_CONVERTED}:
        raise ConfirmationError("esta solicitação já foi encerrada")
    note = (payload.note or "").strip() or None
    if payload.action == "request_completion":
        from app.domain.date_request_accept import request_date_request_completion

        completed = request_date_request_completion(
            session, settings, request, note=note, actor_ref=actor_ref
        )
        return get_date_request(session, completed.id)
    if payload.action == "accept":
        from app.domain.date_request_accept import accept_date_request

        accepted = accept_date_request(session, settings, request, payload, actor_ref=actor_ref)
        return get_date_request(session, accepted.id)
    if payload.action == "propose":
        if payload.proposed_date is None:
            raise ConfirmationError("informe a data alternativa")
        if payload.proposed_date == request.desired_date:
            raise ConfirmationError(
                "para aceitar a data pedida, use o aceite; para propor, escolha outra data"
            )
        today = bakery_today(settings)
        if payload.proposed_date < today:
            raise ConfirmationError("a data alternativa precisa ser hoje ou futura")
        request.proposed_date = payload.proposed_date
        request.status = STATUS_PROPOSED
        request.admin_note = note
        _append_event(
            session,
            request,
            "proposed",
            actor_ref,
            f"alternativa {payload.proposed_date.isoformat()}" + (f" — {note}" if note else ""),
        )
        enqueue_date_request_email(session, settings, request, "date_request_proposed", note=note)
        session.flush()
        return get_date_request(session, request.id)
    if payload.action != "close":
        raise ConfirmationError("ação não reconhecida")
    if not note:
        raise ConfirmationError("escreva a justificativa que será enviada ao cliente")
    dest = (request.customer_email or "").strip()
    if not dest or "@" not in dest:
        raise ConfirmationError("esta solicitação não tem e-mail válido para avisar o cliente")
    request.admin_note = note
    try:
        enqueue_date_request_email(session, settings, request, "date_request_declined", note=note)
    except ValueError as exc:
        raise ConfirmationError(str(exc)) from exc
    request.status = STATUS_CLOSED
    request.closed_at = datetime.now(UTC)
    _append_event(session, request, "closed", actor_ref, "justificativa enviada ao cliente")
    session.flush()
    return get_date_request(session, request.id)


def date_request_allowed_actions(request: DateRequest) -> list[str]:
    if request.status in {STATUS_CLOSED, STATUS_CONVERTED}:
        return []
    return ["accept", "propose", "close", "request_completion"]


def date_request_reply_preview(settings: Settings) -> str:
    del settings
    return (
        "Aceitar a data pedida formaliza o pedido, reserva a fornada "
        "e envia o link protegido de pagamento, mesmo sem endereço completo. "
        "Endereço ausente vira pendência de entrega — não bloqueia o aceite. "
        "Se faltarem pães ou quantidade, o detalhe mostra essa falta específica. "
        "Propor outra data não reserva nem cria cobrança; o cliente precisa responder. "
        "Encerrar exige justificativa enviada por e-mail; não há encerramento sem aviso."
    )


def get_date_request(session: Session, request_id: UUID) -> DateRequest:
    request = session.scalar(
        select(DateRequest)
        .options(selectinload(DateRequest.events))
        .where(DateRequest.id == request_id)
    )
    if request is None:
        raise NotFoundError("solicitação não encontrada")
    return request
