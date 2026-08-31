"""Cliente S2S do Micro-CMS do Action Hub (somente servidor)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def hub_base_url(configured: str = "") -> str:
    return (
        (configured or "").strip()
        or os.environ.get("ACTION_HUB_API_URL", "").strip()
        or os.environ.get("HUB_API_URL", "").strip()
        or "http://127.0.0.1:4001"
    ).rstrip("/")


def fetch_hub_cms(
    *,
    config_key: str,
    base_url: str,
    timeout_seconds: float,
    max_bytes: int,
) -> dict[str, Any] | None:
    """
    GET /api/public/cms?config_key=…
    Retorna dict do Hub ou None (caller usa cache/fallback).
    Não propaga exceção; não envia cookies/tokens de usuário.
    """
    url = f"{hub_base_url(base_url)}/api/public/cms"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            res = client.get(url, params={"config_key": config_key})
        if res.status_code != 200:
            logger.warning("[login-editorial] Hub status=%s key=%s", res.status_code, config_key)
            return None
        if len(res.content) > max_bytes:
            logger.warning("[login-editorial] Hub payload excessivo key=%s", config_key)
            return None
        data = res.json()
        if not isinstance(data, dict) or data.get("success") is False:
            return None
        landing = data.get("landing_page_data")
        if landing is not None and not isinstance(landing, dict):
            return None
        return data
    except Exception as exc:
        logger.warning("[login-editorial] Hub indisponível key=%s: %s", config_key, type(exc).__name__)
        return None
