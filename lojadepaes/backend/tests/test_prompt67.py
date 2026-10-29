from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.attendance import OPS_SUMMARY_DEDUPE, date_request_reference
from app.domain.bakery_time import bakery_today
from app.domain.email_outbox import process_due_outbox
from app.domain.recipe_bases import create_recipe_base
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus
from app.models.orders import Order
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS

assert admin_client


def _future(days: int = 10) -> str:
    return (bakery_today(get_settings()) + timedelta(days=days)).isoformat()


def _wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta or 7)
    return day.isoformat()


def _product(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 67")
    product = Product(
        name="Pão 67",
        slug=f"pao-67-{uuid4().hex[:8]}",
        short_description="teste",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=2490,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _create_date(
    client: TestClient,
    key: str,
    days: int = 10,
    name: str = "Bia 67",
    *,
    desired_date: str | None = None,
    lines: list | None = None,
) -> dict:
    payload = {
        "desired_date": desired_date or _future(days),
        "customer_name": name,
        "customer_email": f"{key}@example.test",
        "intended_quantity": 1,
        "message": "quero essa data",
        "idempotency_key": key,
    }
    if lines:
        payload["lines"] = lines
    response = client.post("/api/v1/schedule/date-requests", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_mixed_queue_detail_and_honest_replies(admin_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    headers = {"X-CSRF-Token": csrf}
    order = admin_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Ana 67",
            "customer_email": "ana-67@example.test",
            **NEW_ORDER_ADDRESS,
            "idempotency_key": "p67-order-1",
        },
    )
    assert order.status_code == 200, order.text
    created = _create_date(admin_client, "p67-date-1")
    aged = DateRequest(
        desired_date=bakery_today(get_settings()) - timedelta(days=1),
        customer_name="Clara 67",
        customer_email="clara-67@example.test",
        intended_quantity=2,
        status="pending",
        idempotency_key="p67-aged",
        client_host="test",
        created_at=datetime.now(UTC) - timedelta(hours=30),
    )
    db.add(aged)
    db.commit()

    listed = admin_client.get("/api/v1/admin/orders")
    assert listed.status_code == 200
    body = listed.json()
    assert body["orders_error"] is None
    assert body["date_requests_error"] is None
    keys = {item["row_key"] for item in body["items"]}
    refs = {item["public_reference"] for item in body["items"]}
    assert order.json()["public_reference"] in refs
    assert f"date_request:{created['id']}" in keys
    assert f"date_request:{aged.id}" in keys
    date_row = next(item for item in body["items"] if item["id"] == created["id"])
    assert date_row["source"] == "date_request"
    assert date_row["public_reference"] == date_request_reference(created["id"])
    assert date_row["financial_kind"] == "none"
    assert date_row["total"]["cents"] is None
    assert date_row["pending_hours"] is not None
    aged_row = next(item for item in body["items"] if item["id"] == str(aged.id))
    assert aged_row["pending_hours"] >= 24
    assert aged_row["overdue"] is True

    by_ref = admin_client.get(
        "/api/v1/admin/orders", params={"reference": date_row["public_reference"]}
    )
    assert any(item["id"] == created["id"] for item in by_ref.json()["items"])

    page = admin_client.get("/api/v1/admin/orders", params={"page": 1, "page_size": 1})
    assert page.json()["total"] >= 3
    assert len(page.json()["items"]) == 1

    closed_only = admin_client.get("/api/v1/admin/orders", params={"status": "date_closed"})
    assert all(item["source"] == "date_request" for item in closed_only.json()["items"])

    detail = admin_client.get(f"/api/v1/admin/date-requests/{created['id']}")
    assert detail.status_code == 200
    assert "formaliza o pedido" in (detail.json()["reply_preview"] or "")
    assert "accept" in detail.json()["allowed_actions"]
    assert "propose" in detail.json()["allowed_actions"]
    assert "close" in detail.json()["allowed_actions"]
    assert "close_silent" not in detail.json()["allowed_actions"]
    assert detail.json()["accept_preview"]["gaps"]

    missing_date = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=headers,
        json={"action": "propose", "note": "há vaga nessa data"},
    )
    assert missing_date.status_code == 422

    same_date = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=headers,
        json={"action": "propose", "proposed_date": created["desired_date"]},
    )
    assert same_date.status_code == 422

    other = _create_date(admin_client, "p67-date-2", days=12, name="Dora 67")
    proposed = admin_client.post(
        f"/api/v1/admin/date-requests/{other['id']}",
        headers=headers,
        json={"action": "propose", "proposed_date": _future(20), "note": "olha esta"},
    )
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["status"] == "alternative_proposed"
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=other["id"], kind="date_request_proposed")
        .count()
        == 1
    )

    silent = _create_date(admin_client, "p67-date-silent", days=14, name="Eva 67")
    closed = admin_client.post(
        f"/api/v1/admin/date-requests/{silent['id']}",
        headers=headers,
        json={"action": "close_silent"},
    )
    assert closed.status_code == 422
    blank = admin_client.post(
        f"/api/v1/admin/date-requests/{silent['id']}",
        headers=headers,
        json={"action": "close", "note": "   "},
    )
    assert blank.status_code == 422
    no_mail = DateRequest(
        desired_date=bakery_today(get_settings()) + timedelta(days=16),
        customer_name="Sem e-mail 67",
        customer_email=" ",
        intended_quantity=1,
        status="pending",
        idempotency_key="p67-no-mail",
        client_host="test",
    )
    db.add(no_mail)
    db.commit()
    missing_dest = admin_client.post(
        f"/api/v1/admin/date-requests/{no_mail.id}",
        headers=headers,
        json={"action": "close", "note": "não temos vaga"},
    )
    assert missing_dest.status_code == 422

    declined = _create_date(admin_client, "p67-date-close", days=15, name="Fia 67")
    answered = admin_client.post(
        f"/api/v1/admin/date-requests/{declined['id']}",
        headers=headers,
        json={"action": "close", "note": "nessa semana não dá"},
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["status"] == "closed"
    declined_mail = (
        db.query(EmailOutbox)
        .filter_by(date_request_id=declined["id"], kind="date_request_declined")
        .one()
    )
    assert "nessa semana não dá" in declined_mail.body
    assert declined_mail.status == "skipped"
    summary_after_close = admin_client.get("/api/v1/admin/ops/attendance-summary").json()
    assert all(item["id"] != declined["id"] for item in summary_after_close["priority"])


def test_accept_converts_once_and_incomplete_waits(admin_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    headers = {"X-CSRF-Token": csrf}
    incomplete = _create_date(admin_client, "p67-accept-gap")
    waiting = admin_client.post(
        f"/api/v1/admin/date-requests/{incomplete['id']}",
        headers=headers,
        json={"action": "accept"},
    )
    assert waiting.status_code == 422, waiting.text
    detail = waiting.json()["detail"].lower()
    assert "quantidade 1 está informada" in detail
    assert "confirme o produto" in detail
    assert waiting.json().get("status") != "awaiting_details"
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=incomplete["id"], kind="date_request_complete")
        .count()
        == 0
    )

    ready = _create_date(
        admin_client,
        "p67-accept-ok",
        name="Gia 67",
        desired_date=_wednesday(),
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{ready['id']}",
        headers=headers,
        json={"action": "accept", "address": NEW_ORDER_ADDRESS},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "converted"
    order_id = accepted.json()["converted_order_id"]
    assert order_id
    order = db.query(Order).filter_by(id=order_id).one()
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.source_date_request_id is not None
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert order.public_reference in mail.body
    assert "/pedido/" in mail.body
    again = admin_client.post(
        f"/api/v1/admin/date-requests/{ready['id']}",
        headers=headers,
        json={"action": "accept", "address": NEW_ORDER_ADDRESS},
    )
    assert again.status_code == 200
    assert again.json()["converted_order_id"] == order_id
    assert db.query(Order).filter_by(source_date_request_id=ready["id"]).count() == 1
    listed = admin_client.get("/api/v1/admin/orders").json()
    date_keys = [item["row_key"] for item in listed["items"] if item["id"] == ready["id"]]
    assert date_keys == []
    assert any(item["id"] == str(order.id) for item in listed["items"])

    standard = admin_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Auto 67",
            "customer_email": "auto-67@example.test",
            **NEW_ORDER_ADDRESS,
            "idempotency_key": "p67-auto-1",
        },
    )
    assert standard.status_code == 200, standard.text
    auto = db.query(Order).filter_by(public_reference=standard.json()["public_reference"]).one()
    assert auto.status == "confirmed"
    assert auto.holds_capacity is True
    assert db.query(EmailOutbox).filter_by(order_id=auto.id, kind="order_auto_accepted_admin").count() == 1
    assert db.query(EmailOutbox).filter_by(order_id=auto.id, kind="order_submitted").count() == 0


def test_summary_partial_failure_and_ops_dedupe(admin_client: TestClient, db: Session, monkeypatch) -> None:
    login(admin_client)
    empty = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert empty.status_code == 200
    assert empty.json()["unique_records"] == 0
    assert empty.json()["date_requests_awaiting"] == 0

    _create_date(admin_client, "p67-sum-1")
    summary = admin_client.get("/api/v1/admin/ops/attendance-summary").json()
    assert summary["date_requests_awaiting"] == 1
    assert summary["unique_records"] == 1
    assert summary["counts_are_subsets"] is True
    assert summary["priority"][0]["href"].startswith("/admin/pedidos/solicitacao/")

    csrf = login(admin_client)
    headers = {"X-CSRF-Token": csrf}
    first = admin_client.post("/api/v1/admin/ops/attendance-summary/dispatch", headers=headers)
    second = admin_client.post("/api/v1/admin/ops/attendance-summary/dispatch", headers=headers)
    assert first.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["dedupe_key"] == OPS_SUMMARY_DEDUPE
    assert db.query(EmailOutbox).filter_by(kind="ops_attendance_summary").count() == 1

    monkeypatch.setattr(
        "app.domain.attendance._load_orders",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("isolado")),
    )
    partial = admin_client.get("/api/v1/admin/orders").json()
    assert partial["orders_error"]
    assert partial["date_requests_error"] is None
    assert any(item["source"] == "date_request" for item in partial["items"])


def test_retry_does_not_duplicate_sent(admin_client: TestClient, db: Session, monkeypatch) -> None:
    created = _create_date(admin_client, "p67-retry")
    row = db.query(EmailOutbox).filter_by(date_request_id=created["id"], kind="date_request_received").one()
    row.status = "failed"
    row.last_error = "isolado"
    db.commit()
    csrf = login(admin_client)
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()

    def accept(*_args, **_kwargs):
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(accepted=True, message_id="ses-67", error=None)

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", accept)
    first = admin_client.post(f"/api/v1/admin/ops/outbox/{row.id}/retry", headers={"X-CSRF-Token": csrf})
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "sent"
    second = admin_client.post(f"/api/v1/admin/ops/outbox/{row.id}/retry", headers={"X-CSRF-Token": csrf})
    assert second.json()["status"] == "sent"
    assert db.query(EmailOutbox).filter_by(date_request_id=created["id"], kind="date_request_received").count() == 1
    process_due_outbox(db, get_settings())
    assert db.query(EmailOutbox).filter_by(date_request_id=created["id"], kind="date_request_received").count() == 1
    get_settings.cache_clear()


def test_admin_endpoints_require_auth(admin_client: TestClient) -> None:
    created = _create_date(admin_client, "p67-auth")
    assert admin_client.get("/api/v1/admin/ops/attendance-summary").status_code == 401
    assert admin_client.get(f"/api/v1/admin/date-requests/{created['id']}").status_code == 401
    assert admin_client.get("/api/v1/admin/orders").status_code == 401
