from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.bakery_time import bakery_today
from app.domain.capacity import utc_now
from app.domain.email_outbox import enqueue_date_request_email
from app.domain.errors import ConfirmationError, NotFoundError, RateLimitError
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.products import Product, ProductVariant
from app.schemas.suggestions import DateRequestActionIn, DateRequestCreateIn

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUS_PENDING = "pending"
STATUS_PROPOSED = "alternative_proposed"
STATUS_CLOSED = "closed"
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
        raise ConfirmationError("escolha uma data futura")
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
    elif quantity is None:
        raise ConfirmationError("informe a quantidade pretendida")
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
    request = session.get(DateRequest, request_id)
    if request is None:
        raise NotFoundError("solicitação não encontrada")
    if request.status == STATUS_CLOSED:
        raise ConfirmationError("esta solicitação já foi encerrada")
    note = (payload.note or "").strip() or None
    if payload.action == "propose":
        if payload.proposed_date is None:
            raise ConfirmationError("informe a data alternativa")
        if payload.proposed_date < bakery_today(settings):
            raise ConfirmationError("a data alternativa precisa ser futura")
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
        enqueue_date_request_email(session, settings, request, "date_request_proposed")
        session.flush()
        return request
    request.status = STATUS_CLOSED
    request.closed_at = datetime.now(UTC)
    request.admin_note = note
    _append_event(session, request, "closed", actor_ref, note)
    session.flush()
    return request
