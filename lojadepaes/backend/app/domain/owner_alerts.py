"""Alertas do proprietário. E-mail reutiliza a outbox. O link manual da home não envia alerta."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.managerial_exclusion import active_exclusion_sets
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsChannelSetting, OpsOwnerAlert
from app.models.orders import Order, OrderItem

_WHATSAPP_BLOCK = (
    "O atendimento por WhatsApp da home continua manual. "
    "O envio automático de alertas ainda não tem adaptador de envio; "
    "nenhuma mensagem automática foi enviada."
)
_PHONE = re.compile(r"^\+[1-9]\d{8,14}$")


def _excluded(session: Session, order_id: UUID | None, date_request_id: UUID | None) -> bool:
    orders, dates = active_exclusion_sets(session)
    if order_id is not None and order_id in orders:
        return True
    if date_request_id is not None and date_request_id in dates:
        return True
    return False


def _items_text(session: Session, order: Order) -> str:
    rows = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    parts = []
    for row in rows:
        name = (row.dough_name_snapshot or row.shape_name_snapshot or "pão").strip()
        parts.append(f"{row.quantity}× {name}")
    return ", ".join(parts) if parts else "itens no painel"


def _money(cents: int | None) -> str:
    if cents is None:
        return "valor a definir"
    return f"R$ {cents / 100:.2f}".replace(".", ",")


def _date_bits(order: Order) -> tuple[str, str]:
    if order.production_local_date is not None:
        return "Data da fornada", order.production_local_date.isoformat()
    if order.proposed_production_date is not None:
        return "Data desejada", order.proposed_production_date.isoformat()
    return "Data", "sem data definida"


def order_summary(session: Session, settings: Settings, order: Order, title: str) -> str:
    label, day = _date_bits(order)
    link = f"{settings.public_origin.rstrip('/')}/admin/pedidos/{order.id}"
    text = (
        f"{title} {order.public_reference}. "
        f"Cliente: {(order.customer_name or 'não informado').strip()}. "
        f"{label}: {day}. "
        f"Itens: {_items_text(session, order)}. "
        f"Valor: {_money(order.total_cents)}. "
        f"Estado: {order.status}. "
        f"Painel: {link}"
    )
    return text[:500]


def request_summary(settings: Settings, request: DateRequest) -> str:
    from app.domain.attendance import date_request_reference

    link = f"{settings.public_origin.rstrip('/')}/admin/pedidos/solicitacao/{request.id}"
    text = (
        f"Nova solicitação {date_request_reference(request.id)}. "
        f"Cliente: {request.customer_name.strip()}. "
        f"Data desejada: {request.desired_date.isoformat()}. "
        f"Isto ainda não é pedido aceito. "
        f"Painel: {link}"
    )
    return text[:500]


def _email_status(row: EmailOutbox) -> tuple[str, str | None]:
    if row.status == "pending":
        return "awaiting", None
    if row.status == "sent":
        return "accepted", None
    if row.status == "failed":
        return "failed", (row.last_error or "falha no envio")[:280]
    return "disabled", (row.last_error or "envio não disparado")[:280]


def _upsert(
    session: Session,
    *,
    channel: str,
    event_key: str,
    kind: str,
    order_id: UUID | None,
    date_request_id: UUID | None,
    status: str,
    summary: str,
    last_error: str | None,
    email_outbox_id: UUID | None = None,
) -> OpsOwnerAlert:
    existing = session.scalar(
        select(OpsOwnerAlert).where(
            OpsOwnerAlert.event_key == event_key,
            OpsOwnerAlert.channel == channel,
        )
    )
    if existing is not None:
        return existing
    row = OpsOwnerAlert(
        channel=channel,
        event_key=event_key[:160],
        kind=kind[:40],
        order_id=order_id,
        date_request_id=date_request_id,
        status=status,
        summary=summary[:500],
        last_error=last_error,
        attempts=0,
        email_outbox_id=email_outbox_id,
    )
    session.add(row)
    session.flush()
    return row


def whatsapp_block_reason(settings: Settings, destination: str, enabled: bool) -> str | None:
    provider = (settings.whatsapp_provider or "").strip().lower()
    if provider in {"", "browser", "wa.me", "web"}:
        return _WHATSAPP_BLOCK
    if not enabled or not _PHONE.match(destination):
        return _WHATSAPP_BLOCK
    if not settings.whatsapp_ops_enabled:
        return _WHATSAPP_BLOCK
    return None


def _whatsapp_destination(session: Session, settings: Settings) -> tuple[str, bool]:
    row = session.get(OpsChannelSetting, "whatsapp")
    destination = (row.destination if row is not None else "") or (settings.whatsapp_ops_to or "")
    destination = destination.strip()
    enabled = bool(row and row.enabled)
    return destination, enabled


def record_owner_event(
    session: Session,
    settings: Settings,
    *,
    event_key: str,
    kind: str,
    summary: str,
    email_row: EmailOutbox | None,
    order_id: UUID | None,
    date_request_id: UUID | None,
) -> None:
    if _excluded(session, order_id, date_request_id):
        return
    if email_row is not None:
        status, error = _email_status(email_row)
        _upsert(
            session,
            channel="email",
            event_key=event_key,
            kind=kind,
            order_id=order_id,
            date_request_id=date_request_id,
            status=status,
            summary=summary,
            last_error=error,
            email_outbox_id=email_row.id,
        )
    destination, enabled = _whatsapp_destination(session, settings)
    block = whatsapp_block_reason(settings, destination, enabled)
    _upsert(
        session,
        channel="whatsapp",
        event_key=event_key,
        kind=kind,
        order_id=order_id,
        date_request_id=date_request_id,
        status="disabled" if block else "awaiting",
        summary=summary,
        last_error=block,
    )
    from app.domain.web_push import enqueue_event_pushes

    enqueue_event_pushes(
        session,
        settings,
        event_key=event_key,
        kind=kind,
        order_id=order_id,
        date_request_id=date_request_id,
    )


def note_admin_email(
    session: Session,
    settings: Settings,
    row: EmailOutbox,
    *,
    summary: str,
    title_kind: str,
) -> None:
    record_owner_event(
        session,
        settings,
        event_key=row.dedupe_key or f"outbox:{row.id}",
        kind=title_kind,
        summary=summary,
        email_row=row,
        order_id=row.order_id,
        date_request_id=row.date_request_id,
    )


def notify_acceptance(
    session: Session, settings: Settings, order: Order, request: DateRequest
) -> None:
    """Aceite de solicitação: um aviso correlato, não um segundo pedido."""
    if _excluded(session, order.id, request.id):
        return
    event_key = f"acceptance:{request.id}:{order.id}"
    existing = session.scalar(
        select(EmailOutbox).where(EmailOutbox.dedupe_key == event_key)
    )
    dest = (settings.mail_ops_to or "").strip()
    configured = bool(dest) and "@" in dest
    ready = settings.mail_transport_ready and configured
    summary = order_summary(session, settings, order, "Aceite da solicitação")
    if existing is None:
        existing = EmailOutbox(
            order_id=order.id,
            date_request_id=request.id,
            kind="acceptance_update_admin",
            to_address=dest if configured else "ops-unconfigured",
            subject=f"Aceite da solicitação — pedido {order.public_reference}",
            body=summary,
            status="pending" if ready else "skipped",
            attempts=0,
            last_error=None if ready else "destinatário ou transporte de e-mail indisponível",
            dedupe_key=event_key,
        )
        session.add(existing)
        session.flush()
    record_owner_event(
        session,
        settings,
        event_key=event_key,
        kind="acceptance_update",
        summary=summary,
        email_row=existing,
        order_id=order.id,
        date_request_id=request.id,
    )


def save_whatsapp_destination(session: Session, number: str, *, author_ref: str) -> dict:
    digits = re.sub(r"[^\d+]", "", number.strip())
    if digits.startswith("00"):
        digits = f"+{digits[2:]}"
    if digits and not digits.startswith("+"):
        digits = f"+{digits}"
    if not _PHONE.match(digits):
        raise ValueError("informe o número com DDI e DDD, no formato +5585...")
    row = session.get(OpsChannelSetting, "whatsapp")
    if row is None:
        row = OpsChannelSetting(channel="whatsapp", destination=digits, enabled=False)
        session.add(row)
    row.destination = digits
    row.enabled = False
    row.updated_by = author_ref[:120]
    row.updated_at = datetime.now(UTC)
    session.flush()
    return {"destination": digits, "enabled": False, "block": _WHATSAPP_BLOCK}


def channel_status(session: Session, settings: Settings) -> dict:
    destination, enabled = _whatsapp_destination(session, settings)
    block = whatsapp_block_reason(settings, destination, enabled)
    email_ready = bool((settings.mail_ops_to or "").strip()) and "@" in (settings.mail_ops_to or "")
    return {
        "email": {
            "active": bool(email_ready and settings.mail_transport_ready),
            "destination_configured": email_ready,
            "delivery_confirmed": False,
        },
        "whatsapp": {
            "active": block is None,
            "destination_configured": bool(_PHONE.match(destination)),
            "delivery_confirmed": False,
            "block": block,
        },
    }


def recent_alert_failures(session: Session) -> list[dict]:
    rows = session.scalars(
        select(OpsOwnerAlert)
        .where(OpsOwnerAlert.status.in_(("failed", "disabled")))
        .order_by(OpsOwnerAlert.created_at.desc())
        .limit(8)
    )
    return [
        {
            "id": str(row.id),
            "channel": row.channel,
            "kind": row.kind,
            "status": row.status,
            "last_error": row.last_error,
        }
        for row in rows
    ]


def retry_owner_alert(session: Session, settings: Settings, alert_id: UUID) -> OpsOwnerAlert:
    row = session.get(OpsOwnerAlert, alert_id)
    if row is None:
        raise LookupError("alerta não encontrado")
    if row.status != "failed":
        return row
    if row.channel == "whatsapp":
        destination, enabled = _whatsapp_destination(session, settings)
        block = whatsapp_block_reason(settings, destination, enabled)
        row.attempts += 1
        row.updated_at = datetime.now(UTC)
        if block:
            row.status = "disabled"
            row.last_error = block
        else:
            row.status = "failed"
            row.last_error = "provedor oficial ainda sem envio comprovado"
        session.flush()
        return row
    row.attempts += 1
    row.updated_at = datetime.now(UTC)
    session.flush()
    return row
