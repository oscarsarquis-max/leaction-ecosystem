"""Orquestra Hub → mapper → cache → fallback estático para /entrar."""

from __future__ import annotations

from app.config import get_settings
from app.modules.login_editorial.cache import cache_get, cache_get_stale, cache_set
from app.modules.login_editorial.config_key import resolve_login_editorial_config_key
from app.modules.login_editorial.content import (
    SCHEMA_VERSION,
    hosts_from_settings,
    sanitize_column,
    static_payload,
    unavailable_fallback,
)
from app.modules.login_editorial.hub_client import fetch_hub_cms
from app.modules.login_editorial.mapper import map_hub_landing_to_panne

__all__ = [
    "SCHEMA_VERSION",
    "sanitize_column",
    "static_payload",
    "unavailable_fallback",
    "resolve_editorial_payload",
]


def resolve_editorial_payload(*, force_mode: str | None = None) -> dict:
    """
    force_mode é **somente** para injeção em testes unitários do service.
    A rota HTTP pública não aceita nem encaminha mode.
    """
    if force_mode == "unavailable":
        return unavailable_fallback()
    if force_mode == "invalid":
        return {"schema_version": 99, "columns": [{"title": ""}]}

    settings = get_settings()
    media_hosts, cta_hosts = hosts_from_settings(settings)
    config_key = resolve_login_editorial_config_key(
        env=settings.env,
        override=settings.login_editorial_config_key,
        allow_demo_override_in_prod=bool(settings.login_editorial_allow_demo_key_in_prod),
    )
    cache_key = f"login-editorial:{config_key}"
    ttl = float(settings.login_editorial_cache_ttl_seconds)
    max_stale = float(settings.login_editorial_cache_max_stale_seconds)

    cached = cache_get(cache_key, ttl)
    if cached:
        out = dict(cached)
        out["source"] = "cache" if out.get("source") == "hub" else out.get("source", "cache")
        out["config_key"] = config_key
        return out

    hub = fetch_hub_cms(
        config_key=config_key,
        base_url=settings.action_hub_api_url,
        timeout_seconds=float(settings.login_editorial_timeout_seconds),
        max_bytes=int(settings.login_editorial_max_bytes),
    )
    static = static_payload(media_hosts=media_hosts, cta_hosts=cta_hosts)
    if hub:
        mapped = map_hub_landing_to_panne(
            hub.get("landing_page_data") if isinstance(hub.get("landing_page_data"), dict) else None,
            static_columns=list(static.get("columns") or []),
            media_hosts=media_hosts,
            cta_hosts=cta_hosts,
        )
        if mapped and mapped.get("columns"):
            mapped["config_key"] = config_key
            cache_set(cache_key, mapped)
            return mapped

    stale = cache_get_stale(cache_key, max_stale_seconds=max_stale)
    if stale and stale.get("columns"):
        out = dict(stale)
        out["source"] = "cache"
        out["config_key"] = config_key
        out["note"] = "Último conteúdo válido em cache (Hub indisponível; dentro da idade máxima stale)."
        return out

    fallback = static_payload(media_hosts=media_hosts, cta_hosts=cta_hosts)
    fallback["config_key"] = config_key
    fallback["note"] = "Fallback estático — Hub indisponível, incompatível ou stale expirado."
    return fallback
