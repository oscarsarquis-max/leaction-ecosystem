from unittest.mock import patch

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_ok_without_database() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "panne"
    assert "versao" in body
    assert "ambiente" in body
    assert "host" not in body
    assert "password" not in str(body).lower()


def test_ready_ok_when_postgres_answers() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "service": "panne"}
    assert "host" not in body


def test_ready_unavailable_does_not_leak_details() -> None:
    with patch(
        "app.main.assert_database_ready", side_effect=RuntimeError("segredo")
    ):
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "indisponivel"}
    assert "segredo" not in response.text
