"""
Cliente S2S do Headless CMS do Action Hub, com cache em memória.

Graceful degradation: timeout/erro no Hub → devolve cache antigo ou [].
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# 5–10 min (padrão 8 min)
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


def fetch_published_posts(
    *,
    sistema_destino: str = "inove4us",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Lista posts publicados do Hub; nunca propaga falha ao cliente."""
    key = f"{sistema_destino}:{limit}"
    now = time.time()

    with _lock:
        entry = _cache.get(key)
        if entry and (now - float(entry["fetched_at"])) < CACHE_TTL_SEC:
            return list(entry["posts"])

    url = f"{_hub_base()}/api/cms/posts"
    params = {"sistema_destino": sistema_destino, "limit": str(limit)}

    try:
        res = requests.get(url, params=params, timeout=HUB_TIMEOUT_SEC)
        res.raise_for_status()
        data = res.json() if res.content else {}
        posts = data.get("posts") if isinstance(data, dict) else None
        if not isinstance(posts, list):
            posts = []
        with _lock:
            _cache[key] = {"posts": posts, "fetched_at": now}
        return list(posts)
    except Exception as exc:
        logger.warning("[cms] Hub indisponível (%s): %s", url, exc)
        with _lock:
            stale = _cache.get(key)
            if stale and isinstance(stale.get("posts"), list):
                return list(stale["posts"])
        return []
