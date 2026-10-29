from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.house_fidelity import FOCACCIA_SLUG, lines_qualify_for_stamp
from app.domain.house_fidelity_admin import apply_manual_adjustment, participant_detail
from app.domain.house_fidelity_ledger import (
    apply_omitted_stamps,
    omitted_stamp_candidates,
    reconcile_order,
)
from app.domain.house_fidelity_redeem import eligible_500g_variants
from app.domain.date_request_accept import recover_order_address_from_linked_request
from app.domain.orders import delivery_missing_fields, transition_order
from app.domain.storefront_orders import email_access_token
from app.models.enums import OrderStatus
from app.models.house_fidelity import HouseFidelityCredit, HouseFidelityEvent
from app.models.date_requests import DateRequest
from app.models.orders import Order
from app.models.products import Product
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS, draft_order, priced_catalog
from tests.test_house_fidelity_ledger import (
    _account,
    _campaign,
    _close,
    _order,
    _pay,
    _product,
    _qualify,
    _settings,
)
from tests.test_prompt68 import _accept, _create_date, _product as _date_product, _wednesday

assert admin_client


def test_todos_finalizados_and_name_search_finds_history(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    current = draft_order(db, catalog)
    current.status = OrderStatus.CONFIRMED.value
    current.confirmed_at = datetime.now(UTC)
    done = draft_order(db, catalog)
    done.customer_name = "Osváldo Histórico"
    done.status = OrderStatus.COMPLETED.value
    cancelled = draft_order(db, catalog)
    cancelled.customer_name = "Outro"
    cancelled.status = OrderStatus.CANCELLED.value
    db.commit()
    login(admin_client)

    queue = admin_client.get("/api/v1/admin/orders")
    assert queue.status_code == 200
    queue_refs = {item["public_reference"] for item in queue.json()["items"]}
    assert current.public_reference in queue_refs
    assert done.public_reference not in queue_refs
    assert cancelled.public_reference not in queue_refs
    assert queue.json()["search_scope"] == "fila operacional"
    counts = queue.json()["state_counts"]
    assert counts["queue"] >= 1
    assert counts["completed"] >= 1
    assert counts["cancelled"] >= 1
    assert counts["all"] >= counts["queue"] + counts["completed"] + counts["cancelled"]

    todos = admin_client.get("/api/v1/admin/orders", params={"status": "all"})
    todos_refs = {item["public_reference"] for item in todos.json()["items"]}
    assert current.public_reference in todos_refs
    assert done.public_reference in todos_refs
    assert cancelled.public_reference in todos_refs
    assert todos.json()["search_scope"] == "todos os estados"

    finished = admin_client.get("/api/v1/admin/orders", params={"status": "completed"})
    finished_refs = {item["public_reference"] for item in finished.json()["items"]}
    assert done.public_reference in finished_refs
    assert cancelled.public_reference not in finished_refs

    cancelled_list = admin_client.get("/api/v1/admin/orders", params={"status": "cancelled"})
    cancelled_refs = {item["public_reference"] for item in cancelled_list.json()["items"]}
    assert cancelled.public_reference in cancelled_refs
    assert done.public_reference not in cancelled_refs

    by_name = admin_client.get("/api/v1/admin/orders", params={"reference": "osvaldo"})
    assert by_name.json()["search_scope"] == "histórico completo"
    name_refs = {item["public_reference"] for item in by_name.json()["items"]}
    assert done.public_reference in name_refs
    assert current.public_reference not in name_refs
    accent = admin_client.get("/api/v1/admin/orders", params={"reference": "Osváldo"})
    assert done.public_reference in {item["public_reference"] for item in accent.json()["items"]}
    partial = admin_client.get("/api/v1/admin/orders", params={"reference": "osv"})
    assert done.public_reference in {item["public_reference"] for item in partial.json()["items"]}
    by_ref = admin_client.get(
        "/api/v1/admin/orders", params={"reference": done.public_reference}
    )
    assert by_ref.json()["total"] == 1


def test_paid_in_production_address_shows_missing_fields_in_admin(
    admin_client: TestClient, db: Session, monkeypatch
) -> None:
    variant = _date_product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p72-addr",
        name="Cliente 72",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    transition_order(
        db, order.id, OrderStatus.IN_PRODUCTION.value, unpaid_exception=True, actor_ref="test:prompt72"
    )
    db.commit()
    token = email_access_token(get_settings(), order)
    before = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert before.json()["delivery_pending"] is True
    assert "rua" in before.json()["delivery_missing_fields"]
    assert before.json()["linked_delivery_filled_fields"] == []
    assert not (before.json()["address"]["street"] or "")

    saved = admin_client.post(
        f"/api/v1/storefront/orders/{order.public_reference}/delivery-address",
        headers={"X-Order-Token": token, "Content-Type": "application/json"},
        json=NEW_ORDER_ADDRESS,
    )
    assert saved.status_code == 200, saved.text
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    assert delivery_missing_fields(order) == []
    after = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert after.json()["delivery_pending"] is False
    assert after.json()["address"]["street"] == NEW_ORDER_ADDRESS["delivery_street"]
    assert after.json()["delivery_missing_fields"] == []
    assert after.json()["status"] == "in_production"


def test_recover_address_from_linked_request_not_overwrite(
    admin_client: TestClient, db: Session
) -> None:
    variant = _date_product(db)
    db.commit()
    csrf = login(admin_client)
    created = _create_date(
        admin_client,
        "p72-rec-ok",
        name="Cliente Rec 72",
        lines=[{"variant_id": str(variant.id), "quantity": 1}],
    )
    accepted = _accept(admin_client, csrf, created["id"])
    order = db.query(Order).filter_by(id=accepted.json()["converted_order_id"]).one()
    request = db.get(DateRequest, created["id"])
    request.complement = {
        "delivery_street": NEW_ORDER_ADDRESS["delivery_street"],
        "delivery_number": NEW_ORDER_ADDRESS["delivery_number"],
        "delivery_district": NEW_ORDER_ADDRESS["delivery_district"],
        "delivery_city": NEW_ORDER_ADDRESS["delivery_city"],
        "delivery_state": NEW_ORDER_ADDRESS["delivery_state"],
        "delivery_postal_code": NEW_ORDER_ADDRESS["delivery_postal_code"],
        "delivery_complement": None,
    }
    db.flush()
    result = recover_order_address_from_linked_request(db, order)
    assert result["applied"] is True
    db.refresh(order)
    assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
    again = recover_order_address_from_linked_request(db, order)
    assert again["applied"] is False
    assert again["reason"] == "order_has_address"


def test_focaccia_stamps_but_cannot_be_prize(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    focaccia = _product(db)
    product = db.get(Product, focaccia.product_id)
    product.slug = FOCACCIA_SLUG
    product.fidelity_eligible = False
    db.flush()
    quoted = [
        {
            "origin": "product",
            "product_id": str(focaccia.product_id),
            "variant_id": str(focaccia.id),
            "line_cents": 9000,
        }
    ]
    assert lines_qualify_for_stamp(db, quoted) is True
    assert all(item["slug"] != FOCACCIA_SLUG for item in eligible_500g_variants(db))

    for _ in range(4):
        order = _order(db, account, campaign, focaccia, total=9000)
        order.status = OrderStatus.IN_PRODUCTION.value
        order.confirmed_at = datetime.now(UTC)
        _pay(db, order)
        reconcile_order(db, settings, order)
    events = list(
        db.scalars(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.account_id == account.id,
                HouseFidelityEvent.kind == "qualify",
                HouseFidelityEvent.status == "applied",
            )
        )
    )
    assert len(events) == 4
    credits = list(
        db.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.account_id == account.id,
                HouseFidelityCredit.status == "available",
            )
        )
    )
    assert len(credits) == 1


def test_manual_grant_blocks_ambiguous_reprocess(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    focaccia = _product(db)
    product = db.get(Product, focaccia.product_id)
    product.slug = FOCACCIA_SLUG
    product.fidelity_eligible = False
    db.flush()
    order = _order(db, account, campaign, focaccia, total=9000)
    _close(db, order)
    _pay(db, order)
    apply_manual_adjustment(
        db,
        settings,
        account_id=str(account.id),
        kind="grant",
        reason="cortesia do proprietário",
        actor_ref="admin",
    )
    candidates = omitted_stamp_candidates(db, settings)
    assert order.public_reference in {row["public_reference"] for row in candidates}
    assert any(row["has_manual_grant"] for row in candidates if row["public_reference"] == order.public_reference)
    applied = apply_omitted_stamps(db, settings, skip_accounts_with_manual_grant=True)
    assert order.public_reference not in applied
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == order.id)) is None
    detail = participant_detail(db, settings, str(account.id))
    assert detail["manual_adjustments_count"] >= 1
    assert detail["valid_orders_month"] == 0
    row = next(item for item in detail["month_orders"] if item["public_reference"] == order.public_reference)
    assert row["stamped"] is False
