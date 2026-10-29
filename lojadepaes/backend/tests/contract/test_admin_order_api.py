"""Rotas de /admin/orders. Sem sessão a API recusa."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.contract.support import send_confirmed, send_submitted

assert admin_client
pytestmark = pytest.mark.contract


def test_orders_require_a_session(admin_client: TestClient) -> None:
    denied = admin_client.get("/api/v1/admin/orders")
    assert denied.status_code == 401


def test_list_shape_and_commands(admin_client: TestClient, db: Session) -> None:
    # GET "", POST confirm, start-production, cancel, notes
    reviewed = send_submitted(db, "api-review")
    plain = send_confirmed(db, "api-plain")
    db.commit()
    csrf = login(admin_client)
    headers = {"X-CSRF-Token": csrf}
    listed = admin_client.get("/api/v1/admin/orders")
    assert listed.status_code == 200
    body = listed.json()
    assert {"items", "total", "page", "page_size"} <= set(body)
    sample = next(item for item in body["items"] if item["public_reference"] == plain.public_reference)
    assert "visible_stage" in sample
    assert "visible_label" in sample
    assert sample["visible_stage"] == "accepted"

    missing_csrf = admin_client.post(f"/api/v1/admin/orders/{reviewed.id}/confirm")
    assert missing_csrf.status_code == 403

    confirmed = admin_client.post(f"/api/v1/admin/orders/{reviewed.id}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["visible_stage"] == "accepted"

    blocked = admin_client.post(
        f"/api/v1/admin/orders/{plain.id}/start-production",
        headers=headers,
        json={"unpaid_exception": False},
    )
    assert blocked.status_code == 409
    assert blocked.json()["financial_bucket"]

    started = admin_client.post(
        f"/api/v1/admin/orders/{plain.id}/start-production",
        headers=headers,
        json={"unpaid_exception": True},
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_production"

    note = admin_client.post(
        f"/api/v1/admin/orders/{plain.id}/notes",
        headers=headers,
        json={"body": "conferir o forno"},
    )
    assert note.status_code == 200, note.text
    assert note.json()["body"] == "conferir o forno"

    no_reason = admin_client.post(
        f"/api/v1/admin/orders/{reviewed.id}/cancel",
        headers=headers,
        json={"reason": " "},
    )
    assert no_reason.status_code == 422
