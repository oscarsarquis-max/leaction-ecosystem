from app.main import app
from app.modules.login_editorial.service import sanitize_column, static_payload
from fastapi.testclient import TestClient


def test_public_editorial_is_sanitized_and_does_not_need_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/public/login-editorial")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert body["source"] == "static"
    assert {row["placement"] for row in body["columns"]} == {"left", "right"}
    assert "actionhub" not in response.text.lower()


def test_invalid_and_unavailable_editorial() -> None:
    client = TestClient(app)
    unavailable = client.get("/api/v1/public/login-editorial", params={"mode": "unavailable"})
    assert unavailable.status_code == 200
    assert unavailable.json()["source"] == "fallback"
    assert unavailable.json()["columns"] == []
    invalid = client.get("/api/v1/public/login-editorial", params={"mode": "invalid"})
    assert invalid.json()["schema_version"] == 99


def test_sanitize_rejects_dangerous_media() -> None:
    assert sanitize_column({"placement": "left", "title": ""}) is None
    cleaned = sanitize_column(
        {
            "placement": "left",
            "title": "<script>x</script>Oficina",
            "image": {"url": "javascript:alert(1)", "alt": "x"},
        }
    )
    assert cleaned is not None
    assert "<" not in cleaned["title"]
    assert cleaned["image"]["url"] == ""
    assert static_payload()["columns"]
