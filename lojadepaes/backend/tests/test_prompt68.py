from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.attendance import date_request_reference
from app.domain.bakery_time import bakery_today
from app.domain.date_request_accept import date_request_access_token
from app.domain.date_requests import apply_date_request_action
from app.domain.email_outbox import process_due_outbox
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import save_date_override
from app.domain.storefront_orders import email_access_token
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, FinancialStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from app.schemas.suggestions import DateRequestActionIn
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
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 68")
    product = Product(
        name="Focaccia Alta",
        slug=f"focaccia-68-{uuid4().hex[:8]}",
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
    *,
    name: str = "Bia 68",
    desired_date: str | None = None,
    lines: list | None = None,
) -> dict:
    payload = {
        "desired_date": desired_date or _future(10),
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


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def _accept(client: TestClient, csrf: str, request_id: str, **extra) -> object:
    return client.post(
        f"/api/v1/admin/date-requests/{request_id}",
        headers=_headers(csrf),
        json={"action": "accept", **extra},
    )


def test_accept_without_address_creates_order_and_payment_link(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p68-no-addr",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    preview = admin_client.get(
        f"/api/v1/admin/date-requests/{created['id']}", headers=_headers(csrf)
    ).json()["accept_preview"]
    assert preview["can_accept"] is True
    assert preview["delivery_pending"] is True
    assert "endereço" not in " ".join(preview["gaps"]).lower()

    accepted = _accept(admin_client, csrf, created["id"])
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "converted"
    assert body["converted_order_id"]
    order = db.query(Order).filter_by(id=body["converted_order_id"]).one()
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert order.delivery_street is None
    assert order.total_cents == 2490
    mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    assert "/pedido/" in mail.body
    assert "complete os dados de entrega" in mail.body
    assert mail.dedupe_key == f"{order.id}:order_accepted"
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=created["id"], kind="date_request_complete")
        .count()
        == 0
    )

    listed = admin_client.get("/api/v1/admin/orders").json()
    assert not any(item["id"] == created["id"] for item in listed["items"])
    order_row = next(item for item in listed["items"] if item["id"] == str(order.id))
    assert order_row["delivery_pending"] is True
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}", headers=_headers(csrf)).json()
    assert detail["delivery_pending"] is True


def test_payment_without_address_then_complement_preserves_order(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p68-pay-ok",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    token = email_access_token(get_settings(), order)
    view = admin_client.get(
        f"/api/v1/storefront/orders/{order.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert view.status_code == 200, view.text
    assert view.json()["payment_available"] is True
    assert view.json()["delivery_pending"] is True

    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-68",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix68",
            pix_qr_code_base64="abc",
        ),
    )
    pay = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert pay.status_code == 200, pay.text
    assert pay.json()["pix"]["qr_code"] == "00020126pix68"

    saved = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/delivery-address",
        json=NEW_ORDER_ADDRESS,
        headers={"X-Order-Token": token},
    )
    assert saved.status_code == 200, saved.text
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    assert order.total_cents == 2490
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1


def test_double_click_and_lost_response_are_idempotent(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p68-idemp",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    first = _accept(admin_client, csrf, created["id"])
    lost = _accept(admin_client, csrf, created["id"])
    assert first.status_code == 200
    assert lost.status_code == 200
    assert first.json()["converted_order_id"] == lost.json()["converted_order_id"]
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
    assert db.query(EmailOutbox).filter_by(kind="order_accepted").count() == 1
    events = db.query(DateRequestEvent).filter_by(request_id=created["id"], action="converted").all()
    assert len(events) == 1

    raced = _create_date(
        admin_client,
        "p68-race",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    race_id = UUID(raced["id"])
    engine = get_engine()

    def _race(_key: str) -> str:
        with Session(engine) as session:
            apply_date_request_action(
                session,
                get_settings(),
                race_id,
                DateRequestActionIn(action="accept"),
                actor_ref="race",
            )
            session.commit()
            row = session.get(DateRequest, race_id)
            assert row is not None
            return str(row.converted_order_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_race, ["a", "b"]))
    assert results[0] == results[1] != "None"
    assert db.query(Order).filter_by(source_date_request_id=race_id).count() == 1
    assert db.query(DateRequestEvent).filter_by(request_id=race_id, action="converted").count() == 1


def test_recover_awaiting_details_with_and_without_partial_order(
    admin_client: TestClient, db: Session
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    legacy = _create_date(
        admin_client,
        "p68-legacy",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    request = db.get(DateRequest, legacy["id"])
    request.status = "awaiting_details"
    request.accept_authorized_at = datetime.now(UTC)
    db.add(
        DateRequestEvent(
            request_id=request.id,
            action="awaiting_details",
            actor_ref="admin",
            detail="aceite autorizado; faltam dados para formalizar o pedido",
        )
    )
    db.add(
        DateRequestEvent(
            request_id=request.id,
            action="awaiting_details",
            actor_ref="admin",
            detail="aceite autorizado; faltam dados para formalizar o pedido",
        )
    )
    db.commit()
    recovered = _accept(admin_client, csrf, legacy["id"])
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "converted"
    order = db.query(Order).filter_by(id=recovered.json()["converted_order_id"]).one()
    assert order.status == "confirmed"
    awaiting = (
        db.query(DateRequestEvent).filter_by(request_id=legacy["id"], action="awaiting_details").count()
    )
    assert awaiting == 2
    converted = db.query(DateRequestEvent).filter_by(request_id=legacy["id"], action="converted").one()
    assert "recuperação do aceite já autorizado" in (converted.detail or "")
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1

    partial = _create_date(
        admin_client,
        "p68-partial",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    first = _accept(admin_client, csrf, partial["id"])
    existing = db.query(Order).filter_by(id=first.json()["converted_order_id"]).one()
    request = db.get(DateRequest, partial["id"])
    request.status = "awaiting_details"
    request.converted_order_id = None
    request.closed_at = None
    db.commit()
    again = _accept(admin_client, csrf, partial["id"])
    assert again.status_code == 200
    assert again.json()["converted_order_id"] == str(existing.id)
    assert db.query(Order).filter_by(source_date_request_id=partial["id"]).count() == 1


def test_outbox_retry_exceptional_date_capacity_past_paid_and_standard(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)

    created = _create_date(
        admin_client,
        "p68-outbox",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    row = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
    row.status = "failed"
    row.last_error = "isolado"
    db.commit()
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    get_settings.cache_clear()

    def accept_mail(*_args, **_kwargs):
        from app.domain.ses_mailer import MailSendResult

        return MailSendResult(accepted=True, message_id="ses-68", error=None)

    monkeypatch.setattr("app.domain.email_outbox.send_outbox_email", accept_mail)
    first = admin_client.post(f"/api/v1/admin/ops/outbox/{row.id}/retry", headers=headers)
    second = admin_client.post(f"/api/v1/admin/ops/outbox/{row.id}/retry", headers=headers)
    assert first.json()["status"] == "sent"
    assert second.json()["status"] == "sent"
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1
    process_due_outbox(db, get_settings())
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == 1
    get_settings.cache_clear()

    today = bakery_today(get_settings())
    same_day = _create_date(
        admin_client,
        "p68-today",
        desired_date=today.isoformat(),
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    today_ok = _accept(admin_client, csrf, same_day["id"])
    assert today_ok.status_code == 200, today_ok.text
    today_order = db.query(Order).filter_by(id=today_ok.json()["converted_order_id"]).one()
    assert today_order.production_local_date == today
    assert today_order.holds_capacity is True

    crowded = bakery_today(get_settings()) + timedelta(days=14)
    save_date_override(
        db,
        get_settings(),
        crowded,
        open_state="open",
        daily_physical_limit=1,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    db.commit()
    first_cap = _create_date(
        admin_client,
        "p68-cap-a",
        desired_date=crowded.isoformat(),
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    second_cap = _create_date(
        admin_client,
        "p68-cap-b",
        desired_date=crowded.isoformat(),
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    assert _accept(admin_client, csrf, first_cap["id"]).status_code == 200
    blocked = _accept(admin_client, csrf, second_cap["id"])
    assert blocked.status_code == 409
    assert db.query(Order).filter_by(source_date_request_id=second_cap["id"]).count() == 0

    past = DateRequest(
        desired_date=bakery_today(get_settings()) - timedelta(days=1),
        customer_name="Passada 68",
        customer_email="passada-68@example.test",
        intended_quantity=1,
        status="pending",
        cart_context=[
            {
                "variant_id": str(variant.id),
                "product_name": "Focaccia Alta",
                "variant_name": "500 g",
                "quantity": 1,
            }
        ],
        idempotency_key="p68-past",
        client_host="test",
    )
    db.add(past)
    db.commit()
    past_res = _accept(admin_client, csrf, str(past.id))
    assert past_res.status_code == 422
    assert "passada" in past_res.json()["detail"]

    paid_req = _create_date(
        admin_client,
        "p68-paid",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    paid_acc = _accept(admin_client, csrf, paid_req["id"])
    paid_order = db.query(Order).filter_by(id=paid_acc.json()["converted_order_id"]).one()
    credit_before = paid_order.fidelity_credit_id
    record = db.query(PaymentRecord).filter_by(order_id=paid_order.id).one()
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = paid_order.total_cents
    db.commit()
    token = email_access_token(get_settings(), paid_order)
    charged = admin_client.post(
        f"/api/v1/storefront/orders/{paid_order.public_reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert charged.status_code == 422
    again = _accept(admin_client, csrf, paid_req["id"])
    assert again.json()["converted_order_id"] == str(paid_order.id)
    db.refresh(paid_order)
    assert paid_order.fidelity_credit_id == credit_before
    assert db.query(PaymentRecord).filter_by(order_id=paid_order.id).count() == 1

    standard = admin_client.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": _wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 2490,
            "customer_name": "Auto 68",
            "customer_email": "auto-68@example.test",
            **NEW_ORDER_ADDRESS,
            "idempotency_key": "p68-auto-1",
        },
    )
    assert standard.status_code == 200, standard.text
    auto = db.query(Order).filter_by(public_reference=standard.json()["public_reference"]).one()
    assert auto.status == "confirmed"
    assert auto.holds_capacity is True

    close = _create_date(admin_client, "p68-close")
    closed = admin_client.post(
        f"/api/v1/admin/date-requests/{close['id']}",
        headers=headers,
        json={"action": "close", "note": "nessa semana não dá"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert (
        db.query(EmailOutbox)
        .filter_by(date_request_id=close["id"], kind="date_request_declined")
        .count()
        == 1
    )
    assert date_request_reference(close["id"]).startswith("SD")


def test_complement_page_updates_existing_order(admin_client: TestClient, db: Session) -> None:
    variant = _product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p68-complete",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    request = db.get(DateRequest, created["id"])
    token = date_request_access_token(get_settings(), request)
    public = admin_client.get(
        f"/api/v1/schedule/date-requests/{created['id']}", params={"token": token}
    )
    assert public.status_code == 200
    assert public.json()["converted"] is True
    assert public.json()["delivery_pending"] is True
    assert "/pedido/" in (public.json()["order_href"] or "")
    filled = admin_client.post(
        f"/api/v1/schedule/date-requests/{created['id']}/complete",
        json={"token": token, **NEW_ORDER_ADDRESS},
    )
    assert filled.status_code == 200, filled.text
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    assert order.total_cents == 2490
    assert db.query(Order).filter_by(source_date_request_id=created["id"]).count() == 1
