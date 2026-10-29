"""Adendo 101C: pronto sem entrega segue vigente e a produção exige confirmação. Dados fictícios."""

import pytest
from app.domain.errors import TransitionError, UnpaidProductionError
from app.domain.orders import (
    MARK_READY_REASON,
    confirm_order,
    correct_ready_to_in_production,
    transition_order,
)
from app.models.enums import OrderStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import draft_order, priced_catalog
from tests.test_prompt101b import _board, _confirm, _counts, _headers, _history, _pay, _stage

assert admin_client


def test_ready_page_matches_the_current_exception(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 4
    catalog["slot"].capacity_units = 4
    first = draft_order(db, catalog)
    second = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    for order in (first, second):
        _confirm(admin_client, csrf, order)
        db.expire_all()
        current = db.get(Order, order.id)
        _pay(db, current, "paid", paid=current.total_cents)
        assert admin_client.post(
            f"/api/v1/admin/orders/{order.id}/start-production", headers=headers
        ).status_code == 200
        marked = admin_client.post(f"/api/v1/admin/orders/{order.id}/mark-ready", headers=headers)
        assert marked.status_code == 200, marked.text
        assert marked.json()["visible_label"] == "Pronto — aguardando confirmação de entrega"
        assert marked.json()["visible_stage"] == "ready_legacy"
    board = _board(admin_client)
    assert _stage(board, "stage:ready_legacy") == 2
    assert _stage(board, "stage:delivered") == 0
    assert sum(item["count"] for item in board["stages"]) + 2 == board["operational_total"]
    page = admin_client.get(
        "/api/v1/admin/orders", params={"lens": "stage:ready_legacy", "page": 1, "page_size": 1}
    )
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 2
    second_page = admin_client.get(
        "/api/v1/admin/orders", params={"lens": "stage:ready_legacy", "page": 2, "page_size": 1}
    )
    refs = {page.json()["items"][0]["public_reference"], second_page.json()["items"][0]["public_reference"]}
    assert refs == {first.public_reference, second.public_reference}
    assert all(
        item["visible_label"] == "Pronto — aguardando confirmação de entrega"
        for item in page.json()["items"] + second_page.json()["items"]
    )
    queue = admin_client.get("/api/v1/admin/orders")
    assert queue.json()["total"] == board["operational_total"]
    assert refs <= {item["public_reference"] for item in queue.json()["items"]}


def test_accepted_and_paid_filters_use_the_financial_class(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 4
    catalog["slot"].capacity_units = 4
    waiting = draft_order(db, catalog)
    paid = draft_order(db, catalog)
    free = draft_order(db, catalog)
    producing = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    for order in (waiting, paid, free, producing):
        _confirm(admin_client, csrf, order)
    db.expire_all()
    paid = db.get(Order, paid.id)
    free = db.get(Order, free.id)
    producing = db.get(Order, producing.id)
    _pay(db, paid, "paid", paid=paid.total_cents)
    free.total_cents = 0
    free.order_kind = "redemption"
    _pay(db, producing, "pending")
    db.commit()
    started = admin_client.post(
        f"/api/v1/admin/orders/{producing.id}/start-production",
        headers=headers,
        json={"unpaid_exception": True},
    )
    assert started.status_code == 200, started.text
    assert started.json()["visible_label"] == "Em produção"
    assert started.json()["payment_attention"] == "Pagamento pendente"
    accepted = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:accepted"})
    paid_rows = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:paid"})
    production = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:in_production"})
    accepted_refs = {item["public_reference"] for item in accepted.json()["items"]}
    paid_refs = {item["public_reference"] for item in paid_rows.json()["items"]}
    assert waiting.public_reference in accepted_refs
    assert free.public_reference in accepted_refs
    assert paid.public_reference not in accepted_refs
    assert producing.public_reference not in accepted_refs
    assert paid_refs == {paid.public_reference}
    assert production.json()["items"][0]["public_reference"] == producing.public_reference
    assert production.json()["items"][0]["visible_label"] == "Em produção"
    board = _board(admin_client)
    assert _stage(board, "stage:accepted") == accepted.json()["total"] == 2
    assert _stage(board, "stage:paid") == paid_rows.json()["total"] == 1
    assert _stage(board, "stage:in_production") == 1


def test_direct_transition_cannot_skip_the_payment_confirmation(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    confirm_order(db, order.id, actor_ref="test:101c")
    db.commit()
    with pytest.raises(UnpaidProductionError):
        transition_order(db, order.id, OrderStatus.IN_PRODUCTION.value, actor_ref="test:101c")
    db.rollback()
    db.expire_all()
    order = db.get(Order, order.id)
    assert order.status == "confirmed"
    assert [row.to_status for row in _history(db, order.id)] == ["confirmed"]
    started = transition_order(
        db,
        order.id,
        OrderStatus.IN_PRODUCTION.value,
        actor_ref="test:101c",
        unpaid_exception=True,
    )
    assert started.status == "in_production"
    reasons = [row.reason for row in _history(db, order.id) if row.to_status == "in_production"]
    assert len(reasons) == 1
    assert reasons[0] and "financeiro observado" in reasons[0]
    again = transition_order(
        db,
        order.id,
        OrderStatus.IN_PRODUCTION.value,
        actor_ref="test:101c",
        unpaid_exception=True,
    )
    assert again.status == "in_production"
    assert len([row for row in _history(db, order.id) if row.to_status == "in_production"]) == 1

    paid = draft_order(db, catalog)
    db.commit()
    confirm_order(db, paid.id, actor_ref="test:101c")
    db.expire_all()
    paid = db.get(Order, paid.id)
    _pay(db, paid, "paid", paid=paid.total_cents)
    plain = transition_order(db, paid.id, OrderStatus.IN_PRODUCTION.value, actor_ref="test:101c")
    assert plain.status == "in_production"
    assert [row.reason for row in _history(db, paid.id) if row.to_status == "in_production"] == [None]


def test_ready_repair_keeps_payment_reservation_and_silence(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    other = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    for row in (order, other):
        _confirm(admin_client, csrf, row)
        db.expire_all()
        current = db.get(Order, row.id)
        _pay(db, current, "paid", paid=current.total_cents)
        assert admin_client.post(
            f"/api/v1/admin/orders/{row.id}/start-production", headers=headers
        ).status_code == 200
        marked = admin_client.post(f"/api/v1/admin/orders/{row.id}/mark-ready", headers=headers)
        assert marked.status_code == 200, marked.text
    db.expire_all()
    order = db.get(Order, order.id)
    ready_at = order.ready_at
    total = order.total_cents
    capacity = order.holds_capacity
    payments = int(db.scalar(select(func.count()).select_from(PaymentRecord)) or 0)
    paid_cents = db.scalar(
        select(PaymentRecord.amount_paid_cents).where(PaymentRecord.order_id == order.id)
    )
    before = _counts(db)
    previous = len(_history(db, order.id))
    corrected = correct_ready_to_in_production(db, order.id, actor_ref="assisted:101c")
    db.commit()
    assert corrected.status == "in_production"
    assert corrected.total_cents == total ==  paid_cents
    assert corrected.holds_capacity is capacity is True
    assert corrected.ready_at == ready_at
    assert corrected.delivery_confirmed_at is None
    assert _counts(db)[1] == before[1]
    assert int(db.scalar(select(func.count()).select_from(PaymentRecord)) or 0) == payments
    rows = _history(db, order.id)
    assert len(rows) == previous + 1
    assert rows[-1].from_status == "ready"
    assert rows[-1].to_status == "in_production"
    assert rows[-1].actor_ref == "assisted:101c"
    assert "anterior=ready" in rows[-1].reason
    assert "novo=in_production" in rows[-1].reason
    assert any(row.reason == MARK_READY_REASON for row in rows)
    board = _board(admin_client)
    assert _stage(board, "stage:in_production") == 1
    assert _stage(board, "stage:ready_legacy") == 1
    listed = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:in_production"})
    assert listed.json()["items"][0]["public_reference"] == order.public_reference
    untouched = db.get(Order, other.id)
    assert untouched.status == "ready"
    with pytest.raises(TransitionError, match="não está em pronto"):
        correct_ready_to_in_production(db, order.id, actor_ref="assisted:101c")
    db.rollback()
    assert len(_history(db, order.id)) == previous + 1
