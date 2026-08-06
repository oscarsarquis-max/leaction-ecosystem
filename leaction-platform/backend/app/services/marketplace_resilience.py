"""Resiliência do Marketplace — cache SWR, circuit breaker e orçamento de tempo.

Objetivo: /offers e /vitrine nunca dependerem do pior caso da API ML (N+1 + 12s).
- Cache fresco (TTL) → resposta imediata
- Cache stale → responde já e revalida em background
- Circuito aberto → só cache/fallback (protege rate-limit e latência)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Fresco: serve sem revalidar. Stale: serve + refresh async. Depois: miss duro.
CACHE_TTL_S = float(os.getenv("MARKETPLACE_CACHE_TTL_S", "300"))
CACHE_STALE_S = float(os.getenv("MARKETPLACE_CACHE_STALE_S", "1800"))
CIRCUIT_FAIL_THRESHOLD = int(os.getenv("MARKETPLACE_CIRCUIT_FAILS", "3"))
CIRCUIT_OPEN_S = float(os.getenv("MARKETPLACE_CIRCUIT_OPEN_S", "60"))
# Vitrine monta 3 prateleiras em paralelo (~5s cada). Budget 4s forçava fallback sem imagens ML.
LIVE_BUDGET_S = float(os.getenv("MARKETPLACE_LIVE_BUDGET_S", "18"))

_refresh_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mkt-swr")


@dataclass
class _CacheEntry:
    payload: Any
    fresh_until: float
    stale_until: float
    meta: dict[str, Any] = field(default_factory=dict)


class MarketplaceCircuitBreaker:
    """Abre após N falhas consecutivas; fecha no sucesso ou após cooldown."""

    def __init__(
        self,
        *,
        fail_threshold: int = CIRCUIT_FAIL_THRESHOLD,
        open_seconds: float = CIRCUIT_OPEN_S,
    ) -> None:
        self.fail_threshold = max(1, fail_threshold)
        self.open_seconds = max(5.0, open_seconds)
        self._failures = 0
        self._open_until = 0.0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if time.monotonic() < self._open_until:
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._open_until = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.fail_threshold:
                self._open_until = time.monotonic() + self.open_seconds
                logger.warning(
                    "Marketplace circuit OPEN por %.0fs após %s falhas",
                    self.open_seconds,
                    self._failures,
                )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_for = max(0.0, self._open_until - time.monotonic())
            return {
                "open": open_for > 0,
                "open_remaining_s": round(open_for, 1),
                "failures": self._failures,
            }


class MarketplaceResponseCache:
    """Cache em memória process-local com stale-while-revalidate."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._inflight: set[str] = set()

    def get(self, key: str) -> tuple[Any | None, str]:
        """Retorna (payload|None, state) onde state ∈ fresh|stale|miss."""
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None, "miss"
            if now <= entry.fresh_until:
                return entry.payload, "fresh"
            if now <= entry.stale_until:
                return entry.payload, "stale"
            return None, "miss"

    def set(
        self,
        key: str,
        payload: Any,
        *,
        ttl_s: float = CACHE_TTL_S,
        stale_s: float = CACHE_STALE_S,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = time.monotonic()
        with self._lock:
            self._store[key] = _CacheEntry(
                payload=payload,
                fresh_until=now + max(1.0, ttl_s),
                stale_until=now + max(ttl_s, stale_s),
                meta=dict(meta or {}),
            )

    def schedule_refresh(
        self,
        key: str,
        producer: Callable[[], Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_failure: Callable[[BaseException], None] | None = None,
    ) -> None:
        with self._lock:
            if key in self._inflight:
                return
            self._inflight.add(key)

        def _run() -> None:
            try:
                payload = producer()
                self.set(key, payload)
                if on_success:
                    on_success(payload)
            except Exception as exc:
                logger.warning("SWR refresh falhou key=%s: %s", key, exc)
                if on_failure:
                    on_failure(exc)
            finally:
                with self._lock:
                    self._inflight.discard(key)

        _refresh_pool.submit(_run)


# Singletons do processo marketplace
ml_circuit = MarketplaceCircuitBreaker()
offers_cache = MarketplaceResponseCache()
vitrine_cache = MarketplaceResponseCache()


def annotate_cache_meta(
    payload: dict[str, Any],
    *,
    cache_state: str,
    circuit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Copia o payload e anexa metadados de resiliência (não quebra clientes)."""
    out = dict(payload)
    reliability = {
        "cache": cache_state,
        "circuit": circuit or ml_circuit.snapshot(),
    }
    out["reliability"] = reliability
    if cache_state == "stale":
        # Mantém offers, mas sinaliza que live pode estar defasado
        notice = out.get("notice")
        stale_note = "Resposta em cache (revalidação em andamento)."
        out["notice"] = f"{notice} {stale_note}".strip() if notice else stale_note
        if "live" in out and cache_state == "stale":
            # Não minta que é live fresco
            out["served_from_cache"] = True
    elif cache_state == "fresh":
        out["served_from_cache"] = True
    return out


def run_with_live_budget(
    producer: Callable[[], T],
    *,
    budget_s: float = LIVE_BUDGET_S,
) -> T:
    """Executa producer com teto de tempo; estoura TimeoutError se passar do budget."""
    deadline = time.monotonic() + max(0.5, budget_s)
    box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _run() -> None:
        try:
            box["value"] = producer()
        except BaseException as exc:  # noqa: BLE001 — propaga via box
            error_box["exc"] = exc

    thread = threading.Thread(target=_run, name="mkt-live-budget", daemon=True)
    thread.start()
    remaining = max(0.05, deadline - time.monotonic())
    thread.join(timeout=remaining)
    if thread.is_alive():
        raise TimeoutError(f"live budget esgotado após {budget_s:.1f}s")
    if "exc" in error_box:
        raise error_box["exc"]
    return box["value"]
