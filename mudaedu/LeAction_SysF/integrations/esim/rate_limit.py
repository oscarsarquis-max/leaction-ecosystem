"""Rate limit simples para o webhook eSIM (in-memory, por IP)."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

_LOCK = Lock()
_JANELAS: dict[str, deque[float]] = defaultdict(deque)

DEFAULT_LIMIT = int(os.environ.get("ESIM_RATE_LIMIT_PER_MINUTE", os.environ.get("BASEMOBILE_RATE_LIMIT_PER_MINUTE", "60")))
DEFAULT_WINDOW_S = int(os.environ.get("ESIM_RATE_LIMIT_WINDOW_S", os.environ.get("BASEMOBILE_RATE_LIMIT_WINDOW_S", "60")))


def esim_verificar_rate_limit_webhook(
    client_key: str,
    *,
    limite: int | None = None,
    janela_s: int | None = None,
) -> tuple[bool, int]:
    """Retorna (permitido, retry_after_seconds)."""
    limite = limite if limite is not None else DEFAULT_LIMIT
    janela_s = janela_s if janela_s is not None else DEFAULT_WINDOW_S
    chave = (client_key or "unknown").strip() or "unknown"
    agora = time.time()

    with _LOCK:
        fila = _JANELAS[chave]
        while fila and fila[0] <= agora - janela_s:
            fila.popleft()

        if len(fila) >= limite:
            retry_after = max(1, int(janela_s - (agora - fila[0]))) if fila else janela_s
            return False, retry_after

        fila.append(agora)
        return True, 0


def esim_reset_rate_limit_state() -> None:
    with _LOCK:
        _JANELAS.clear()


verificar_rate_limit_webhook = esim_verificar_rate_limit_webhook
reset_rate_limit_state = esim_reset_rate_limit_state
