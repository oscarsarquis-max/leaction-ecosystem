"""Cache em memória do conteúdo editorial (por config_key), com stale-on-error.

AVISO OPERACIONAL: cache é **por processo/task** (dict em memória + lock).
Não é compartilhado entre workers, reinícios ou réplicas. Sem Redis nesta passagem.
"""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_store: dict[str, dict[str, Any]] = {}


def cache_get(key: str, ttl_seconds: float) -> dict[str, Any] | None:
    """Retorna payload se ainda fresco (idade ≤ TTL)."""
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        age = now - float(entry["fetched_at"])
        if age > ttl_seconds:
            return None
        payload = entry.get("payload")
        return dict(payload) if isinstance(payload, dict) else None


def cache_get_stale(key: str, *, max_stale_seconds: float) -> dict[str, Any] | None:
    """
    Retorna payload stale se idade ≤ max_stale_seconds.
    Além desse limite → None (caller usa fallback estático).
    """
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        age = now - float(entry["fetched_at"])
        if age > max_stale_seconds:
            return None
        payload = entry.get("payload")
        return dict(payload) if isinstance(payload, dict) else None


def cache_set(key: str, payload: dict[str, Any], *, fetched_at: float | None = None) -> None:
    with _lock:
        _store[key] = {
            "payload": dict(payload),
            "fetched_at": float(fetched_at if fetched_at is not None else time.time()),
        }


def cache_age_seconds(key: str) -> float | None:
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        return time.time() - float(entry["fetched_at"])


def cache_clear() -> None:
    with _lock:
        _store.clear()
