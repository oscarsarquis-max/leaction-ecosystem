from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.admin_orders import attendance_health
from app.domain.bakery_time import bakery_today
from app.domain.email_outbox import process_due_outbox
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import submit_order
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, FinancialStatus, PaymentProvider
from app.models.orders import Order
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_custom_loaf import _catalog, _payload
from tests.test_schedule import _next_iso

assert admin_client


def _wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta or 7)
    return day.isoformat()


def _product(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 66")
    product = Product(
        name="Pão 66",
        slug=f"pao-66-{uuid4().hex[:8]}",
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


def test_submit_outbox_list_and_old_submitted_stay_visible(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    day = _wednesday()
    payload = {
        "requested_date": day,
        "items": [{"variant_id": str(variant.id), "quantity": 1}],
        "quoted_cents": 2490,
        "customer_name": "Ana",
        "customer_email": "ana-66@example.test",
        **NEW_ORDER_ADDRESS,
        "idempotency_key": "p66-standard-1",
    }
    first = admin_client.post("/api/v1/storefront/orders", json=payload)
    second = admin_client.post("/api/v1/storefront/orders", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json()["public_reference"] == second.json()["public_reference"]
    ref = first.json()["public_reference"]
    order = db.query(Order).filter_by(public_reference=ref).one()
    customer = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    admin_mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_auto_accepted_admin").one()
    assert customer.status == "skipped"
    assert admin_mail.status == "skipped"
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_submitted").count() == 0

    listed = admin_client.get("/api/v1/admin/orders")
    assert listed.status_code == 200
    refs = {item["public_reference"] for item in listed.json()["items"]}
    assert ref in refs
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert detail.status_code == 200
    assert detail.json()["public_reference"] == ref
    assert detail.json()["items"][0]["origin"] == "product"
    assert detail.json()["production_local_date"] == day

    catalog = _catalog(db)
    custom, _token = submit_order(db, get_settings(), _payload(catalog, idempotency_key="p66-custom"))
    aged = db.query(Order).filter_by(public_reference=ref).one()
    aged.created_at = datetime.now(UTC) - timedelta(hours=30)
    paid_order, _paid_token = submit_order(db, get_settings(), _payload(catalog, idempotency_key="p66-paid"))
    paid_order.created_at = datetime.now(UTC) - timedelta(hours=40)
    db.add(
        PaymentRecord(
            order_id=paid_order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=paid_order.total_cents or 0,
            amount_paid_cents=paid_order.total_cents or 0,
            currency="BRL",
            financial_status=FinancialStatus.PAID.value,
        )
    )
    historical = Order(
        public_reference="LPHIST66PICK",
        status="submitted",
        fulfillment_modality="pickup",
        customer_name="Histórico",
        customer_email="hist-66@example.test",
        currency="BRL",
        total_cents=100,
        created_at=datetime.now(UTC) - timedelta(days=8),
    )
    db.add(historical)
    db.flush()
    db.commit()

    page1 = admin_client.get("/api/v1/admin/orders", params={"page": 1, "page_size": 2})
    assert page1.status_code == 200
    assert page1.json()["total"] >= 4
    all_refs: set[str] = set()
    page = 1
    while True:
        body = admin_client.get(
            "/api/v1/admin/orders", params={"page": page, "page_size": 2}
        ).json()
        all_refs.update(item["public_reference"] for item in body["items"])
        if page * 2 >= body["total"]:
            break
        page += 1
    assert ref in all_refs
    assert custom.public_reference in all_refs
    assert paid_order.public_reference in all_refs
    assert historical.public_reference in all_refs

    future = (_next_iso(3) + timedelta(days=14)).isoformat()
    date_req = admin_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": future,
            "customer_name": "Bia",
            "customer_email": "bia-66@example.test",
            "intended_quantity": 1,
            "idempotency_key": "p66-date-1",
        },
    )
    assert date_req.status_code == 200, date_req.text
    again = admin_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": future,
            "customer_name": "Bia",
            "customer_email": "bia-66@example.test",
            "intended_quantity": 1,
            "idempotency_key": "p66-date-1",
        },
    )
    assert again.json()["id"] == date_req.json()["id"]
    dates = admin_client.get("/api/v1/admin/date-requests", headers={"X-CSRF-Token": csrf})
    assert dates.status_code == 200
    assert dates.json()["pending_count"] >= 1
    assert any(item["id"] == date_req.json()["id"] for item in dates.json()["items"])
    listed_orders = admin_client.get("/api/v1/admin/orders").json()["items"]
    assert any(item["id"] == date_req.json()["id"] and item["source"] == "date_request" for item in listed_orders)
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=date_req.json()["id"], kind="date_request_received")
        .count()
        == 1
    )
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=date_req.json()["id"], kind="date_request_received_admin")
        .count()
        == 1
    )

    health = admin_client.get("/api/v1/admin/ops/attendance-health").json()
    assert health["hidden_submitted"] == 0
    assert health["discrepancy"] is False
    assert health["open_date_requests"] >= 1
    assert health["page_size_default"] == 20
    listed_all = admin_client.get("/api/v1/admin/orders", params={"page_size": 50}).json()
    assert listed_all["total"] == health["queue_total"]


def test_email_failure_does_not_hide_order(admin_client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-66@example.test")
    get_settings.cache_clear()
    catalog = _catalog(db)
    from app.domain.storefront_orders import submit_order

    order, _token = submit_order(db, get_settings(), _payload(catalog, idempotency_key="p66-mail-fail"))
    row = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_submitted").one()
    row.status = "pending"
    db.flush()

    def boom(*_args, **_kwargs):
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(accepted=False, message_id=None, error="ses-isolado")

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", boom)
    process_due_outbox(db, get_settings())
    db.refresh(row)
    assert row.status == "failed"
    db.commit()
    login(admin_client)
    refs = {item["public_reference"] for item in admin_client.get("/api/v1/admin/orders").json()["items"]}
    assert order.public_reference in refs
    health = attendance_health(db)
    assert health["hidden_submitted"] == 0
    get_settings.cache_clear()
