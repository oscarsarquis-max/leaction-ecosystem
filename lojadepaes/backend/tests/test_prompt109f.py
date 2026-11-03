"""109F: solicitação de data que um pedido do mesmo cliente já atende. Dados fictícios."""

from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.managerial_exclusion import exclude_subject
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.contract.support import send_confirmed, variant
from tests.test_prompt109c import _confirm, _headers

assert admin_client


def _paid_order(client: TestClient, db: Session, key: str, bread=None) -> Order:
    order = _confirm(client, db, send_confirmed(db, key, bread))
    db.add(
        PaymentRecord(
            order_id=order.id,
            expected_cents=order.total_cents or 0,
            amount_paid_cents=order.total_cents or 0,
            currency="BRL",
            financial_status="paid",
            idempotency_key=str(uuid4()),
        )
    )
    db.commit()
    return order


def _request_for(db: Session, order: Order, *, desired=None, email: str | None = None) -> DateRequest:
    item = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).first()
    assert item is not None and item.product_variant_id is not None
    request = DateRequest(
        desired_date=desired or order.production_local_date,
        customer_name=order.customer_name,
        customer_email=email or order.customer_email,
        intended_quantity=item.quantity,
        status="pending",
        cart_context=[{"variant_id": str(item.product_variant_id), "quantity": item.quantity}],
        idempotency_key=f"109f-{uuid4().hex}",
        client_host="127.0.0.1",
    )
    db.add(request)
    db.commit()
    return request


def _act(client: TestClient, request: DateRequest, order: Order):
    return client.post(
        f"/api/v1/admin/date-requests/{request.id}",
        headers=_headers(client),
        json={"action": "close_as_fulfilled", "order_id": str(order.id)},
    )


def _fila(client: TestClient, request: DateRequest) -> dict:
    listed = client.get("/api/v1/admin/orders", params={"page_size": 50})
    assert listed.status_code == 200, listed.text
    rows = [row for row in listed.json()["items"] if row["row_key"] == f"date_request:{request.id}"]
    assert len(rows) == 1, listed.text
    return rows[0]


def test_close_as_fulfilled_links_order_and_changes_nothing_else(
    admin_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _paid_order(admin_client, db, "109f-ok", variant(db, "Pão 109F", 7000))
    request = _request_for(db, order)
    orders_before = db.query(Order).count()
    outbox_before = db.query(EmailOutbox).count()
    snapshot = (order.status, order.production_local_date, order.requested_date, order.total_cents, order.holds_capacity)

    import app.domain.crm_tracking as crm

    def no_fact(*_a, **_k):
        raise AssertionError("fato de CRM não pode sair ao encerrar como atendida")

    monkeypatch.setattr(crm, "emit_order_fact", no_fact)
    done = _act(admin_client, request, order)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["status"] == "converted"
    assert body["converted_order_id"] == str(order.id)
    assert body["allowed_actions"] == []

    db.expire_all()
    stored = db.get(DateRequest, request.id)
    assert stored.status == "converted" and stored.converted_order_id == order.id
    assert stored.closed_at is not None
    events = list(db.scalars(select(DateRequestEvent).where(DateRequestEvent.request_id == request.id)))
    closing = [row for row in events if row.action == "fulfilled"]
    assert len(closing) == 1
    assert closing[0].detail == f"atendida pelo pedido {order.public_reference}"
    assert closing[0].actor_ref
    assert db.query(Order).count() == orders_before
    assert db.query(EmailOutbox).count() == outbox_before
    after = db.get(Order, order.id)
    assert (after.status, after.production_local_date, after.requested_date, after.total_cents, after.holds_capacity) == snapshot

    again = _act(admin_client, request, order)
    assert again.status_code == 422
    assert "já foi encerrada" in again.json()["detail"]


def test_close_as_fulfilled_refuses_other_customer_cancelled_and_voided(
    admin_client: TestClient, db: Session
) -> None:
    bread = variant(db, "Pão 109F recusa", 7000)
    mine = _paid_order(admin_client, db, "109f-mine", bread)
    request = _request_for(db, mine)

    other = _paid_order(admin_client, db, "109f-other", variant(db, "Pão outro 109F", 3000))
    other.customer_email = "outra-pessoa@example.test"
    other.customer_name = "Outra Pessoa"
    db.commit()
    refused = _act(admin_client, request, other)
    assert refused.status_code == 409, refused.text
    assert "não é uma encomenda existente deste cliente" in refused.json()["detail"]

    cancelled = _paid_order(admin_client, db, "109f-cancelled", bread)
    cancelled.customer_email = mine.customer_email
    cancelled.customer_name = mine.customer_name
    cancelled.status = "cancelled"
    db.commit()
    refused = _act(admin_client, request, cancelled)
    assert refused.status_code == 409, refused.text
    assert "cancelado" in refused.json()["detail"]

    voided = _paid_order(admin_client, db, "109f-voided", bread)
    voided.customer_email = mine.customer_email
    voided.customer_name = mine.customer_name
    exclude_subject(
        db,
        "order",
        voided.id,
        author_ref="test",
        kind="duplicate",
        original_order_id=mine.id,
        reason="duplicado de teste",
    )
    db.commit()
    refused = _act(admin_client, request, voided)
    assert refused.status_code == 409, refused.text
    assert "anulado" in refused.json()["detail"]

    db.expire_all()
    assert db.get(DateRequest, request.id).status == "pending"
    assert db.get(DateRequest, request.id).converted_order_id is None


def test_case_sdb6ba3cd_queue_shows_it_and_closing_removes_it_from_vigentes(
    admin_client: TestClient, db: Session
) -> None:
    order = _paid_order(admin_client, db, "109f-case", variant(db, "Rolled Bread 109F", 7000))
    request = _request_for(db, order)
    different = _request_for(db, order, desired=order.production_local_date + timedelta(days=7))

    row = _fila(admin_client, request)
    assert row["attention"] == f"Já há o pedido {order.public_reference} para esta data"
    assert row["next_action"] == {"code": "close_fulfilled", "label": "Encerrar solicitação", "primary": True}
    other_row = _fila(admin_client, different)
    shown = order.production_local_date.strftime("%d/%m")
    assert other_row["attention"] == f"Cliente tem o pedido {order.public_reference} para {shown}"
    assert other_row["next_action"]["code"] == "respond_date_request"
    assert other_row["next_action"]["label"] == "Avaliar e responder"

    summary = admin_client.get("/api/v1/admin/ops/attendance-summary").json()
    vigentes_before = {lens["key"]: lens["count"] for lens in summary["queue_lenses"]}["stage:open"]
    paid_snapshot = (order.status, order.production_local_date, order.total_cents)

    assert _act(admin_client, request, order).status_code == 200
    db.expire_all()
    after = db.get(Order, order.id)
    assert (after.status, after.production_local_date, after.total_cents) == paid_snapshot

    summary = admin_client.get("/api/v1/admin/ops/attendance-summary").json()
    vigentes_after = {lens["key"]: lens["count"] for lens in summary["queue_lenses"]}["stage:open"]
    assert vigentes_after == vigentes_before - 1
    listed = admin_client.get("/api/v1/admin/orders", params={"page_size": 50}).json()
    assert all(item["row_key"] != f"date_request:{request.id}" for item in listed["items"])


def test_queue_ignores_other_customer_cancelled_and_voided(admin_client: TestClient, db: Session) -> None:
    bread = variant(db, "Pão 109F fila", 7000)
    base = _paid_order(admin_client, db, "109f-q-base", bread)
    request = _request_for(db, base)
    assert _fila(admin_client, request)["attention"]

    base.status = "cancelled"
    db.commit()
    row = _fila(admin_client, request)
    assert row["attention"] is None
    assert row["next_action"]["code"] == "respond_date_request"

    base.status = "confirmed"
    db.commit()
    assert _fila(admin_client, request)["next_action"]["code"] == "close_fulfilled"
    exclude_subject(
        db, "order", base.id, author_ref="test", kind="duplicate", original_order_id=None, reason="duplicado de teste"
    )
    db.commit()
    row = _fila(admin_client, request)
    assert row["attention"] is None
    assert row["next_action"]["code"] == "respond_date_request"


def test_queue_loads_candidates_in_batch(admin_client: TestClient, db: Session) -> None:
    from app.db.session import get_engine

    order = _paid_order(admin_client, db, "109f-batch", variant(db, "Pão 109F lote", 7000))
    _request_for(db, order)
    login(admin_client)
    engine = get_engine()
    box = {"n": 0}

    def bump(*_args, **_kwargs):
        box["n"] += 1

    event.listen(engine, "before_cursor_execute", bump)
    try:
        box["n"] = 0
        assert admin_client.get("/api/v1/admin/orders", params={"page_size": 50}).status_code == 200
        few = box["n"]
        for _ in range(15):
            _request_for(db, order, desired=order.production_local_date + timedelta(days=1))
        box["n"] = 0
        assert admin_client.get("/api/v1/admin/orders", params={"page_size": 50}).status_code == 200
        many = box["n"]
    finally:
        event.remove(engine, "before_cursor_execute", bump)
    assert many <= few + 3, (few, many)
    assert get_settings() is not None


def test_detail_box_exposes_flags_for_the_button(admin_client: TestClient, db: Session) -> None:
    order = _paid_order(admin_client, db, "109f-box", variant(db, "Pão 109F caixa", 7000))
    request = _request_for(db, order)
    detail = admin_client.get(f"/api/v1/admin/date-requests/{request.id}", headers=_headers(admin_client))
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert "close_as_fulfilled" in body["allowed_actions"]
    match = next(row for row in body["accept_preview"]["existing_orders"] if row["id"] == str(order.id))
    assert match["production_local_date"] == order.production_local_date.isoformat()
    assert match["can_close_as_fulfilled"] is True and match["voided"] is False
