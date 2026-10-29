"""R026-012 — identidade demo em /health sem segredos."""

import os
from unittest.mock import patch

from app.health import DemoRuntimeInfo, _logical_database_name, build_health
from app.main import app
from fastapi.testclient import TestClient


def test_logical_database_name_strips_credentials() -> None:
    url = "postgresql+asyncpg://admin:s3cret@127.0.0.1:5433/panne_demo"
    assert _logical_database_name(url) == "panne_demo"
    assert "s3cret" not in (_logical_database_name(url) or "")


def test_health_omits_demo_block_outside_demo(monkeypatch) -> None:
    client = TestClient(app)
    with patch("app.health.get_settings") as settings:
        settings.return_value.env = "local"
        settings.return_value.versao = "0.1.0"
        settings.return_value.database_url = "postgresql+asyncpg://u:p@127.0.0.1:5433/panne"
        settings.return_value.demo_instance_id = "should-not-appear"
        settings.return_value.demo_started_at = "x"
        settings.return_value.demo_anchor_date = "2026-08-24"
        # rebuild via endpoint uses app's get_settings — patch build path
        body = build_health()
    assert body.ambiente == "local"
    assert body.demo is None


def test_health_demo_identity_no_secrets(monkeypatch) -> None:
    with patch("app.health.get_settings") as settings:
        settings.return_value.env = "demo"
        settings.return_value.versao = "0.1.0"
        settings.return_value.database_url = (
            "postgresql+asyncpg://admin:super-secret@127.0.0.1:5433/panne_demo"
        )
        settings.return_value.demo_instance_id = "abc123"
        settings.return_value.demo_started_at = "2026-08-27T18:00:00+00:00"
        settings.return_value.demo_anchor_date = "2026-08-24"
        body = build_health()
    assert body.ambiente == "demo"
    assert isinstance(body.demo, DemoRuntimeInfo)
    assert body.demo.instance_id == "abc123"
    assert body.demo.logical_database == "panne_demo"
    assert body.demo.demo_anchor_date == "2026-08-24"
    assert body.demo.process_id == os.getpid()
    dumped = body.model_dump()
    assert "super-secret" not in str(dumped).lower()
    assert "password" not in str(dumped).lower()
    assert "admin" not in str(dumped)


def test_health_endpoint_still_public() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "panne"
