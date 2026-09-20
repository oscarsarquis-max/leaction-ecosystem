from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from fastapi.testclient import TestClient


def test_ready_unavailable_returns_503_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv(
        "LOJADEPAES_DATABASE_URL",
        "postgresql+psycopg://probe_user:super-secret-pass@127.0.0.1:1/lojadepaes",
    )
    monkeypatch.setenv("LOJADEPAES_DB_CONNECT_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ready")
    reset_engine()
    get_settings.cache_clear()

    assert response.status_code == 503
    body = response.text
    assert "super-secret-pass" not in body
    assert "probe_user" not in body
    assert "postgresql" not in body.lower()
    payload = response.json()
    detail = payload.get("detail", payload)
    assert detail["status"] == "unavailable"
    assert detail["service"] == "lojadepaes"
