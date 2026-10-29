"""Medição de consumo do Gigio. Sem texto integral, fórmulas pessoais ou dados de pedido."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.baker_library import GigioUsageEvent
from app.models.customers import CustomerAccount

_recent: dict[str, datetime] = {}


def subject_hmac(settings: Settings, email: str | None) -> str | None:
    if not email:
        return None
    secret = (settings.customer_identity_secret or settings.admin_session_secret or "biblioteca").encode()
    return hmac.new(secret, f"uso:{email.strip().lower()}".encode(), hashlib.sha256).hexdigest()


def accidental_repeat(key: str, *, window_seconds: float = 2.0) -> bool:
    now = datetime.now(UTC)
    previous = _recent.get(key)
    _recent[key] = now
    if previous is None:
        return False
    return (now - previous) <= timedelta(seconds=window_seconds)


def record_usage(
    session: Session,
    settings: Settings,
    *,
    origin: str,
    function: str,
    ok: bool,
    duration_ms: int,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    fail_kind: str | None = None,
    account: CustomerAccount | None = None,
    article_id: str | None = None,
    provider: str | None = None,
) -> None:
    session.add(
        GigioUsageEvent(
            origin=origin if origin in {"biblioteca", "atendimento", "fazedor"} else "atendimento",
            function=function[:32],
            ok=ok,
            duration_ms=max(0, int(duration_ms)),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            fail_kind=(fail_kind or "")[:40] or None,
            subject_hmac=subject_hmac(settings, account.email if account else None),
            article_id=(article_id or "")[:80] or None,
            provider=(provider or "")[:20] or None,
        )
    )
    session.flush()


def usage_snapshot(session: Session, *, limit: int = 50) -> dict[str, Any]:
    rows = list(
        session.scalars(select(GigioUsageEvent).order_by(GigioUsageEvent.created_at.desc()).limit(limit))
    )
    by_origin: dict[str, int] = {}
    for row in rows:
        by_origin[row.origin] = by_origin.get(row.origin, 0) + 1
    return {
        "events": len(rows),
        "by_origin": by_origin,
        "note": "Franquia comercial e excedente ainda não foram definidos. Isto é medição técnica, não pacote vendido.",
    }
