from uuid import uuid4

from app.domain.orders import confirm_order, transition_order
from app.models.enums import FinancialStatus, OrderStatus, PaymentProvider
from app.models.orders import OrderInternalNote, OrderStatusHistory
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_USER, admin_client, login
from tests.db_fixtures import draft_order, priced_catalog

assert admin_client


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def test_list_empty_and_filters(admin_client: TestClient, db: Session) -> None:
    csrf = login(admin_client)
    del csrf
    empty = admin_client.get("/api/v1/admin/orders")
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}

    catalog = priced_catalog(db)
    first = draft_order(db, catalog)
    second = draft_order(db, catalog)
    confirm_order(db, first.id)
    db.commit()

    listed = admin_client.get("/api/v1/admin/orders")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 2
    confirmed = admin_client.get("/api/v1/admin/orders", params={"status": "confirmed"})
    assert confirmed.json()["total"] == 1
    assert confirmed.json()["items"][0]["public_reference"] == first.public_reference
    by_ref = admin_client.get(
        "/api/v1/admin/orders", params={"reference": first.public_reference}
    )
    assert by_ref.json()["total"] == 1
    page = admin_client.get("/api/v1/admin/orders", params={"page": 1, "page_size": 1})
    assert len(page.json()["items"]) == 1
    assert page.json()["total"] == 2
    missing = admin_client.get(f"/api/v1/admin/orders/{uuid4()}")
    assert missing.status_code == 404
    del second


def test_transitions_notes_and_history(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)

    confirm = admin_client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "confirmed"
    assert confirm.json()["snapshots_locked"] is True
    assert confirm.json()["items"][0]["unit_price"]["cents"] == 1400
    assert confirm.json()["financial_kind"] == "none"

    again = admin_client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers=headers)
    assert again.status_code == 200
    db.expire_all()
    history = db.query(OrderStatusHistory).filter_by(order_id=order.id).all()
    assert len(history) == 1
    assert history[0].actor_ref == f"admin:{TEST_ADMIN_USER}"

    start = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/start-production", headers=headers
    )
    assert start.json()["status"] == "in_production"
    ready = admin_client.post(f"/api/v1/admin/orders/{order.id}/mark-ready", headers=headers)
    assert ready.json()["status"] == "ready"
    done = admin_client.post(f"/api/v1/admin/orders/{order.id}/complete", headers=headers)
    assert done.json()["status"] == "completed"
    assert done.json()["holds_capacity"] is True

    invalid = admin_client.post(f"/api/v1/admin/orders/{order.id}/cancel", headers=headers, json={"reason": "tarde"})
    assert invalid.status_code == 409

    note = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/notes",
        headers=headers,
        json={"body": "separar para retirada no balcão"},
    )
    assert note.status_code == 200
    assert note.json()["author_ref"] == f"admin:{TEST_ADMIN_USER}"
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert detail.json()["notes"][0]["body"].startswith("separar")
    assert "internal" not in admin_client.get("/api/v1/health").text


def test_cancel_requires_reason_and_keeps_finance(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=1400,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
        )
    )
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    missing = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel", headers=headers, json={"reason": ""}
    )
    assert missing.status_code == 422
    cancelled = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel",
        headers=headers,
        json={"reason": "cliente avisou atraso"},
    )
    assert cancelled.status_code == 200
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["cancellation_reason"] == "cliente avisou atraso"
    assert len(body["payment_records"]) == 1
    assert body["payment_records"][0]["financial_status"] == "pending"
    assert body["financial_kind"] == "unknown" or body["financial_kind"] == "open"


def test_confirm_without_price(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    catalog["dough"].base_price_cents = None
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    response = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm", headers=_headers(csrf)
    )
    assert response.status_code == 422
    assert "preço" in response.json()["detail"]


def test_complete_does_not_free_capacity_via_api(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 1
    catalog["slot"].capacity_units = 1
    first = draft_order(db, catalog)
    confirm_order(db, first.id)
    transition_order(db, first.id, OrderStatus.IN_PRODUCTION.value)
    transition_order(db, first.id, OrderStatus.READY.value)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    done = admin_client.post(f"/api/v1/admin/orders/{first.id}/complete", headers=headers)
    assert done.status_code == 200
    second = draft_order(db, catalog)
    db.commit()
    blocked = admin_client.post(f"/api/v1/admin/orders/{second.id}/confirm", headers=headers)
    assert blocked.status_code == 409
    assert "capacidade" in blocked.json()["detail"]


def test_financial_kind_not_paid_from_one_record(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=1400,
            currency="BRL",
            financial_status=FinancialStatus.PAID.value,
            amount_paid_cents=100,
        )
    )
    db.commit()
    login(admin_client)
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert detail.json()["financially_settled"] is False
    assert detail.json()["financial_kind"] == "open"
    listed = admin_client.get("/api/v1/admin/orders")
    assert listed.json()["items"][0]["financial_kind"] != "settled"


def test_notes_stay_in_admin(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.add(OrderInternalNote(order_id=order.id, body="telefone conferido", author_ref="admin:padaria"))
    db.commit()
    login(admin_client)
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert detail.json()["notes"][0]["body"] == "telefone conferido"
    health = admin_client.get("/api/v1/health").text
    assert "telefone conferido" not in health
    assert admin_client.get("/api/v1/orders").status_code == 404
