"""Pool institucional + idempotência CREDITS_GRANTED (prompt 98). Sem I/O de produção."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_ia_credits import (  # noqa: E402
    CREDITO_IA_INSTITUTIONAL_POOL,
    ORIGEM_LICENSE_POOL,
)
from webhook_routes import resolve_hub_idempotency_key  # noqa: E402


def test_pool_default_50():
    assert CREDITO_IA_INSTITUTIONAL_POOL == 50
    assert ORIGEM_LICENSE_POOL == "institutional_license_pool"


def test_idempotency_key_header():
    key = resolve_hub_idempotency_key(
        decoded={},
        body={},
        payload={"order_id": "should-not-win"},
        headers={"X-Hub-Idempotency-Key": "order_abc_activation"},
    )
    assert key == "order_abc_activation"


def test_idempotency_key_order_fallback():
    key = resolve_hub_idempotency_key(
        decoded={},
        body={},
        payload={"order_id": "11111111-2222-3333-4444-555555555555"},
        headers={},
    )
    assert key == "order_11111111-2222-3333-4444-555555555555_activation"


def test_idempotency_key_body_wins_over_payload_order():
    key = resolve_hub_idempotency_key(
        decoded={},
        body={"idempotency_key": "bounty_xyz"},
        payload={"order_id": "ignored"},
        headers={},
    )
    assert key == "bounty_xyz"


def test_bind_calls_grant(monkeypatch=None):
    """Smoke estrutural: bind importa o grant (não executa DB)."""
    import inspect
    from services import school_academic_mirror as mirror

    src = inspect.getsource(mirror.bind_professor_to_institution)
    assert "grant_institutional_ia_pool" in src
    src2 = inspect.getsource(mirror.materialize_allocation)
    assert "grant_institutional_ia_pool" in src2


if __name__ == "__main__":
    test_pool_default_50()
    test_idempotency_key_header()
    test_idempotency_key_order_fallback()
    test_idempotency_key_body_wins_over_payload_order()
    test_bind_calls_grant()
    print("ok")
