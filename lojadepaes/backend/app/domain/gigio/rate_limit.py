from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.domain.errors import RateLimitError

_WINDOW = 60.0
_MAX_PER_HOST = 20
_MAX_IN_FLIGHT = 4
_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
_in_flight = 0


def acquire(host: str) -> None:
    global _in_flight
    now = time.monotonic()
    key = (host or "unknown")[:80]
    with _lock:
        bucket = _hits[key]
        while bucket and now - bucket[0] > _WINDOW:
            bucket.popleft()
        if len(bucket) >= _MAX_PER_HOST:
            raise RateLimitError("muitas conversas neste momento; aguarde um pouco")
        if _in_flight >= _MAX_IN_FLIGHT:
            raise RateLimitError("o Gigio está ocupado; tente de novo em instantes")
        bucket.append(now)
        _in_flight += 1


def release() -> None:
    global _in_flight
    with _lock:
        _in_flight = max(0, _in_flight - 1)
