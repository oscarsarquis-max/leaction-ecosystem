from types import SimpleNamespace

import pytest
from app.api import deps
from app.core.config import Settings, get_settings
from app.db.session import reset_engine
from app.domain.admin_auth import local_passwordless_permitted
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_SESSION_SECRET


def _local_app(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    monkeypatch.setenv("LOJADEPAES_ENV", env.get("env", "local"))
    monkeypatch.setenv("LOJADEPAES_HTTP_HOST", env.get("http_host", "127.0.0.1"))
    monkeypatch.setenv("LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS", env.get("flag", "true"))
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", env.get("secret", TEST_SESSION_SECRET))
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", env.get("username", ""))
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", env.get("password_hash", ""))
    get_settings.cache_clear()
    reset_engine()
    app = create_app()
    client_host = env.get("client_host", "127.0.0.1")
    app.dependency_overrides[deps._client_host] = lambda: client_host
    return TestClient(app)


def test_passwordless_flag_defaults_off() -> None:
    assert Settings.model_fields["admin_local_passwordless"].default is False


def test_access_indicator_off_when_flag_disabled(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    del db
    app_client = _local_app(monkeypatch, flag="false")
    response = app_client.get("/api/v1/admin/access")
    assert response.status_code == 200
    assert response.json() == {"local_passwordless": False}
    get_settings.cache_clear()
    reset_engine()


def test_local_login_creates_session_and_opens_products(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    del db
    app_client = _local_app(monkeypatch)
    denied = app_client.get("/api/v1/admin/products")
    assert denied.status_code == 401
    access = app_client.get("/api/v1/admin/access")
    assert access.json() == {"local_passwordless": True}
    login = app_client.post("/api/v1/admin/local-login")
    assert login.status_code == 200
    assert login.json()["username"] == "desenvolvimento"
    assert login.json()["csrf_token"]
    products = app_client.get("/api/v1/admin/products")
    assert products.status_code == 200
    csrf = login.json()["csrf_token"]
    logout = app_client.post("/api/v1/admin/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert app_client.get("/api/v1/admin/products").status_code == 401
    assert app_client.post("/api/v1/admin/local-login").status_code == 200
    get_settings.cache_clear()
    reset_engine()


def test_local_login_refuses_production(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    del db
    app_client = _local_app(monkeypatch, env="production")
    assert app_client.get("/api/v1/admin/access").json()["local_passwordless"] is False
    assert app_client.post("/api/v1/admin/local-login").status_code == 403
    assert app_client.get("/api/v1/admin/products").status_code == 503
    get_settings.cache_clear()
    reset_engine()


def test_local_login_refuses_when_flag_off(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    del db
    app_client = _local_app(monkeypatch, flag="false")
    assert app_client.post("/api/v1/admin/local-login").status_code == 403
    get_settings.cache_clear()
    reset_engine()


def test_local_login_refuses_non_loopback_client(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    del db
    app_client = _local_app(monkeypatch, client_host="203.0.113.10")
    assert app_client.post("/api/v1/admin/local-login").status_code == 403
    get_settings.cache_clear()
    reset_engine()


def test_local_login_refuses_non_loopback_bind(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    del db
    app_client = _local_app(monkeypatch, http_host="0.0.0.0")
    assert app_client.get("/api/v1/admin/access").json()["local_passwordless"] is False
    assert app_client.post("/api/v1/admin/local-login").status_code == 403
    get_settings.cache_clear()
    reset_engine()


def test_password_login_still_disabled_without_credentials(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    del db
    app_client = _local_app(monkeypatch)
    response = app_client.post(
        "/api/v1/admin/login",
        json={"username": "qualquer", "password": "qualquer"},
    )
    assert response.status_code == 503
    get_settings.cache_clear()
    reset_engine()


def test_local_passwordless_predicate() -> None:
    fake = SimpleNamespace(admin_local_passwordless=True, env="local", http_host="127.0.0.1")
    assert local_passwordless_permitted(fake, "127.0.0.1") is True
    fake.env = "production"
    assert local_passwordless_permitted(fake, "127.0.0.1") is False
    fake.env = "local"
    fake.admin_local_passwordless = False
    assert local_passwordless_permitted(fake, "127.0.0.1") is False
    fake.admin_local_passwordless = True
    assert local_passwordless_permitted(fake, "203.0.113.9") is False
    fake.http_host = "0.0.0.0"
    assert local_passwordless_permitted(fake, "127.0.0.1") is False
    fake.http_host = "127.0.0.1"
    assert local_passwordless_permitted(fake, "127.0.0.1", "0.0.0.0") is False
    assert local_passwordless_permitted(fake, "127.0.0.1", "testserver") is True
