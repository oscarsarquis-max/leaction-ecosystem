from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from fastapi.testclient import TestClient
from tests.admin_client import TEST_ADMIN_PASSWORD, TEST_ADMIN_USER, admin_client, login

assert admin_client


def test_admin_disabled_without_secrets(client: TestClient) -> None:
    response = client.get("/api/v1/admin/orders")
    assert response.status_code == 503
    assert "desabilitada" in response.json()["detail"]


def test_unauthenticated_orders(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/orders")
    assert response.status_code == 401


def test_login_invalid_and_valid(admin_client: TestClient) -> None:
    bad = admin_client.post(
        "/api/v1/admin/login",
        json={"username": TEST_ADMIN_USER, "password": "wrong-password"},
    )
    assert bad.status_code == 401
    login(admin_client)
    session = admin_client.get("/api/v1/admin/session")
    assert session.status_code == 200
    assert session.json()["username"] == TEST_ADMIN_USER
    assert session.json()["csrf_token"]


def test_logout_requires_csrf_and_revokes(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    denied = admin_client.post("/api/v1/admin/logout")
    assert denied.status_code == 403
    ok = admin_client.post("/api/v1/admin/logout", headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 200
    assert admin_client.get("/api/v1/admin/orders").status_code == 401


def test_login_rate_limit(admin_client: TestClient, monkeypatch) -> None:
    del admin_client
    monkeypatch.setenv("LOJADEPAES_LOGIN_MAX_FAILURES", "3")
    get_settings.cache_clear()
    reset_engine()
    limited_app = TestClient(create_app())
    for _ in range(3):
        response = limited_app.post(
            "/api/v1/admin/login",
            json={"username": TEST_ADMIN_USER, "password": "nope"},
        )
        assert response.status_code == 401
    blocked = limited_app.post(
        "/api/v1/admin/login",
        json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD},
    )
    assert blocked.status_code == 429
    get_settings.cache_clear()
    reset_engine()


def test_notes_not_on_public_routes(admin_client: TestClient) -> None:
    login(admin_client)
    public = admin_client.get("/api/v1/health")
    assert public.status_code == 200
    assert "notes" not in public.text
    assert admin_client.get("/api/v1/orders").status_code == 404
