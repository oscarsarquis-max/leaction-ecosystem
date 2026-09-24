from collections.abc import Iterator
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.bakery_time import bakery_today
from app.main import create_app
from app.models.email_outbox import EmailOutbox
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.test_admin_products import _auth
from tests.test_schedule import _next_iso


@pytest.fixture
def product_client(db: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_date_request_persists_and_rejects_past(product_client: TestClient) -> None:
    future = (_next_iso(3) + timedelta(days=14)).isoformat()
    past = (bakery_today(get_settings()) - timedelta(days=1)).isoformat()
    payload = {
        "desired_date": future,
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "intended_quantity": 2,
        "message": "Aniversário da família",
        "idempotency_key": "req-date-1",
    }
    first = product_client.post("/api/v1/schedule/date-requests", json=payload)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["status"] == "pending"
    assert "ainda não confirma" in body["message"]
    second = product_client.post("/api/v1/schedule/date-requests", json=payload)
    assert second.status_code == 200
    assert second.json()["id"] == body["id"]
    denied = product_client.post(
        "/api/v1/schedule/date-requests",
        json={**payload, "desired_date": past, "idempotency_key": "req-date-past"},
    )
    assert denied.status_code == 422

    headers = _auth(product_client)
    listed = product_client.get("/api/v1/admin/date-requests", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items[0]["customer_email"] == "ana@example.com"
    assert items[0]["desired_date"] == future
    public = product_client.get("/api/v1/schedule/date-requests")
    assert public.status_code == 405


def test_closed_or_full_date_can_be_requested(product_client: TestClient, db: Session) -> None:
    closed = _next_iso(1).isoformat()
    payload = {
        "desired_date": closed,
        "customer_name": "Bia",
        "customer_email": "bia@example.com",
        "intended_quantity": 4,
        "idempotency_key": "req-monday-closed",
    }
    response = product_client.post("/api/v1/schedule/date-requests", json=payload)
    assert response.status_code == 200, response.text
    row = db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "date_request_received"))
    assert row is not None
    assert row.status == "skipped"
    assert "Solicitação de data" in row.subject


def test_admin_propose_does_not_occupy_capacity(product_client: TestClient) -> None:
    future = (_next_iso(6) + timedelta(days=7)).isoformat()
    created = product_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": future,
            "customer_name": "Caio",
            "customer_email": "caio@example.com",
            "intended_quantity": 3,
            "idempotency_key": "req-propose-1",
        },
    )
    assert created.status_code == 200, created.text
    request_id = created.json()["id"]
    headers = _auth(product_client)
    proposed = product_client.post(
        f"/api/v1/admin/date-requests/{request_id}",
        headers=headers,
        json={"action": "propose", "proposed_date": future, "note": "podemos olhar esse sábado"},
    )
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["status"] == "alternative_proposed"
    assert proposed.json()["proposed_date"] == future
    closed = product_client.post(
        f"/api/v1/admin/date-requests/{request_id}",
        headers=headers,
        json={"action": "close", "note": "encerrado após conversa"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_date_request_requires_admin_to_list(product_client: TestClient) -> None:
    assert product_client.get("/api/v1/admin/date-requests").status_code == 401
