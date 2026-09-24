from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.email_outbox import enqueue_order_email
from app.domain.errors import AuthError, ConfirmationError
from app.domain.hub_jwt import HubJwtError, verify_hub_jwt
from app.models.enums import EventProcessStatus, FinancialStatus
from app.models.orders import Order
from app.models.payments import PaymentIntegrationEvent, PaymentRecord

TERMINAL_FORWARD = {
    FinancialStatus.PENDING.value: 1,
    FinancialStatus.FAILED.value: 2,
    FinancialStatus.CANCELLED.value: 2,
    FinancialStatus.UNKNOWN.value: 2,
    FinancialStatus.PAID.value: 3,
    FinancialStatus.PARTIALLY_REFUNDED.value: 4,
    FinancialStatus.REFUNDED.value: 5,
}


def _inner_payload(claims: dict) -> dict:
    payload = claims.get("payload")
    if isinstance(payload, dict):
        return payload
    return claims


def apply_actionhub_webhook(session: Session, settings: Settings, token: str) -> dict:
    if not settings.actionhub_app_secret.strip():
        raise ConfirmationError("ActionHub não configurado")
    try:
        claims = verify_hub_jwt(token, settings.actionhub_app_secret)
    except HubJwtError as exc:
        raise AuthError("notificação recusada") from exc
    if str(claims.get("app_id") or "").lower() != settings.actionhub_app_id.lower():
        raise AuthError("notificação de outro aplicativo")
    inner = _inner_payload(claims)
    event_id = str(claims.get("outbox_id") or claims.get("idempotency_key") or "").strip()
    if not event_id:
        raise ConfirmationError("evento sem identificador estável")
    existing = session.scalar(
        select(PaymentIntegrationEvent).where(
            PaymentIntegrationEvent.provider == "actionhub",
            PaymentIntegrationEvent.external_event_id == event_id,
        )
    )
    if existing is not None:
        return {"duplicate": True, "process_status": existing.process_status}

    event = PaymentIntegrationEvent(
        provider="actionhub",
        external_event_id=event_id,
        external_type=str(claims.get("event_type") or inner.get("event_type") or ""),
        received_at=datetime.now(UTC),
        process_status=EventProcessStatus.RECEIVED.value,
    )
    session.add(event)
    session.flush()

    order_ref = str(inner.get("order_reference") or "").strip()
    hub_order_id = str(inner.get("order_id") or "").strip()
    record = None
    if hub_order_id:
        record = session.scalar(
            select(PaymentRecord).where(
                PaymentRecord.provider == "actionhub",
                PaymentRecord.external_reference == hub_order_id,
            )
        )
    if record is None and order_ref:
        order = session.scalar(select(Order).where(Order.public_reference == order_ref))
        if order is not None:
            record = session.scalar(
                select(PaymentRecord)
                .where(PaymentRecord.order_id == order.id)
                .order_by(PaymentRecord.created_at.desc())
            )
    if record is None:
        event.process_status = EventProcessStatus.IGNORED.value
        event.sanitized_error = "evento sem cobrança associada"
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    event.payment_record_id = record.id
    order = session.get(Order, record.order_id)
    if order is None:
        event.process_status = EventProcessStatus.IGNORED.value
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    incoming = str(inner.get("financial_status") or "").strip().lower()
    if incoming not in {item.value for item in FinancialStatus}:
        event.process_status = EventProcessStatus.IGNORED.value
        event.sanitized_error = "estado financeiro desconhecido"
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    paid_cents = inner.get("paid_amount_cents")
    expected = record.expected_cents
    if incoming == FinancialStatus.PAID.value:
        if paid_cents is not None and int(paid_cents) != expected:
            event.process_status = EventProcessStatus.IGNORED.value
            event.sanitized_error = "valor aprovado diverge do esperado"
            record.sanitized_error = "valor aprovado diverge do esperado"
            session.flush()
            return {"duplicate": False, "process_status": event.process_status}
        if (
            record.financial_status == FinancialStatus.PAID.value
            and record.amount_paid_cents
            and paid_cents
            and int(paid_cents) != record.amount_paid_cents
        ):
            event.process_status = EventProcessStatus.IGNORED.value
            event.sanitized_error = "pagamento duplicado inesperado"
            record.sanitized_error = "pagamento duplicado inesperado"
            session.flush()
            return {"duplicate": False, "process_status": event.process_status}

    current_rank = TERMINAL_FORWARD.get(record.financial_status, 0)
    incoming_rank = TERMINAL_FORWARD.get(incoming, 0)
    if incoming_rank < current_rank:
        event.process_status = EventProcessStatus.IGNORED.value
        event.sanitized_error = "evento fora de ordem ignorado"
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    was_paid = record.financial_status == FinancialStatus.PAID.value
    record.financial_status = incoming
    record.external_status_raw = str(inner.get("mp_status") or incoming)[:80]
    record.last_synced_at = datetime.now(UTC)
    if incoming == FinancialStatus.PAID.value:
        record.amount_paid_cents = expected
        record.confirmed_at = record.confirmed_at or datetime.now(UTC)
        record.sanitized_error = None
        enqueue_order_email(session, settings, order, "payment_approved")
    elif incoming == FinancialStatus.REFUNDED.value:
        record.amount_refunded_cents = record.amount_paid_cents or expected
    elif incoming == FinancialStatus.PARTIALLY_REFUNDED.value:
        refunded = inner.get("amount_refunded_cents")
        record.amount_refunded_cents = int(refunded) if refunded is not None else None
    elif incoming in {FinancialStatus.FAILED.value, FinancialStatus.CANCELLED.value}:
        record.sanitized_error = str(inner.get("mp_status") or incoming)

    event.process_status = EventProcessStatus.APPLIED.value
    session.flush()
    if incoming == FinancialStatus.PAID.value and not was_paid:
        from app.domain.crm_tracking import emit_order_fact

        emit_order_fact(session, settings, order, "pagamento_registrar", situacao="paid")
    return {"duplicate": False, "process_status": event.process_status}
