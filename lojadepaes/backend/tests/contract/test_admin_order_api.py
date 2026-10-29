"""Rotas de /admin/orders. Cada rota: sessão e CSRF, sem sessão, e sem CSRF nas que gravam."""

from datetime import timedelta

import pytest
from app.domain.orders import start_production, transition_order
from app.models.enums import OrderStatus
from app.models.orders import OrderItem
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


def _prepare(db: Session, case: str) -> tuple[str, str, dict | None, dict]:
    """Devolve método, caminho, corpo e o recorte que a tela lê."""
    if case == "GET /admin/orders":
        send_confirmed(db, "route-list")
        return "GET", "/api/v1/admin/orders", None, {"items": list, "total": int, "page": int, "page_size": int}
    if case == "GET /admin/orders/{id}":
        order = send_confirmed(db, "route-detail")
        return (
            "GET",
            f"/api/v1/admin/orders/{order.id}",
            None,
            {"status": str, "visible_stage": str, "items": list, "notes": list, "allowed_actions": list},
        )
    if case == "POST /admin/orders/{id}/confirm":
        order = send_submitted(db, "route-confirm")
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/confirm",
            None,
            {"status": "confirmed", "visible_stage": "accepted", "public_reference": str},
        )
    if case == "POST /admin/orders/{id}/propose-date":
        order = send_submitted(db, "route-propose")
        other = (order.production_local_date + timedelta(days=7)).isoformat()
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/propose-date",
            {"date": other},
            {"status": "submitted", "proposed_production_date": other},
        )
    if case == "POST /admin/orders/{id}/start-production":
        order = send_confirmed(db, "route-start")
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/start-production",
            {"unpaid_exception": True},
            {"status": "in_production", "visible_stage": "in_production"},
        )
    if case == "POST /admin/orders/{id}/confirm-delivery":
        order = send_confirmed(db, "route-delivery")
        start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/confirm-delivery",
            None,
            {"status": "completed", "visible_stage": "delivered"},
        )
    if case == "POST /admin/orders/{id}/mark-ready":
        order = send_confirmed(db, "route-ready")
        start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/mark-ready",
            None,
            {"status": "ready", "visible_stage": "ready_legacy"},
        )
    if case == "POST /admin/orders/{id}/complete":
        order = send_confirmed(db, "route-complete")
        start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
        transition_order(
            db, order.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato"
        )
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/complete",
            None,
            {"status": "completed", "visible_stage": "finalized"},
        )
    if case == "POST /admin/orders/{id}/cancel":
        order = send_confirmed(db, "route-cancel")
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/cancel",
            {"reason": "cliente desistiu"},
            {"status": "cancelled", "visible_stage": "cancelled"},
        )
    if case == "POST /admin/orders/{id}/items/{item_id}/adaptation":
        order = send_submitted(db, "route-adapt")
        item = db.query(OrderItem).filter_by(order_id=order.id).one()
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/items/{item.id}/adaptation",
            {"decision": "accept", "response": "segue sem sementes"},
            {"status": "submitted", "items": list},
        )
    if case == "POST /admin/orders/{id}/notes":
        order = send_confirmed(db, "route-note")
        return (
            "POST",
            f"/api/v1/admin/orders/{order.id}/notes",
            {"body": "nota da rota"},
            {"body": "nota da rota"},
        )
    raise AssertionError(case)


READS = [
    "GET /admin/orders",
    "GET /admin/orders/{id}",
]
WRITES = [
    "POST /admin/orders/{id}/confirm",
    "POST /admin/orders/{id}/propose-date",
    "POST /admin/orders/{id}/start-production",
    "POST /admin/orders/{id}/confirm-delivery",
    "POST /admin/orders/{id}/mark-ready",
    "POST /admin/orders/{id}/complete",
    "POST /admin/orders/{id}/cancel",
    "POST /admin/orders/{id}/items/{item_id}/adaptation",
    "POST /admin/orders/{id}/notes",
]
ROUTES = READS + WRITES


def _assert_shape(body: dict, expect: dict) -> None:
    for key, expected in expect.items():
        assert key in body
        if isinstance(expected, type):
            assert isinstance(body[key], expected)
        else:
            assert body[key] == expected


@pytest.mark.parametrize("case", ROUTES)
def test_admin_route_without_session(admin_client: TestClient, db: Session, case: str) -> None:
    _method, path, payload, _expect = _prepare(db, case)
    db.commit()
    response = admin_client.request(_method, path, json=payload)
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("case", WRITES)
def test_admin_route_without_csrf(admin_client: TestClient, db: Session, case: str) -> None:
    method, path, payload, _expect = _prepare(db, case)
    db.commit()
    login(admin_client)
    response = admin_client.request(method, path, json=payload)
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("case", ROUTES)
def test_admin_route_with_session_and_csrf(admin_client: TestClient, db: Session, case: str) -> None:
    method, path, payload, expect = _prepare(db, case)
    db.commit()
    headers = {"X-CSRF-Token": login(admin_client)}
    response = admin_client.request(method, path, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    _assert_shape(body, expect)
    if case == "GET /admin/orders":
        sample = body["items"][0]
        assert "visible_stage" in sample
        assert "visible_label" in sample
