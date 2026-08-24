"""Idempotency keys that cannot be made to answer the wrong question.

A bare `Idempotency-Key` is not enough. Two failure modes matter:

**Cross-operation collisions.** A client that reuses `"run-1"` for both
"authorize an evidence for action A" and "record a measurement" must get two
independent results. The key is therefore always paired with an
`idempotency_scope` — a canonical operation name plus its target, chosen by the
**server** from the URL and never taken from the request body. A caller cannot
widen or narrow its own scope.

**Silent divergence.** A client that retries `"run-1"` with a *different*
payload is not retrying, it is issuing a new command with a stale key. Replaying
the first result would hand back an object that does not match what was asked
for. So every stored key carries a `request_fingerprint` over the meaningful
fields of the request; same fingerprint replays, different fingerprint is a
409 `idempotency_conflict`.

Both the key and the fingerprint are stored as SHA-256 digests. The raw key can
identify a client integration and is not business data, and the fingerprint
inputs may include sizes and identifiers we have no reason to keep in the clear.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.errors import AppError

# Bumping this invalidates every stored fingerprint, which is exactly what we
# want if the recipe ever changes: an old digest must never be compared against
# a new one and judged "different payload".
FINGERPRINT_VERSION = "isoi008-rev001"


def key_hash(raw_key: str) -> str:
    return "sha256:" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value") and not isinstance(value, (str, int, float, bool)):
        return str(value.value)
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def request_fingerprint(scope: str, parts: Mapping[str, Any]) -> str:
    """Stable digest over the fields that make two requests the same request."""
    payload = {
        "version": FINGERPRINT_VERSION,
        "scope": scope,
        "parts": _canonical(dict(parts)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assert_same_request(stored_fingerprint: str | None, fingerprint: str) -> None:
    """Refuse a key that is being reused for a different request."""
    if stored_fingerprint is not None and stored_fingerprint != fingerprint:
        raise AppError(
            "idempotency_conflict",
            "Esta Idempotency-Key já foi usada para outro pedido. "
            "Use uma chave nova para um pedido diferente.",
            status_code=409,
        )
