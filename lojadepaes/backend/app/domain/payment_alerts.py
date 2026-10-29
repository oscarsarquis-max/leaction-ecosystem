"""Alerta operacional quando a verificação financeira falha de forma persistente.

Aguardar o cliente pagar não é falha. O limiar é 90 segundos depois que a ocorrência abre.
Pendente e desconhecido são revistos a cada 30 segundos. Um registro já pago só é
selecionado de novo após 5 minutos, então o aviso pode sair nessa conferência seguinte.
Uma ocorrência gera um e-mail e um push por aparelho; os ciclos seguintes não repetem.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsOwnerAlert
from app.models.orders import Order
from app.models.payments import PaymentIntegrationEvent, PaymentRecord

PERSISTENT_SYNC_FAILURE = timedelta(seconds=90)
ALERT_KIND = "payment_sync_alert"
_MARKERS = (
    "indisponível",
    "falhou",
    "falha",
    "diverge",
    "não foi localizada",
    "falta confirmação",
)


def sync_failure_class(record: PaymentRecord) -> str | None:
    text = (record.sanitized_error or "").strip().lower()
    if not text or not any(marker in text for marker in _MARKERS):
        return None
    return "verificacao"


def review_sync_alert(
    session: Session,
    settings: Settings,
    order: Order,
    record: PaymentRecord,
    now: datetime,
) -> None:
    kind = sync_failure_class(record)
    open_watch = session.scalar(
        select(PaymentIntegrationEvent)
        .where(
            PaymentIntegrationEvent.provider == "actionhub",
            PaymentIntegrationEvent.external_event_id.like(f"sync-watch:{record.id}:%"),
            PaymentIntegrationEvent.process_status == "received",
        )
        .order_by(PaymentIntegrationEvent.received_at.asc())
    )
    if kind is None:
        if open_watch is not None:
            open_watch.process_status = "applied"
            _close_alert(session, open_watch.external_event_id, now)
        return
    if open_watch is None:
        open_watch = PaymentIntegrationEvent(
            provider="actionhub",
            external_event_id=f"sync-watch:{record.id}:{int(now.timestamp())}",
            external_type="SYNC_WATCH",
            payment_record_id=record.id,
            received_at=now,
            process_status="received",
            sanitized_error=kind,
        )
        session.add(open_watch)
        session.flush()
    if now - open_watch.received_at < PERSISTENT_SYNC_FAILURE:
        return
    _enqueue_once(session, settings, order, record, open_watch.external_event_id, now)


def _enqueue_once(
    session: Session,
    settings: Settings,
    order: Order,
    record: PaymentRecord,
    event_key: str,
    now: datetime,
) -> None:
    existing = session.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == event_key))
    if existing is not None:
        return
    checked = now.isoformat()
    link = f"{settings.public_origin.rstrip('/')}/admin/pedidos/{order.id}"
    nature = (record.sanitized_error or "verificação financeira sem confirmação").strip()
    body = (
        f"Pedido {order.public_reference}.\n"
        f"Natureza: {nature}\n"
        f"Última verificação: {checked}.\n"
        "Isto não significa que o cliente deixou de pagar.\n"
        f"Registro administrativo: {link}\n"
    )
    dest = (settings.mail_ops_to or "").strip()
    configured = "@" in dest
    ready = bool(settings.mail_transport_ready and configured)
    row = EmailOutbox(
        order_id=order.id,
        kind=ALERT_KIND,
        to_address=dest if configured else "ops-unconfigured",
        subject=f"Verificar pagamento — {order.public_reference}",
        body=body,
        status="pending" if ready else "skipped",
        attempts=0,
        last_error=None if ready else "destinatário ou transporte indisponível",
        dedupe_key=event_key,
    )
    session.add(row)
    session.flush()
    from app.domain.owner_alerts import record_owner_event

    record_owner_event(
        session,
        settings,
        event_key=event_key,
        kind=ALERT_KIND,
        summary=body.replace("\n", " ")[:500],
        email_row=row,
        order_id=order.id,
        date_request_id=None,
    )


def _close_alert(session: Session, event_key: str, now: datetime) -> None:
    rows = list(
        session.scalars(select(OpsOwnerAlert).where(OpsOwnerAlert.event_key == event_key))
    )
    note = f" Ocorrência encerrada após a verificação de {now.isoformat()}."
    for row in rows:
        if "encerrada" in (row.summary or ""):
            continue
        row.summary = (row.summary + note)[:500]
    session.flush()
