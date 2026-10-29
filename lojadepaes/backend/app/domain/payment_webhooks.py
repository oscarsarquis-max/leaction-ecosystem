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


def _fill_empty_paid_metadata(record: PaymentRecord, event: PaymentIntegrationEvent, inner: dict) -> None:
    """Completa campos vazios de um pagamento já quitado. Não altera valor, data local nem estado."""
    incoming_id = str(inner.get("mp_payment_id") or "")[:80]
    if incoming_id and not record.mp_payment_id:
        record.mp_payment_id = incoming_id
    raw_status = str(inner.get("mp_status") or "")[:80]
    if raw_status and not record.external_status_raw:
        record.external_status_raw = raw_status
    if not record.method and inner.get("method") in {"pix", "card"}:
        record.method = inner["method"]
    refunded = inner.get("amount_refunded_cents")
    if record.amount_refunded_cents is None and isinstance(refunded, int) and not isinstance(refunded, bool):
        record.amount_refunded_cents = refunded
    approved_raw = inner.get("provider_approved_at")
    if approved_raw and event.provider_occurred_at is None:
        try:
            moment = datetime.fromisoformat(str(approved_raw).replace("Z", "+00:00"))
            if moment.tzinfo is not None:
                event.provider_occurred_at = moment
        except (ValueError, TypeError):
            pass


def _complete_recorded_paid_observation(session: Session, event: PaymentIntegrationEvent, inner: dict) -> None:
    """A mesma confirmação, já registrada, pode preencher o que a primeira gravação deixou vazio."""
    if event.process_status != EventProcessStatus.APPLIED.value or event.payment_record_id is None:
        return
    if str(inner.get("financial_status") or "").strip().lower() != FinancialStatus.PAID.value:
        return
    paid_cents = inner.get("paid_amount_cents")
    if not isinstance(paid_cents, int) or isinstance(paid_cents, bool):
        return
    record = session.get(PaymentRecord, event.payment_record_id)
    if record is None or record.financial_status != FinancialStatus.PAID.value:
        return
    if paid_cents != record.expected_cents or paid_cents != record.amount_paid_cents:
        return
    incoming_id = str(inner.get("mp_payment_id") or "")[:80]
    if incoming_id and record.mp_payment_id and incoming_id != record.mp_payment_id:
        return
    _fill_empty_paid_metadata(record, event, inner)
    session.flush()


def apply_actionhub_webhook(session: Session, settings: Settings, token: str) -> dict:
    if not settings.actionhub_app_secret.strip():
        raise ConfirmationError("ActionHub não configurado")
    try:
        claims = verify_hub_jwt(token, settings.actionhub_app_secret)
    except HubJwtError as exc:
        raise AuthError("notificação recusada") from exc
    return apply_actionhub_observation(session, settings, claims)


def apply_actionhub_observation(session: Session, settings: Settings, claims: dict) -> dict:
    """Apply an authenticated Hub webhook or authenticated reconciliation response.

    This internal function is never exposed as an unauthenticated HTTP endpoint.
    """
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
        _complete_recorded_paid_observation(session, existing, inner)
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
    if record is None and order_ref and not hub_order_id:
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

    record = session.scalar(
        select(PaymentRecord)
        .where(PaymentRecord.id == record.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    event.payment_record_id = record.id
    order = session.get(Order, record.order_id)
    if order is None:
        event.process_status = EventProcessStatus.IGNORED.value
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    if (order_ref and order_ref != order.public_reference) or (
        inner.get("currency") and inner["currency"] != record.currency
    ):
        event.process_status = EventProcessStatus.IGNORED.value
        event.sanitized_error = "referência ou moeda diverge da cobrança"
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
        if (
            not isinstance(paid_cents, int)
            or isinstance(paid_cents, bool)
            or paid_cents != expected
        ):
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

    if (
        record.financial_status == FinancialStatus.PAID.value
        and incoming == FinancialStatus.PAID.value
    ):
        incoming_id = str(inner.get("mp_payment_id") or "")[:80]
        if incoming_id and record.mp_payment_id and incoming_id != record.mp_payment_id:
            event.process_status = EventProcessStatus.IGNORED.value
            event.sanitized_error = "identificador de pagamento já registrado"
            session.flush()
            return {"duplicate": False, "process_status": event.process_status}
        _fill_empty_paid_metadata(record, event, inner)
        verified = bool(record.mp_payment_id) and record.amount_paid_cents == record.expected_cents
        if verified:
            record.last_synced_at = datetime.now(UTC)
            record.sanitized_error = None
        event.process_status = EventProcessStatus.APPLIED.value
        session.flush()
        return {"duplicate": False, "process_status": event.process_status}

    was_paid = record.financial_status == FinancialStatus.PAID.value
    record.financial_status = incoming
    record.external_status_raw = str(inner.get("mp_status") or incoming)[:80]
    record.last_synced_at = datetime.now(UTC)
    if inner.get("mp_payment_id"):
        record.mp_payment_id = str(inner["mp_payment_id"])[:80]
    if inner.get("method") in {"pix", "card"}:
        record.method = inner["method"]
    for field in ("provider_observed_at", "provider_approved_at"):
        raw = inner.get(field)
        if raw:
            try:
                moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if moment.tzinfo is not None:
                    if field == "provider_observed_at":
                        event.provider_occurred_at = moment
                    elif incoming == FinancialStatus.PAID.value:
                        record.confirmed_at = moment
            except (ValueError, TypeError):
                pass
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
    from app.domain.house_fidelity_ledger import reconcile_order

    reconcile_order(session, settings, order)
    return {"duplicate": False, "process_status": event.process_status}
