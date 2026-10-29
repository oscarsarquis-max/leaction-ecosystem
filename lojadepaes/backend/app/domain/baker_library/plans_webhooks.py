"""Ingresso isolado de eventos de planos. Não toca pedidos, Pay nem fidelidade."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.baker_library.access import _remember, subject_hmac
from app.domain.baker_library.hub_plans import invoke as hub_plans_invoke
from app.domain.actionhub_client import HubUnavailableError
from app.domain.errors import AuthError, ConfirmationError
from app.domain.hub_jwt import HubJwtError, verify_hub_jwt
from app.models.baker_library import HubPlansEvent

logger = logging.getLogger("lojadepaes.biblioteca")

PLANS_EVENT_TYPES = {
    "CONTRACT_ACTIVATED",
    "CREDITS_GRANTED",
    "SUBSCRIPTION_STATUS",
}

BUSINESS_RANK = {
    "pending": 1,
    "authorized": 2,
    "paused": 2,
    "cancelled": 3,
    "canceled": 3,
    "expired": 4,
}


def _inner_payload(claims: dict) -> dict:
    payload = claims.get("payload")
    return payload if isinstance(payload, dict) else {}


def apply_plans_webhook(session: Session, settings: Settings, token: str) -> dict:
    if not settings.actionhub_app_secret.strip():
        raise ConfirmationError("ActionHub não configurado")
    try:
        claims = verify_hub_jwt(token, settings.actionhub_app_secret)
    except HubJwtError as exc:
        raise AuthError("notificação de planos recusada") from exc
    if str(claims.get("app_id") or "").lower() != settings.actionhub_app_id.lower():
        raise AuthError("notificação de outro aplicativo")
    event_type = str(claims.get("event_type") or "").strip().upper()
    if event_type.startswith("BIBLIOTECA_"):
        pass
    elif event_type not in PLANS_EVENT_TYPES:
        raise ConfirmationError("evento de planos não reconhecido")
    inner = _inner_payload(claims)
    event_id = str(claims.get("outbox_id") or claims.get("idempotency_key") or "").strip()
    if not event_id:
        raise ConfirmationError("evento de planos sem identificador estável")
    existing = session.scalar(select(HubPlansEvent).where(HubPlansEvent.event_id == event_id))
    if existing is not None:
        return {
            "duplicate": True,
            "process_status": existing.process_status,
            "domain": "plans",
        }

    subject = str(inner.get("subject_id") or "").strip()
    digest = subject_hmac(settings, subject) if subject else None
    issued_at = _issued_at(claims)
    row = HubPlansEvent(
        event_id=event_id[:120],
        event_type=event_type[:80],
        subject_hmac=digest,
        business_status=str(inner.get("status") or inner.get("commercial_status") or "")[:40] or None,
        issued_at=issued_at,
        received_at=datetime.now(UTC),
        process_status="received",
        payload_json=json.dumps(_sanitized(inner), ensure_ascii=False),
    )
    session.add(row)
    session.flush()

    if digest and _is_stale(session, row):
        row.process_status = "ignored_stale"
        session.flush()
        return {"duplicate": False, "process_status": row.process_status, "domain": "plans"}

    if digest and subject:
        try:
            remote = hub_plans_invoke(
                settings,
                "GET_HUB_ENTITLEMENTS",
                {"subject_id": subject},
                correlation_id=f"plans-wh-{event_id}"[:80],
                idempotency_key=f"plans-wh-ent:{event_id}"[:80],
            )
            if isinstance(remote, dict):
                _remember(session, settings, digest, remote, source="hub")
        except (HubUnavailableError, ConfirmationError, AuthError):
            logger.info("plans webhook persisted; hub reconcile deferred event=%s", event_id[:24])

    row.process_status = "applied"
    session.flush()
    return {"duplicate": False, "process_status": row.process_status, "domain": "plans"}


def _sanitized(inner: dict) -> dict:
    allowed = {
        "subject_id",
        "sku",
        "status",
        "commercial_status",
        "financial_status",
        "contract_id",
        "order_id",
        "credits",
        "credits_added",
        "creditos",
        "cycle_id",
    }
    return {key: inner.get(key) for key in allowed if inner.get(key) is not None}


def _issued_at(claims: dict) -> datetime | None:
    for key in ("iat", "nbf"):
        raw = claims.get(key)
        if raw is None:
            continue
        try:
            return datetime.fromtimestamp(float(raw), tz=UTC)
        except (TypeError, ValueError, OSError):
            continue
    return None


def _is_stale(session: Session, incoming: HubPlansEvent) -> bool:
    if incoming.subject_hmac is None or incoming.issued_at is None:
        return False
    newer = session.scalars(
        select(HubPlansEvent)
        .where(
            HubPlansEvent.subject_hmac == incoming.subject_hmac,
            HubPlansEvent.event_id != incoming.event_id,
            HubPlansEvent.process_status.in_(("applied", "received")),
        )
        .order_by(HubPlansEvent.received_at.desc())
    ).first()
    if newer is None:
        return False
    if newer.issued_at and incoming.issued_at < newer.issued_at:
        return True
    incoming_rank = BUSINESS_RANK.get(str(incoming.business_status or "").lower(), 0)
    newer_rank = BUSINESS_RANK.get(str(newer.business_status or "").lower(), 0)
    if incoming.issued_at == newer.issued_at and incoming_rank and newer_rank and incoming_rank < newer_rank:
        return True
    return False
