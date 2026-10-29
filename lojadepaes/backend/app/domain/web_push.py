"""Inscrições Web Push e entregas. Não envia histórico nem usa telefone."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.date_requests import DateRequest
from app.models.managerial import AdminPushSubscription, OpsPushDelivery
from app.models.orders import Order

LOG = logging.getLogger("lojadepaes.push")
_MAX_ATTEMPTS = 3
_KEY = re.compile(r"^[A-Za-z0-9_-]{16,200}$")
_HOSTS = {
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "web.push.apple.com",
}
_KINDS = {
    "order_submitted_admin": (
        "Loja de Pães — Novo pedido recebido",
        "{ref}. Abra o painel para ver.",
    ),
    "order_auto_accepted_admin": (
        "Loja de Pães — Novo pedido recebido",
        "{ref}. Abra o painel para ver.",
    ),
    "date_request_received_admin": (
        "Loja de Pães — Nova solicitação",
        "{ref}. Ainda não é um pedido aceito.",
    ),
    "acceptance_update": (
        "Loja de Pães — Solicitação aceita",
        "Pedido {ref}. Abra o painel para ver.",
    ),
    "payment_sync_alert": (
        "Loja de Pães — Verificar pagamento",
        "{ref}. A verificação financeira falhou. Abra o painel. Não conclua que o cliente não pagou.",
    ),
    "test": (
        "Loja de Pães — Notificação de teste",
        "Este aviso é só um teste. Abra o painel se quiser conferir.",
    ),
}


def vapid_configured(settings: Settings) -> bool:
    public = (settings.vapid_public_key or "").strip()
    private = (settings.vapid_private_key or "").strip()
    if not _KEY.fullmatch(public) or not _KEY.fullmatch(private):
        return False
    derived = _public_from_private(private)
    return bool(
        derived
        and len(derived) == len(public)
        and hmac.compare_digest(derived, public)
    )


def actor_may_receive(settings: Settings, actor_ref: str) -> bool:
    username = settings.admin_username.strip()
    if not username or not settings.admin_enabled:
        return False
    expected = f"admin:{username}"
    if len(actor_ref) != len(expected):
        return False
    return hmac.compare_digest(actor_ref, expected)


def push_status(settings: Settings) -> dict:
    ready = vapid_configured(settings)
    return {
        "configured": ready,
        "public_key": settings.vapid_public_key.strip() if ready else "",
        "receipt_confirmed": False,
    }


def validate_subscription(endpoint: str, p256dh: str, auth_secret: str) -> None:
    parts = urlsplit(endpoint.strip())
    host = (parts.hostname or "").lower()
    allowed_host = host in _HOSTS or host.endswith(".notify.windows.com")
    if (
        parts.scheme != "https"
        or parts.username
        or parts.password
        or parts.port not in {None, 443}
        or not allowed_host
        or not parts.path
        or parts.path == "/"
    ):
        raise ValueError("inscrição rejeitada")
    if not _KEY.fullmatch(p256dh) or not _KEY.fullmatch(auth_secret):
        raise ValueError("inscrição rejeitada")


def save_subscription(
    session: Session,
    settings: Settings,
    *,
    actor_ref: str,
    endpoint: str,
    p256dh: str,
    auth_secret: str,
    label: str,
) -> AdminPushSubscription:
    if not actor_may_receive(settings, actor_ref):
        raise ValueError("conta administrativa sem permissão para receber avisos")
    validate_subscription(endpoint, p256dh, auth_secret)
    digest = hashlib.sha256(endpoint.strip().encode("utf-8")).hexdigest()
    clean_label = _label(label)
    row = session.scalar(
        select(AdminPushSubscription).where(AdminPushSubscription.endpoint_hash == digest)
    )
    now = datetime.now(UTC)
    if row is None:
        row = AdminPushSubscription(
            actor_ref=actor_ref,
            endpoint=endpoint.strip(),
            endpoint_hash=digest,
            p256dh=p256dh,
            auth_secret=auth_secret,
            label=clean_label,
            active=True,
            failure_count=0,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    else:
        row.actor_ref = actor_ref
        row.endpoint = endpoint.strip()
        row.p256dh = p256dh
        row.auth_secret = auth_secret
        row.label = clean_label
        row.active = True
        row.failure_count = 0
        row.last_error = None
        row.revoked_at = None
        row.revoked_reason = None
        row.updated_at = now
    session.flush()
    return row


def list_devices(session: Session, actor_ref: str) -> list[dict]:
    rows = session.scalars(
        select(AdminPushSubscription)
        .where(AdminPushSubscription.actor_ref == actor_ref)
        .order_by(AdminPushSubscription.created_at.desc())
    )
    return [_public_device(row) for row in rows]


def revoke_device(
    session: Session, actor_ref: str, device_id: UUID, *, reason: str
) -> AdminPushSubscription:
    row = session.get(AdminPushSubscription, device_id)
    if row is None or row.actor_ref != actor_ref:
        raise LookupError("aparelho não encontrado")
    _deactivate(row, reason)
    session.flush()
    return row


def enqueue_event_pushes(
    session: Session,
    settings: Settings,
    *,
    event_key: str,
    kind: str,
    order_id: UUID | None,
    date_request_id: UUID | None,
) -> int:
    if kind not in _KINDS or kind == "test" or not vapid_configured(settings):
        return 0
    title, template = _KINDS[kind]
    reference = _reference(session, order_id, date_request_id)
    body = template.format(ref=reference)[:180]
    path = _path(order_id, date_request_id)
    created = 0
    devices = session.scalars(
        select(AdminPushSubscription).where(AdminPushSubscription.active.is_(True))
    )
    for device in devices:
        if not actor_may_receive(settings, device.actor_ref):
            _deactivate(device, "papel administrativo removido")
            continue
        if _delivery_exists(session, event_key, device.id):
            continue
        session.add(
            _delivery(
                event_key=event_key,
                device=device,
                kind=kind,
                title=title,
                body=body,
                path=path,
            )
        )
        created += 1
    session.flush()
    return created


def enqueue_test_push(
    session: Session, settings: Settings, *, actor_ref: str, device_id: UUID
) -> OpsPushDelivery:
    if not vapid_configured(settings):
        raise ValueError("notificações indisponíveis neste servidor")
    device = session.get(AdminPushSubscription, device_id)
    if device is None or device.actor_ref != actor_ref or not device.active:
        raise LookupError("aparelho não encontrado")
    if not actor_may_receive(settings, actor_ref):
        raise ValueError("conta administrativa sem permissão para receber avisos")
    title, template = _KINDS["test"]
    row = _delivery(
        event_key=f"test:{device.id}:{uuid4()}",
        device=device,
        kind="test",
        title=title,
        body=template.format(ref="teste"),
        path="/admin/pedidos",
    )
    session.add(row)
    session.flush()
    return row


def process_due_pushes(session: Session, settings: Settings, *, sender=None) -> int:
    if not vapid_configured(settings):
        return 0
    send = sender or _network_sender
    rows = list(
        session.scalars(
            select(OpsPushDelivery)
            .where(OpsPushDelivery.status == "awaiting", OpsPushDelivery.attempts < _MAX_ATTEMPTS)
            .order_by(OpsPushDelivery.created_at)
        )
    )
    handled = 0
    for row in rows:
        device = session.get(AdminPushSubscription, row.subscription_id)
        if device is None or not device.active:
            _finish(row, "inactive", "inscrição inativa")
            handled += 1
            continue
        if not actor_may_receive(settings, device.actor_ref):
            _deactivate(device, "papel administrativo removido")
            _finish(row, "inactive", "papel administrativo removido")
            handled += 1
            continue
        outcome = _attempt(send, device, row, settings)
        _apply_outcome(device, row, outcome)
        handled += 1
    session.flush()
    return handled


def _attempt(send, device: AdminPushSubscription, row: OpsPushDelivery, settings: Settings) -> str:
    payload = json.dumps(
        {"title": row.title, "body": row.body, "path": row.path, "tag": row.event_key[:64]},
        ensure_ascii=False,
    )
    try:
        return send(device, payload, settings)
    except TimeoutError:
        return "ambiguous"
    except Exception:
        LOG.exception("falha ao enviar push %s", row.id)
        return "ambiguous"


def _apply_outcome(device: AdminPushSubscription, row: OpsPushDelivery, outcome: str) -> None:
    row.attempts += 1
    row.updated_at = datetime.now(UTC)
    if outcome == "accepted":
        row.status = "accepted"
        row.last_error = None
        device.failure_count = 0
        device.last_error = None
        return
    if outcome == "inactive":
        _deactivate(device, "inscrição expirada")
        _finish(row, "inactive", "inscrição expirada ou revogada")
        return
    if outcome == "ambiguous":
        _finish(row, "failed", "resposta ambígua; sem reenvio automático")
        device.failure_count += 1
        device.last_error = row.last_error
        return
    if outcome == "failed":
        _finish(row, "failed", "o serviço recusou o envio")
        device.failure_count += 1
        device.last_error = row.last_error
        return
    device.failure_count += 1
    if row.attempts >= _MAX_ATTEMPTS:
        _finish(row, "failed", "falha temporária esgotou as tentativas")
    else:
        row.status = "awaiting"
        row.last_error = "falha temporária; nova tentativa prevista"
    device.last_error = row.last_error


def _network_sender(device: AdminPushSubscription, payload: str, settings: Settings) -> str:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": device.endpoint,
                "keys": {"p256dh": device.p256dh, "auth": device.auth_secret},
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key.strip(),
            vapid_claims={
                "sub": settings.vapid_subject.strip() or "mailto:oscar@oscarsarquis.com.br"
            },
            ttl=60,
            timeout=8,
        )
    except WebPushException as exc:
        status = exc.status_code
        if status in {404, 410}:
            return "inactive"
        if status in {408, 429} or (status is not None and status >= 500):
            return "retry"
        if status is None:
            return "ambiguous"
        return "failed"
    except TimeoutError:
        return "ambiguous"
    return "accepted"


def _public_from_private(private: str) -> str | None:
    try:
        from cryptography.hazmat.primitives import serialization
        from py_vapid import Vapid
        from py_vapid.utils import b64urlencode
    except Exception:
        return None
    try:
        vapid = Vapid.from_string(private)
        raw = vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
    except Exception:
        return None
    return b64urlencode(raw)


def _reference(session: Session, order_id: UUID | None, date_request_id: UUID | None) -> str:
    if order_id is not None:
        order = session.get(Order, order_id)
        if order is not None and order.public_reference:
            return order.public_reference
    if date_request_id is not None:
        request = session.get(DateRequest, date_request_id)
        if request is not None:
            from app.domain.attendance import date_request_reference

            return date_request_reference(request.id)
    return "sem referência"


def _path(order_id: UUID | None, date_request_id: UUID | None) -> str:
    if order_id is not None:
        return f"/admin/pedidos/{order_id}"
    if date_request_id is not None:
        return f"/admin/pedidos/solicitacao/{date_request_id}"
    return "/admin/pedidos"


def _delivery_exists(session: Session, event_key: str, device_id: UUID) -> bool:
    found = session.scalar(
        select(OpsPushDelivery.id).where(
            OpsPushDelivery.event_key == event_key,
            OpsPushDelivery.subscription_id == device_id,
        )
    )
    return found is not None


def _delivery(
    *,
    event_key: str,
    device: AdminPushSubscription,
    kind: str,
    title: str,
    body: str,
    path: str,
) -> OpsPushDelivery:
    now = datetime.now(UTC)
    return OpsPushDelivery(
        event_key=event_key[:160],
        subscription_id=device.id,
        kind=kind[:40],
        status="awaiting",
        title=title[:120],
        body=body[:180],
        path=path[:200],
        attempts=0,
        created_at=now,
        updated_at=now,
    )


def _deactivate(row: AdminPushSubscription, reason: str) -> None:
    row.active = False
    row.revoked_at = datetime.now(UTC)
    row.revoked_reason = reason[:120]
    row.updated_at = row.revoked_at


def _finish(row: OpsPushDelivery, status: str, error: str) -> None:
    row.status = status
    row.last_error = error[:280]
    row.updated_at = datetime.now(UTC)


def _public_device(row: AdminPushSubscription) -> dict:
    return {
        "id": str(row.id),
        "label": row.label,
        "active": row.active,
        "created_at": row.created_at.isoformat(),
        "failure_count": row.failure_count,
    }


def _label(value: str) -> str:
    cleaned = "".join(ch for ch in (value or "").strip() if ch.isprintable())
    return (cleaned or "Este aparelho")[:40]
