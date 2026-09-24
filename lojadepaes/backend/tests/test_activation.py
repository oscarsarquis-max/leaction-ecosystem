from collections.abc import Iterator
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.activation import consume_activation, hash_activation_token, issue_activation
from app.domain.capacity import utc_now
from app.domain.errors import AuthError
from app.domain.ses_mailer import MailSendResult
from app.main import create_app
from app.models.admin import AdminActivationToken
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import TEST_SESSION_SECRET

ADMIN_USER = "admin@lojadepaes.com.br"


@pytest.fixture
def activation_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", "")
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", "https://lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_ACTIVATION_RECIPIENT", "oscar@oscarsarquis.com.br")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "false")
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_ACTIVATION_TTL_MINUTES", "1440")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def _issue(db: Session, monkeypatch: pytest.MonkeyPatch, *, force: bool = False):
    captured: dict[str, str] = {}

    def fake_send(settings, *, to_address: str, subject: str, body: str) -> MailSendResult:
        del settings, subject
        captured["to"] = to_address
        captured["body"] = body
        return MailSendResult(True, "test-message-id", None)

    monkeypatch.setattr("app.domain.activation.send_outbox_email", fake_send)
    result = issue_activation(db, get_settings(), force=force, send=True)
    db.commit()
    return result, captured


def test_issue_and_consume_activation(activation_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    first, captured = _issue(db, monkeypatch)
    assert first["status"] == "sent"
    assert captured["to"] == "oscar@oscarsarquis.com.br"
    assert "admin@lojadepaes.com.br" in captured["body"]
    assert "24 horas" in captured["body"]
    assert "horário de Brasília" in captured["body"]
    assert first["expires_at_sp"] in captured["body"]
    assert "30 minutos" not in captured["body"]
    token = captured["body"].split("/ativar/")[1].split()[0]
    peek = activation_client.get(f"/api/v1/admin/activate/{token}")
    assert peek.status_code == 200
    assert peek.json()["username"] == ADMIN_USER
    still = db.scalar(select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(token)))
    assert still is not None and still.consumed_at is None
    mismatch = activation_client.post(
        "/api/v1/admin/activate",
        json={"token": token, "password": "senha-valida-1", "confirm": "outra"},
    )
    assert mismatch.status_code == 422
    assert still.consumed_at is None
    ok = activation_client.post(
        "/api/v1/admin/activate",
        json={"token": token, "password": "senha-valida-1", "confirm": "senha-valida-1"},
    )
    assert ok.status_code == 200
    reused = activation_client.post(
        "/api/v1/admin/activate",
        json={"token": token, "password": "senha-valida-2", "confirm": "senha-valida-2"},
    )
    assert reused.status_code == 401
    login = activation_client.post(
        "/api/v1/admin/login",
        json={"username": ADMIN_USER, "password": "senha-valida-1"},
    )
    assert login.status_code == 200
    catalog = activation_client.get("/api/v1/catalog/showcase")
    assert catalog.status_code == 200
    second, _ = _issue(db, monkeypatch)
    assert second["status"] == "already_activated"


def test_expired_and_reissue(activation_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    del activation_client
    first, captured = _issue(db, monkeypatch)
    assert first["status"] == "sent"
    token = captured["body"].split("/ativar/")[1].split()[0]
    row = db.scalar(select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(token)))
    assert row is not None
    row.expires_at = utc_now() - timedelta(minutes=1)
    db.commit()
    with pytest.raises(AuthError):
        consume_activation(
            db,
            get_settings(),
            raw_token=token,
            password="senha-valida-1",
            confirm="senha-valida-1",
        )
    db.rollback()
    again, captured2 = _issue(db, monkeypatch, force=True)
    assert again["status"] == "sent"
    new_token = captured2["body"].split("/ativar/")[1].split()[0]
    assert new_token != token
    old = db.scalar(select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(token)))
    assert old is not None and old.invalidated_at is not None


def test_ttl_is_twenty_four_hours(activation_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    del activation_client
    before = utc_now()
    result, captured = _issue(db, monkeypatch)
    assert result["status"] == "sent"
    token = captured["body"].split("/ativar/")[1].split()[0]
    row = db.scalar(select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(token)))
    assert row is not None
    delta = row.expires_at - before
    assert timedelta(hours=23, minutes=50) <= delta <= timedelta(hours=24, minutes=10)
    assert "Expira em" in captured["body"]
    assert result["expires_at_sp"] in captured["body"]
    duplicate, _ = _issue(db, monkeypatch)
    assert duplicate["status"] == "already_sent"


def test_force_invalidates_previous_unexpired_link(
    activation_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, captured = _issue(db, monkeypatch)
    assert first["status"] == "sent"
    old_token = captured["body"].split("/ativar/")[1].split()[0]
    peek = activation_client.get(f"/api/v1/admin/activate/{old_token}")
    assert peek.status_code == 200
    again, captured2 = _issue(db, monkeypatch, force=True)
    assert again["status"] == "sent"
    new_token = captured2["body"].split("/ativar/")[1].split()[0]
    assert new_token != old_token
    replaced = activation_client.get(f"/api/v1/admin/activate/{old_token}")
    assert replaced.status_code == 401
    still = db.scalar(
        select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(old_token))
    )
    assert still is not None and still.consumed_at is None and still.invalidated_at is not None
    ready = activation_client.get(f"/api/v1/admin/activate/{new_token}")
    assert ready.status_code == 200
    leftover = db.scalar(
        select(AdminActivationToken).where(AdminActivationToken.token_hash == hash_activation_token(new_token))
    )
    assert leftover is not None and leftover.consumed_at is None


def test_preview_and_commerce_gates(activation_client: TestClient) -> None:
    ops = activation_client.get("/api/v1/operations")
    assert ops.status_code == 200
    body = ops.json()
    assert body["preview_protection"] is True
    assert body["orders_enabled"] is False
    assert body["payments_enabled"] is False
    assert activation_client.get("/api/v1/catalog/showcase").status_code == 401
    denied = activation_client.post("/api/v1/storefront/orders", json={})
    assert denied.status_code in {401, 422}
    local = activation_client.post("/api/v1/admin/local-login")
    assert local.status_code == 403
    webhook = activation_client.post(
        "/api/v1/webhooks/actionhub", json={"token": "x" * 24}
    )
    assert webhook.status_code in {401, 422}
