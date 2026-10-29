"""Solicitação de data: estados e avisos, sem reservar na proposta."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from app.models.email_outbox import EmailOutbox
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET, login
from tests.test_schedule import _next_iso

pytestmark = pytest.mark.contract


@pytest.fixture
def client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as http:
        yield http
    get_settings.cache_clear()
    reset_engine()


def _request(client: TestClient, key: str) -> dict:
    future = (_next_iso(3) + timedelta(days=14)).isoformat()
    response = client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": future,
            "customer_name": "Ana Contrato",
            "customer_email": "ana-contrato@example.com",
            "intended_quantity": 2,
            "message": "Kit ainda não; só a data.",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_is_pending_and_idempotent(client: TestClient, db: Session) -> None:
    # create_date_request
    body = _request(client, "dr-create")
    assert body["status"] == "pending"
    again = _request(client, "dr-create")
    assert again["id"] == body["id"]
    assert db.query(EmailOutbox).filter_by(kind="date_request_received").count() == 1
    assert db.query(EmailOutbox).filter_by(kind="date_request_received_admin").count() == 1


def test_propose_does_not_reserve_and_close_requires_justification(client: TestClient, db: Session) -> None:
    # apply_date_request_action propose e close
    body = _request(client, "dr-propose")
    headers = {"X-CSRF-Token": login(client)}
    proposed = (_next_iso(6) + timedelta(days=14)).isoformat()
    response = client.post(
        f"/api/v1/admin/date-requests/{body['id']}",
        headers=headers,
        json={"action": "propose", "proposed_date": proposed, "note": "outra quarta"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "alternative_proposed"
    assert db.query(EmailOutbox).filter_by(kind="date_request_proposed").count() == 1
    assert db.query(EmailOutbox).filter_by(kind="date_request_available").count() == 0
    denied = client.post(
        f"/api/v1/admin/date-requests/{body['id']}",
        headers=headers,
        json={"action": "close", "note": ""},
    )
    assert denied.status_code == 422
    closed = client.post(
        f"/api/v1/admin/date-requests/{body['id']}",
        headers=headers,
        json={"action": "close", "note": "não conseguimos nesta data"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert db.query(EmailOutbox).filter_by(kind="date_request_declined").count() == 1


def test_request_completion_sends_the_complete_notice(client: TestClient, db: Session) -> None:
    # request_date_request_completion
    body = _request(client, "dr-complete")
    headers = {"X-CSRF-Token": login(client)}
    response = client.post(
        f"/api/v1/admin/date-requests/{body['id']}",
        headers=headers,
        json={"action": "request_completion", "note": "faltam o endereço e os pães"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "awaiting_details"
    assert db.query(EmailOutbox).filter_by(kind="date_request_complete").count() == 1
