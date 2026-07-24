"""
Exemplo Flask (PanelDX) — espelho do consumidor inove4us.

Copie para LeAction_SysF e registre:

    from cms_noticias_routes import cms_noticias_bp  # ou cole a rota abaixo
    app.register_blueprint(cms_noticias_bp)

Env:
  ACTION_HUB_API_URL=http://127.0.0.1:4001
  CMS_CACHE_TTL_SEC=480
"""

from __future__ import annotations

import logging
import os
import threading
import time

import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

CACHE_TTL_SEC = int(os.environ.get("CMS_CACHE_TTL_SEC", "480"))
HUB_TIMEOUT_SEC = float(os.environ.get("CMS_HUB_TIMEOUT_SEC", "3.5"))

_lock = threading.Lock()
_cache: dict = {}

cms_noticias_bp = Blueprint("cms_noticias", __name__)


def _hub_base() -> str:
    return (
        os.environ.get("ACTION_HUB_API_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).strip().rstrip("/")


def fetch_posts(sistema: str = "paneldx", limit: int = 5) -> list:
    key = f"{sistema}:{limit}"
    now = time.time()
    with _lock:
        entry = _cache.get(key)
        if entry and (now - entry["fetched_at"]) < CACHE_TTL_SEC:
            return list(entry["posts"])

    url = f"{_hub_base()}/api/cms/posts"
    try:
        res = requests.get(
            url,
            params={"sistema_destino": sistema, "limit": str(limit)},
            timeout=HUB_TIMEOUT_SEC,
        )
        res.raise_for_status()
        data = res.json() if res.content else {}
        posts = data.get("posts") if isinstance(data, dict) else None
        if not isinstance(posts, list):
            posts = []
        with _lock:
            _cache[key] = {"posts": posts, "fetched_at": now}
        return list(posts)
    except Exception as exc:
        logger.warning("[cms] Hub indisponível: %s", exc)
        with _lock:
            stale = _cache.get(key)
            if stale:
                return list(stale["posts"])
        return []


@cms_noticias_bp.get("/api/noticias")
def list_noticias():
    sistema = (request.args.get("sistema_destino") or "paneldx").strip() or "paneldx"
    try:
        limit = int(request.args.get("limit") or "5")
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 50))
    return jsonify(fetch_posts(sistema, limit)), 200
