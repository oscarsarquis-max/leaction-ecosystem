"""Integração LePain ↔ fidelidade da casa (BLOG-025).

Rotas de serviço: lookup por telefone (sem PII) e carimbo idempotente.
Logs nunca incluem o telefone.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import bakery_now
from app.domain.duplicates import normalize_phone
from app.domain.errors import ConfirmationError, NotFoundError
from app.domain.house_fidelity import (
    campaign_is_publicly_active,
    current_campaign,
    cycle_of,
    real_balance,
    vitrine_products,
)
from app.domain.house_fidelity_ledger import sync_credits_for_cycle
from app.models.house_fidelity import HouseFidelityEnrollment, HouseFidelityEvent
from app.models.orders import Order

logger = logging.getLogger("integracoes.lepain")

_RATE_LOCK = Lock()
_RATE_HITS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT = 60  # req / janela
_RATE_WINDOW_S = 60.0


def assert_rate_limit(client_host: str) -> None:
    now = time.monotonic()
    key = (client_host or "unknown")[:80]
    with _RATE_LOCK:
        bucket = _RATE_HITS[key]
        while bucket and now - bucket[0] > _RATE_WINDOW_S:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            logger.warning("integracoes rate_limit host=%s hits=%s", key, len(bucket))
            raise ConfirmationError("muitas tentativas; aguarde um minuto")
        bucket.append(now)


def _digits_phone(raw: str | None) -> str:
    phone = normalize_phone(raw)
    if len(phone) < 10:
        raise ConfirmationError("telefone inválido")
    return phone


def _orders_for_phone(session: Session, phone: str) -> list[Order]:
    # Match pelos últimos 11/10 dígitos no customer_phone (sem logar o valor).
    rows = list(
        session.scalars(
            select(Order)
            .where(Order.customer_phone.is_not(None))
            .order_by(Order.created_at.desc())
            .limit(400)
        )
    )
    matched = []
    for order in rows:
        if normalize_phone(order.customer_phone) == phone:
            matched.append(order)
    return matched


def resolve_account_id(session: Session, phone: str) -> UUID | None:
    for order in _orders_for_phone(session, phone):
        if order.fidelity_account_id is not None:
            return order.fidelity_account_id
    return None


def cliente_status(session: Session, settings: Settings, telefone: str) -> dict:
    phone = _digits_phone(telefone)
    account_id = resolve_account_id(session, phone)
    if account_id is None:
        logger.info("integracoes cliente_lookup hit=false")
        return {"cliente": False, "pontos": 0, "total": 0}

    campaign = current_campaign(session)
    enrolled = False
    if campaign is not None:
        enrolled = (
            session.scalar(
                select(HouseFidelityEnrollment.id).where(
                    HouseFidelityEnrollment.account_id == account_id,
                    HouseFidelityEnrollment.campaign_id == campaign.id,
                )
            )
            is not None
        )
    if not enrolled or campaign is None or not campaign_is_publicly_active(settings, campaign):
        logger.info("integracoes cliente_lookup hit=true enrolled=false")
        return {"cliente": True, "pontos": 0, "total": 0}

    balance = real_balance(session, settings, account_id, campaign)
    pontos = int(balance.get("valid_orders") or 0)
    total = int(balance.get("credits") or 0)
    logger.info("integracoes cliente_lookup hit=true enrolled=true")
    return {"cliente": True, "pontos": pontos, "total": total}


def credit_stamp(
    session: Session,
    settings: Settings,
    *,
    telefone: str,
    referencia: str,
) -> dict:
    phone = _digits_phone(telefone)
    ref = str(referencia or "").strip()
    if not ref or len(ref) > 80:
        raise ConfirmationError("referencia inválida")
    if not ref.startswith("lepain-"):
        raise ConfirmationError("referencia deve começar com lepain-")

    existing = session.scalar(
        select(HouseFidelityEvent).where(HouseFidelityEvent.actor_ref == ref)
    )
    account_id = resolve_account_id(session, phone)
    if account_id is None:
        raise NotFoundError("cliente não encontrado")

    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        raise ConfirmationError("a fidelidade da casa ainda não está em vigor")

    enrolled = session.scalar(
        select(HouseFidelityEnrollment.id).where(
            HouseFidelityEnrollment.account_id == account_id,
            HouseFidelityEnrollment.campaign_id == campaign.id,
        )
    )
    if enrolled is None:
        raise ConfirmationError("cliente sem participação na fidelidade")

    if existing is not None:
        balance = real_balance(session, settings, account_id, campaign)
        logger.info("integracoes credito idempotente ref_ok=true")
        return {
            "creditado": False,
            "pontos": int(balance.get("valid_orders") or 0),
            "total": int(balance.get("credits") or 0),
        }

    now = bakery_now(settings)
    year, month = cycle_of(settings, now)
    event = HouseFidelityEvent(
        campaign_id=campaign.id,
        account_id=account_id,
        order_id=None,
        kind="qualify",
        status="applied",
        cycle_year=year,
        cycle_month=month,
        eligible_at=now,
        reason="carimbo LePain (receita publicada)",
        actor_ref=ref,
    )
    session.add(event)
    session.flush()

    events = list(
        session.scalars(
            select(HouseFidelityEvent)
            .where(
                HouseFidelityEvent.campaign_id == campaign.id,
                HouseFidelityEvent.account_id == account_id,
                HouseFidelityEvent.kind == "qualify",
                HouseFidelityEvent.status == "applied",
                HouseFidelityEvent.cycle_year == year,
                HouseFidelityEvent.cycle_month == month,
            )
            .order_by(HouseFidelityEvent.eligible_at, HouseFidelityEvent.created_at)
        )
    )
    sync_credits_for_cycle(session, campaign.id, account_id, year, month, events)
    session.flush()

    balance = real_balance(session, settings, account_id, campaign)
    logger.info("integracoes credito aplicado")
    return {
        "creditado": True,
        "pontos": int(balance.get("valid_orders") or 0),
        "total": int(balance.get("credits") or 0),
    }


def list_vitrine(session: Session, *, base_url: str = "https://lojadepaes.com.br") -> list[dict]:
    base = base_url.rstrip("/")
    items = []
    for product in vitrine_products(session):
        slug = str(getattr(product, "slug", "") or "").strip()
        name = str(getattr(product, "name", "") or "").strip()
        if not slug or not name:
            continue
        items.append(
            {
                "id": str(product.id),
                "nome": name,
                "url": f"{base}/paes/{slug}",
            }
        )
    return items
