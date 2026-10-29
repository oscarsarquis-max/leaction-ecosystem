"""Resumo gerencial: contagem, filtro e leitura sem mutação. Dados fictícios."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.orders import new_public_reference
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderItem, OrderItemAdaptation
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS, priced_catalog

assert admin_client


def _order(db: Session, catalog: dict, **fields) -> Order:
    loaves = fields.pop("loaves", 0)
    adapt = fields.pop("adapt", 0)
    pay = fields.pop("pay", None)
    notices = fields.pop("notices", ())
    order = Order(
        public_reference=new_public_reference(),
        currency="BRL",
        customer_note="",
        customer_name=fields.pop("customer_name", "Cliente Ficticio"),
        customer_email=fields.pop("customer_email", f"c-{uuid4().hex[:8]}@example.test"),
        **fields,
    )
    db.add(order)
    db.flush()
    if adapt:
        for _ in range(adapt):
            item = OrderItem(
                order_id=order.id,
                dough_type_id=catalog["dough"].id,
                bread_shape_id=catalog["shape"].id,
                quantity=1,
            )
            db.add(item)
            db.flush()
            db.add(
                OrderItemAdaptation(
                    order_item_id=item.id,
                    customer_text="sem sementes",
                    reason="preference",
                    status="pending",
                )
            )
    elif loaves:
        db.add(
            OrderItem(
                order_id=order.id,
                dough_type_id=catalog["dough"].id,
                bread_shape_id=catalog["shape"].id,
                quantity=loaves,
            )
        )
    if pay:
        db.add(
            PaymentRecord(
                order_id=order.id,
                provider="actionhub",
                external_reference=pay.get("external"),
                idempotency_key=f"p101-{order.id}-{pay['status']}",
                expected_cents=order.total_cents or 0,
                currency="BRL",
                financial_status=pay["status"],
                amount_paid_cents=pay.get("paid"),
                amount_refunded_cents=pay.get("refunded"),
            )
        )
    base = datetime.now(UTC)
    for offset, kind, status in notices:
        db.add(
            EmailOutbox(
                order_id=order.id,
                kind=kind,
                to_address="cliente@example.test",
                subject="aviso",
                body="texto ficticio",
                status=status,
                dedupe_key=f"p101-{uuid4().hex}",
                created_at=base + timedelta(seconds=offset),
            )
        )
    db.flush()
    return order


def _date(db: Session, **fields) -> DateRequest:
    row = DateRequest(
        customer_name=fields.pop("customer_name", "Solicitante Ficticio"),
        customer_email=fields.pop("customer_email", f"s-{uuid4().hex[:8]}@example.test"),
        idempotency_key=f"p101-{uuid4().hex}",
        client_host="test",
        intended_quantity=fields.pop("intended_quantity", 1),
        **fields,
    )
    db.add(row)
    db.flush()
    return row


def _counts(db: Session) -> tuple[int, int, int, int]:
    db.expire_all()
    return (
        db.scalar(select(func.count()).select_from(Order)),
        db.scalar(select(func.count()).select_from(DateRequest)),
        db.scalar(select(func.count()).select_from(EmailOutbox)),
        db.scalar(select(func.count()).select_from(PaymentRecord)),
    )


def _metric(board: dict, group: str, lens: str) -> int:
    found = [item for item in board[group] if item["lens"] == lens]
    assert len(found) == 1
    return found[0]["count"]


def _collect(client: TestClient, lens: str) -> list[dict]:
    first = client.get("/api/v1/admin/orders", params={"lens": lens, "page": 1, "page_size": 1})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["filter_label"]
    assert body["search_scope"] == body["filter_label"]
    total = body["total"]
    rows = list(body["items"])
    for page in range(2, total + 1):
        nxt = client.get(
            "/api/v1/admin/orders",
            params={"lens": lens, "page": page, "page_size": 1},
        )
        assert nxt.status_code == 200, nxt.text
        assert nxt.json()["total"] == total
        rows.extend(nxt.json()["items"])
    assert len(rows) == total
    assert len({row["row_key"] for row in rows}) == total
    return rows


def test_summary_requires_admin_and_failed_read_is_not_zero(admin_client: TestClient, monkeypatch) -> None:
    anonymous = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert anonymous.status_code == 401
    listed = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:ready"})
    assert listed.status_code == 401
    login(admin_client)

    def explode(*_args, **_kwargs):
        raise RuntimeError("leitura indisponivel")

    monkeypatch.setattr("app.domain.order_board.managerial_board", explode)
    with pytest.raises(RuntimeError, match="leitura indisponivel"):
        admin_client.get("/api/v1/admin/ops/attendance-summary")


def test_board_reconciles_filters_and_does_not_mutate(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    today = bakery_today(get_settings())
    yesterday = today - timedelta(days=1)
    ahead = today + timedelta(days=10)
    open_date = _date(db, desired_date=yesterday, status="pending", intended_quantity=3)
    _date(db, desired_date=ahead, status="alternative_proposed")
    converted = _date(db, desired_date=ahead, status="pending")
    _date(db, desired_date=ahead, status="closed")
    heavy = _order(
        db,
        catalog,
        status="submitted",
        total_cents=800,
        loaves=8,
        production_local_date=ahead,
        notices=((0, "order_submitted", "pending"),),
    )
    heavy.created_at = datetime.now(UTC) - timedelta(days=3)
    confirmed = _order(
        db,
        catalog,
        status="confirmed",
        total_cents=1000,
        fulfillment_modality="pickup",
        pay={"status": "paid", "paid": 1000},
        notices=((0, "order_accepted", "failed"), (5, "order_accepted", "sent")),
    )
    confirmed.created_at = datetime.now(UTC) - timedelta(days=40)
    linked = _order(
        db,
        catalog,
        status="confirmed",
        total_cents=1200,
        source_date_request_id=converted.id,
        pay={"status": "pending", "external": "ref-ficticia"},
        notices=((0, "order_accepted", "failed"), (5, "order_accepted", "sent")),
    )
    converted.status = "converted"
    converted.converted_order_id = linked.id
    address = _order(
        db,
        catalog,
        status="in_production",
        total_cents=900,
        fulfillment_modality="delivery",
        customer_phone=None,
        pay={"status": "pending"},
        notices=((0, "order_accepted", "skipped"),),
    )
    _order(
        db,
        catalog,
        status="ready",
        total_cents=0,
        order_kind="redemption",
        fulfillment_modality="pickup",
        customer_phone=None,
    )
    done = _order(
        db,
        catalog,
        status="completed",
        total_cents=2000,
        customer_name="Historico Fornada Final",
        production_local_date=yesterday,
        pay={"status": "paid", "paid": 2000},
        notices=((0, "order_submitted_admin", "failed"), (1, "order_accepted", "sent")),
    )
    _order(
        db,
        catalog,
        status="completed",
        total_cents=1500,
        pay={"status": "paid", "paid": 1500},
    )
    cancelled = _order(
        db,
        catalog,
        status="cancelled",
        total_cents=800,
        customer_name="Historico Fornada Cancelado",
    )
    failed_pay = _order(
        db,
        catalog,
        status="confirmed",
        total_cents=500,
        pay={"status": "failed"},
        notices=((0, "payment_approved", "failed"), (4, "payment_approved", "failed")),
    )
    _order(
        db,
        catalog,
        status="confirmed",
        total_cents=700,
        pay={"status": "refunded", "paid": 700, "refunded": 700},
    )
    _order(
        db,
        catalog,
        status="in_production",
        total_cents=1000,
        pay={"status": "partially_refunded", "paid": 1000, "refunded": 400},
    )
    _order(
        db,
        catalog,
        status="ready",
        total_cents=400,
        pay={"status": "unknown"},
    )
    _order(
        db,
        catalog,
        status="submitted",
        total_cents=300,
        pay={"status": "cancelled"},
    )
    overdue_order = _order(
        db,
        catalog,
        status="confirmed",
        total_cents=600,
        fulfillment_modality="delivery",
        customer_phone=None,
        production_local_date=yesterday,
        adapt=2,
        **NEW_ORDER_ADDRESS,
    )
    _order(db, catalog, status="draft", total_cents=100)
    db.add(
        EmailOutbox(
            date_request_id=open_date.id,
            kind="date_request_received",
            to_address="cliente@example.test",
            subject="aviso",
            body="texto ficticio",
            status="pending",
            dedupe_key=f"p101-{uuid4().hex}",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    before = _counts(db)
    confirmed_status = confirmed.status

    login(admin_client)
    summary = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "@example.test" not in summary.text
    board = body["board"]
    assert board["timezone"] == "America/Sao_Paulo"
    assert board["updated_label"][2] == "/"
    assert "sem filtro de data de criação" in board["scope"]
    assert "fornada" in board["scope"]
    assert board["not_tracked"] == []
    assert "foram convertidos" in board["legacy_note"]

    stages = {item["lens"]: item["count"] for item in board["stages"]}
    assert stages == {
        "stage:open": 4,
        "stage:accepted": 4,
        "stage:paid": 1,
        "stage:in_production": 2,
    }
    assert board["operational_total"] == 13
    assert body["unique_records"] == board["operational_total"]
    assert sum(item["count"] for item in board["stages"]) + sum(
        item["count"] for item in board["exceptions"]
    ) == board["operational_total"]
    assert _metric(board, "exceptions", "stage:ready_legacy") == 2
    assert _metric(board, "history", "stage:delivered") == 0
    assert _metric(board, "history", "stage:finalized") == 2
    assert _metric(board, "history", "stage:cancelled") == 1
    assert _metric(board, "history", "stage:rejected") == 1
    assert sum(item["count"] for item in board["history"]) == 4
    assert "total_geral" not in board
    payment_sum = sum(item["count"] for item in board["payments"] + board["payment_other"])
    assert payment_sum == board["payment_orders"] == 14
    assert payment_sum != board["operational_total"]
    assert _metric(board, "payments", "payment:awaiting") == 1
    assert _metric(board, "payments", "payment:processing") == 1
    assert _metric(board, "payments", "payment:paid") == 3
    assert _metric(board, "payments", "payment:failed") == 1
    assert _metric(board, "payment_other", "payment:no_charge") == 2
    assert _metric(board, "payment_other", "payment:no_amount") == 1
    assert _metric(board, "payment_other", "payment:refunded") == 1
    assert _metric(board, "payment_other", "payment:partial_refund") == 1
    assert _metric(board, "payment_other", "payment:unknown") == 1
    assert _metric(board, "payment_other", "payment:charge_cancelled") == 1
    assert _metric(board, "payment_other", "payment:cancelled_open") == 1
    assert _metric(board, "pendings", "pending:address") == 1
    assert _metric(board, "pendings", "pending:notice_pending") == 2
    assert _metric(board, "pendings", "pending:notice_failed") == 1
    assert _metric(board, "pendings", "pending:notice_skipped") == 1
    assert _metric(board, "pendings", "pending:overdue") == 2
    assert _metric(board, "pendings", "pending:adaptation") == 1

    lenses = [
        item["lens"]
        for group in ("stages", "exceptions", "history", "payments", "payment_other", "pendings")
        for item in board[group]
    ]
    collected = {lens: _collect(admin_client, lens) for lens in lenses}
    for group in ("stages", "exceptions", "history", "payments", "payment_other", "pendings"):
        for item in board[group]:
            assert len(collected[item["lens"]]) == item["count"]

    evaluation = collected["stage:open"]
    heavy_row = next(row for row in evaluation if row["public_reference"] == heavy.public_reference)
    assert heavy_row["bread_units"] == 8
    assert heavy_row["visible_label"] == "Aberto"
    assert len(evaluation) != 8
    assert f"date_request:{converted.id}" not in {row["row_key"] for row in evaluation}
    assert f"order:{linked.id}" not in {row["row_key"] for row in evaluation}
    assert any(row["row_key"] == f"order:{linked.id}" for row in collected["stage:accepted"])
    assert collected["stage:paid"][0]["public_reference"] == confirmed.public_reference
    assert collected["stage:paid"][0]["visible_label"] == "Pago"
    assert all(row["visible_label"] == "Finalizado" for row in collected["stage:finalized"])
    assert all(
        row["visible_label"] == "Pronto — aguardando confirmação de entrega"
        for row in collected["stage:ready_legacy"]
    )
    assert any(row["source"] == "date_request" for row in evaluation)

    address_rows = collected["pending:address"]
    assert [row["public_reference"] for row in address_rows] == [address.public_reference]
    assert address_rows[0]["delivery_pending"] is True
    assert address_rows[0]["status"] == "in_production"
    assert any(row["public_reference"] == address.public_reference for row in collected["stage:in_production"])
    assert overdue_order.public_reference not in {row["public_reference"] for row in address_rows}

    failed_notices = {row["public_reference"] for row in collected["pending:notice_failed"]}
    assert failed_notices == {failed_pay.public_reference}
    assert confirmed.public_reference not in failed_notices
    assert done.public_reference not in failed_notices
    assert len(collected["pending:notice_failed"]) == 1

    overdue_keys = {row["row_key"] for row in collected["pending:overdue"]}
    assert f"date_request:{open_date.id}" in overdue_keys
    assert f"order:{overdue_order.id}" in overdue_keys
    assert f"order:{heavy.id}" not in overdue_keys
    assert f"order:{done.id}" not in overdue_keys

    second = evaluation[1]
    if second["source"] == "date_request":
        detail = admin_client.get(f"/api/v1/admin/date-requests/{second['id']}")
    else:
        detail = admin_client.get(f"/api/v1/admin/orders/{second['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == second["id"]

    history = admin_client.get("/api/v1/admin/orders", params={"reference": "Historico Fornada"})
    assert history.status_code == 200, history.text
    found = {item["public_reference"] for item in history.json()["items"]}
    assert done.public_reference in found
    assert cancelled.public_reference in found
    assert history.json()["search_scope"] == "histórico completo"
    queue = admin_client.get("/api/v1/admin/orders")
    queued = {item["public_reference"] for item in queue.json()["items"]}
    assert done.public_reference not in queued
    assert cancelled.public_reference not in queued
    ready_refs = {row["public_reference"] for row in collected["stage:ready_legacy"]}
    assert ready_refs <= queued
    assert ready_refs.isdisjoint(
        {row["public_reference"] for row in collected["stage:delivered"]}
    )
    assert queue.json()["total"] == board["operational_total"]

    created = admin_client.get(
        "/api/v1/admin/orders",
        params={"status": "confirmed", "created_from": today.isoformat()},
    )
    assert created.status_code == 200, created.text
    assert created.json()["orders_error"] is None
    created_refs = {item["public_reference"] for item in created.json()["items"]}
    assert created.json()["total"] == 4
    assert confirmed.public_reference not in created_refs
    assert linked.public_reference in created_refs
    still = admin_client.get(f"/api/v1/admin/orders/{confirmed.id}")
    assert still.status_code == 200

    again = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert again.status_code == 200
    assert _counts(db) == before
    db.refresh(confirmed)
    assert confirmed.status == confirmed_status == "confirmed"
