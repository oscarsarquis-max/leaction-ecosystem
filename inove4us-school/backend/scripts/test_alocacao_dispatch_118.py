"""Prompt 118 — retry TEACHER_ALLOCATED e flush pendente."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from secretaria_routes import _dispatch_alocacao_b2c  # noqa: E402


def test_dispatch_retry_depois_falha():
    payload = {"alocacao_id": "11111111-1111-1111-1111-111111111111"}
    calls = {"n": 0}

    def fake(p):
        calls["n"] += 1
        if calls["n"] < 2:
            return {"ok": False, "error": "timeout"}
        return {"ok": True, "status_code": 200}

    with patch(
        "b2c_integration_service.dispatch_teacher_allocated",
        side_effect=fake,
    ), patch("secretaria_routes._mark_alocacao_notificado") as marked:
        out = _dispatch_alocacao_b2c(payload, attempts=3, sleep_s=0)
    assert out.get("ok") is True
    assert out.get("attempts") == 2
    assert calls["n"] == 2
    marked.assert_called_once_with(payload["alocacao_id"])


def test_dispatch_esgota_retries_nao_marca():
    payload = {"alocacao_id": "22222222-2222-2222-2222-222222222222"}
    with patch(
        "b2c_integration_service.dispatch_teacher_allocated",
        return_value={"ok": False, "error": "down"},
    ), patch("secretaria_routes._mark_alocacao_notificado") as marked:
        out = _dispatch_alocacao_b2c(payload, attempts=3, sleep_s=0)
    assert out.get("ok") is False
    assert out.get("attempts") == 3
    marked.assert_not_called()


if __name__ == "__main__":
    test_dispatch_retry_depois_falha()
    test_dispatch_esgota_retries_nao_marca()
    print("ok 118 dispatch retry")
