from fastapi.testclient import TestClient


def test_health_does_not_need_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {"status": "ok", "service": "lojadepaes"}


def test_health_body_has_no_connection_details(client: TestClient) -> None:
    body = client.get("/api/v1/health").text.lower()
    assert "postgresql" not in body
    assert "password" not in body
    assert "lojadepaes_dev" not in body
