from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.marketplace_links import (
    keep_image_url,
    keep_official_outbound_url,
    sanitize_plain_text,
    vendor_from_source,
)
from app.domain.offer_contract import offer_fits_contract

logger = logging.getLogger("lojadepaes.marketplace")

_CACHE: dict[str, tuple[float, list["HubOffer"]]] = {}
_CACHE_TTL = 45.0
_PROFILE_COUNT: int | None = None
_ORIGIN_SHELVES = ("vinhos", "queijos", "frios", "azeites", "cervejas", "batatas")


@dataclass(frozen=True)
class HubOffer:
    id: str
    title: str
    description: str
    image_url: str | None
    price_amount: Decimal | None
    price_currency: str
    price_label: str | None
    link: str | None
    source: str
    category: str = ""
    availability_verified: bool = False
    availability_checked_at: str | None = None


def _headers(settings: Settings) -> dict[str, str]:
    app_id = (settings.actionhub_app_id or "").strip()
    headers = {"Accept": "application/json"}
    if app_id:
        headers["X-ActionHub-App-Id"] = app_id
    return headers


def fetch_hub_profile_catalog(settings: Settings, *, limit: int = 12, refresh: bool = False) -> dict[str, Any]:
    """Catálogo do perfil mapeado pelo app id. Sem app id o Hub devolve o legado — não chamamos."""
    base = (settings.actionhub_marketplace_url or "").strip().rstrip("/")
    if not base:
        return {"ok": False, "offers": [], "error": "marketplace_url_unset", "origin": None}
    if not (settings.actionhub_app_id or "").strip():
        return {"ok": False, "offers": [], "error": "app_id_unset", "origin": None}
    cache_key = f"profile|{base}|{settings.actionhub_app_id}|{limit}"
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if not refresh and cached and now - cached[0] < _CACHE_TTL:
        return {"ok": True, "offers": cached[1], "error": None, "cached": True, "origin": "lojadepaes"}
    timeout = max(0.4, min(float(settings.actionhub_marketplace_timeout_seconds), 4.0))
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{base}/vitrine",
                params={"limit": max(1, min(limit, 8)), "origin": "lojadepaes"},
                headers=_headers(settings),
            )
        if response.status_code != 200:
            logger.info("marketplace.vitrine status=%s", response.status_code)
            return {"ok": False, "offers": [], "error": f"http_{response.status_code}", "origin": None}
        payload = response.json()
    except Exception as exc:
        logger.info("marketplace.vitrine fail err=%s", type(exc).__name__)
        return {"ok": False, "offers": [], "error": type(exc).__name__, "origin": None}
    offers: list[HubOffer] = []
    hub_shelves_with_offers: set[str] = set()
    for shelf in payload.get("shelves") or []:
        if not isinstance(shelf, dict):
            continue
        category = sanitize_plain_text(shelf.get("category") or shelf.get("category_label"), limit=80)
        shelf_key = category.casefold()
        if shelf_key in _ORIGIN_SHELVES and shelf.get("offers"):
            hub_shelves_with_offers.add(shelf_key)
        for raw in shelf.get("offers") or []:
            parsed = _parse_offer(raw, category=category)
            if parsed and offer_fits_contract(
                title=parsed.title,
                category=parsed.category or category,
                domain=str(raw.get("provider_domain") or raw.get("domain_id") or ""),
            ):
                offers.append(parsed)
    if not offers:
        for raw in payload.get("offers") or []:
            parsed = _parse_offer(raw)
            if parsed and offer_fits_contract(
                title=parsed.title,
                category=parsed.category,
                domain=str(raw.get("provider_domain") or raw.get("domain_id") or ""),
            ):
                offers.append(parsed)
    parsed_shelves = {sanitize_plain_text(item.category, limit=80).casefold() for item in offers}
    dropped = sorted(hub_shelves_with_offers - parsed_shelves)
    logger.info(
        "marketplace.vitrine ok=%s shelves=%s dropped=%s",
        len(offers),
        ",".join(sorted(hub_shelves_with_offers)) or "-",
        ",".join(dropped) or "-",
    )
    if not dropped:
        _CACHE[cache_key] = (now, offers)
    elif cache_key in _CACHE:
        del _CACHE[cache_key]
    global _PROFILE_COUNT
    _PROFILE_COUNT = len(offers)
    return {
        "ok": True,
        "offers": offers,
        "error": None,
        "cached": False,
        "origin": payload.get("origin"),
        "dropped_shelves": dropped,
    }


def fetch_hub_offers(settings: Settings, query: str, *, limit: int = 8) -> dict[str, Any]:
    """Busca no perfil do consumidor (app id). Não usa o legado de TI."""
    base = (settings.actionhub_marketplace_url or "").strip().rstrip("/")
    if not base:
        return {"ok": False, "offers": [], "error": "marketplace_url_unset"}
    term = sanitize_plain_text(query, limit=80)
    cache_key = f"{base}|{settings.actionhub_app_id}|{term.casefold()}|{limit}"
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return {"ok": True, "offers": cached[1], "error": None, "cached": True}
    timeout = max(0.4, min(float(settings.actionhub_marketplace_timeout_seconds), 4.0))
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{base}/offers",
                params={"q": term or None, "limit": max(1, min(limit, 12)), "origin": "lojadepaes"},
                headers=_headers(settings),
            )
        if response.status_code != 200:
            logger.info("marketplace.offers status=%s", response.status_code)
            return {"ok": False, "offers": [], "error": f"http_{response.status_code}"}
        payload = response.json()
    except Exception as exc:
        logger.info("marketplace.offers fail err=%s", type(exc).__name__)
        return {"ok": False, "offers": [], "error": type(exc).__name__}
    parsed_offers: list[HubOffer] = []
    for item in payload.get("offers") or []:
        parsed = _parse_offer(item)
        if parsed and offer_fits_contract(
            title=parsed.title,
            category=parsed.category,
            domain=str(item.get("provider_domain") or item.get("domain_id") or "") if isinstance(item, dict) else "",
        ):
            parsed_offers.append(parsed)
    offers = parsed_offers
    _CACHE[cache_key] = (now, offers)
    return {"ok": True, "offers": offers, "error": None, "cached": False}


def fetch_hub_offer_by_id(settings: Settings, offer_id: str) -> HubOffer | None:
    wanted = sanitize_plain_text(offer_id, limit=80)
    if not wanted:
        return None
    profile = fetch_hub_profile_catalog(settings)
    for offer in profile.get("offers") or []:
        if offer.id == wanted:
            return offer
    result = fetch_hub_offers(settings, wanted, limit=8)
    for offer in result.get("offers") or []:
        if offer.id == wanted:
            return offer
    return None


def cached_profile_count() -> int | None:
    return _PROFILE_COUNT


def remember_profile_count(count: int) -> None:
    global _PROFILE_COUNT
    _PROFILE_COUNT = max(0, int(count))


def clear_marketplace_cache() -> None:
    _CACHE.clear()
    global _PROFILE_COUNT
    _PROFILE_COUNT = None


def _parse_offer(raw: object, *, category: str = "") -> HubOffer | None:
    if not isinstance(raw, dict):
        return None
    offer_id = sanitize_plain_text(raw.get("id"), limit=80)
    title = sanitize_plain_text(raw.get("title") or raw.get("name"), limit=240)
    if not offer_id or not title:
        return None
    if offer_id.startswith("fallback-") or raw.get("fallback") is True:
        return None
    link = keep_official_outbound_url(raw.get("link"))
    source = vendor_from_source(raw.get("vendor") or raw.get("source"), link)
    amount = _decimal(raw.get("price"))
    currency = sanitize_plain_text(raw.get("currency") or "BRL", limit=8) or "BRL"
    label = sanitize_plain_text(raw.get("price_label"), limit=40) or None
    return HubOffer(
        id=offer_id,
        title=title,
        description=sanitize_plain_text(raw.get("description") or raw.get("summary"), limit=600),
        image_url=keep_image_url(raw.get("image") or raw.get("image_url")),
        price_amount=amount,
        price_currency=currency,
        price_label=label,
        link=link,
        source=source,
        category=sanitize_plain_text(raw.get("category") or category, limit=80),
        availability_verified=bool(raw.get("availability_verified")),
        availability_checked_at=sanitize_plain_text(raw.get("availability_checked_at"), limit=40) or None,
    )


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if amount < 0:
        return None
    return amount.quantize(Decimal("0.01"))
