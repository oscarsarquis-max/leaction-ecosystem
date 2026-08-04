"""Cliente S2S do Micro-CMS do Action Hub, com cache em memória.

Graceful degradation: timeout/erro no Hub → cache antigo ou {}.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

CACHE_TTL_SEC = int(os.environ.get("CMS_CACHE_TTL_SEC", "480"))
HUB_TIMEOUT_SEC = float(os.environ.get("CMS_HUB_TIMEOUT_SEC", "3.5"))

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _hub_base() -> str:
    return (
        os.environ.get("ACTION_HUB_API_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).strip().rstrip("/")


def fetch_site_cms(*, config_key: str = "inove4us-school") -> dict[str, Any]:
    """Micro-CMS do Hub (landing_page_data) por config_key."""
    key = f"site_cms:{config_key}"
    now = time.time()

    with _lock:
        entry = _cache.get(key)
        if entry and (now - float(entry["fetched_at"])) < CACHE_TTL_SEC:
            payload = entry.get("payload")
            return dict(payload) if isinstance(payload, dict) else {}

    url = f"{_hub_base()}/api/public/cms"
    params = {"config_key": config_key}

    try:
        res = requests.get(url, params=params, timeout=HUB_TIMEOUT_SEC)
        res.raise_for_status()
        data = res.json() if res.content else {}
        if not isinstance(data, dict):
            data = {}
        with _lock:
            _cache[key] = {"payload": data, "fetched_at": now}
        return dict(data)
    except Exception as exc:
        logger.warning("[cms] Micro-CMS Hub indisponível (%s): %s", url, exc)
        with _lock:
            stale = _cache.get(key)
            if stale and isinstance(stale.get("payload"), dict):
                return dict(stale["payload"])
        return {}
