"""Adendo 101B: etapas derivadas, entrega explícita e produção sem pagamento. Dados fictícios."""

from datetime import timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import draft_order, priced_catalog
from tests.test_prompt100 import _request, _variant

assert admin_client


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def _counts(db: Session) -> tuple[int, int, int]:
    db.expire_all()
    return (
        int(db.scalar(select(func.count()).select_from(Order)) or 0),
        int(db.scalar(select(func.count()).select_from(EmailOutbox)) or 0),
        int(db.scalar(select(func.count()).select_from(PaymentRecord)) or 0),
    )


def _history(db: Session, order_id) -> list[OrderStatusHistory]:
    db.expire_all()
    return list(
        db.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc())
        )
    )


def _confirm(client: TestClient, csrf: str, order: Order) -> dict:
    response = client.post(
        f"/api/v1/admin/orders/{order.id}/confirm", headers=_headers(csrf)
    )
    assert response.status_code == 200, response.text
    return response.json()


def _pay(db: Session, order: Order, status: str, *, paid: int | None = None, external: str | None = None) -> None:
    db.add(
        PaymentRecord(
            order_id=order.id,
            provider="actionhub",
            external_reference=external,
            idempotency_key=f"p101b-{uuid4().hex}",
            expected_cents=order.total_cents or 0,
            currency="BRL",
            financial_status=status,
            amount_paid_cents=paid,
        )
    )
    db.commit()


def _start(client: TestClient, csrf: str, order: Order, *, exception: bool | None = None):
    kwargs = {"headers": _headers(csrf)}
    if exception is not None:
        kwargs["json"] = {"unpaid_exception": exception}
    return client.post(f"/api/v1/admin/orders/{order.id}/start-production", **kwargs)


def _board(client: TestClient) -> dict:
    response = client.get("/api/v1/admin/ops/attendance-summary")
    assert response.status_code == 200, response.text
    return response.json()["board"]


def _stage(board: dict, lens: str) -> int:
    found = [
        item
        for item in board["stages"] + board.get("exceptions", []) + board["history"]
        if item["lens"] == lens
    ]
    assert len(found) == 1
    return found[0]["count"]


def test_accept_without_address_becomes_one_accepted_order(
    admin_client: TestClient, db: Session
) -> None:
    variant = _variant(db, "Pao Sem Endereco")
    db.commit()
    csrf = login(admin_client)
    desired = (bakery_today(get_settings()) + timedelta(days=3)).isoformat()
    created = _request(
        admin_client,
        f"p101b-{uuid4().hex[:8]}",
        desired,
        message="Pao Sem Endereco para a encomenda",
    )
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created['id']}",
        headers=_headers(csrf),
        json={"action": "accept", "lines": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert accepted.status_code == 200, accepted.text
    detail = admin_client.get(f"/api/v1/admin/orders/{accepted.json()['converted_order_id']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "confirmed"
    assert body["visible_stage"] == "accepted"
    assert body["visible_label"] == "Aceito"
    assert body["address"]["street"] is None
    assert body["delivery_pending"] is True
    assert body["total"]["cents"] == 2490
    assert body["financially_settled"] is False
    board = _board(admin_client)
    assert _stage(board, "stage:accepted") == 1
    assert _stage(board, "stage:open") == 0
    assert _stage(board, "stage:paid") == 0


def test_paid_order_waits_for_explicit_production(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    order.customer_name = "Pago Aguardando"
    db.commit()
    csrf = login(admin_client)
    confirmed = _confirm(admin_client, csrf, order)
    assert confirmed["visible_label"] == "Aceito"
    db.expire_all()
    order = db.get(Order, order.id)
    _pay(db, order, "paid", paid=order.total_cents)
    waiting = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert waiting.json()["visible_stage"] == "paid"
    assert waiting.json()["visible_label"] == "Pago"
    assert waiting.json()["status"] == "confirmed"
    before = _counts(db)
    started = _start(admin_client, csrf, order)
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "in_production"
    assert body["visible_label"] == "Em produção"
    assert body["payment_attention"] is None
    assert body["payment_records"][0]["financial_status"] == "paid"
    reasons = [row.reason for row in _history(db, order.id) if row.to_status == "in_production"]
    assert reasons == [None]
    assert _counts(db) == before
    board = _board(admin_client)
    assert _stage(board, "stage:paid") == 0
    assert _stage(board, "stage:in_production") == 1
    listed = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:in_production"})
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["visible_label"] == "Em produção"
    queue = admin_client.get("/api/v1/admin/orders")
    assert queue.json()["total"] == board["operational_total"] == 1


def test_unpaid_production_needs_an_explicit_exception(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    order.customer_name = "Ainda Nao Pago"
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    _pay(db, order, "pending")
    before = _counts(db)
    direct = _start(admin_client, csrf, order)
    explicit_false = _start(admin_client, csrf, order, exception=False)
    for response in (direct, explicit_false):
        assert response.status_code == 409, response.text
        payload = response.json()
        assert payload["code"] == "unpaid_production"
        assert payload["detail"] == "Este pedido ainda não está pago."
        assert payload["public_reference"] == order.public_reference
        assert payload["total_cents"] == order.total_cents
        assert payload["financial_label"] == "Aguardando pagamento"
        assert payload["uncertain"] is False
        assert "fict" not in response.text
        assert "@" not in response.text
    db.expire_all()
    assert db.get(Order, order.id).status == "confirmed"
    assert _counts(db) == before
    started = _start(admin_client, csrf, order, exception=True)
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["visible_label"] == "Em produção"
    assert body["payment_attention"] == "Pagamento pendente"
    assert body["payment_records"][0]["financial_status"] == "pending"
    assert body["financially_settled"] is False
    again = _start(admin_client, csrf, order, exception=True)
    assert again.status_code == 200, again.text
    production = [row for row in _history(db, order.id) if row.to_status == "in_production"]
    assert len(production) == 1
    assert production[0].actor_ref.startswith("admin:")
    assert production[0].created_at is not None
    assert "sem quitação confirmada" in production[0].reason
    assert "Aguardando pagamento" in production[0].reason
    assert _counts(db) == before


def test_payment_confirmed_before_the_exception_is_a_normal_start(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    _pay(db, order, "pending")
    blocked = _start(admin_client, csrf, order)
    assert blocked.status_code == 409
    record = db.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)).one()
    record.financial_status = "paid"
    record.amount_paid_cents = order.total_cents
    db.commit()
    started = _start(admin_client, csrf, order, exception=True)
    assert started.status_code == 200, started.text
    assert started.json()["visible_label"] == "Em produção"
    assert started.json()["payment_attention"] is None
    reasons = [row.reason for row in _history(db, order.id) if row.to_status == "in_production"]
    assert reasons == [None]


def test_later_payment_keeps_production(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    _pay(db, order, "pending")
    started = _start(admin_client, csrf, order, exception=True)
    assert started.status_code == 200, started.text
    record = db.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)).one()
    record.financial_status = "paid"
    record.amount_paid_cents = order.total_cents
    db.commit()
    detail = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert detail.json()["status"] == "in_production"
    assert detail.json()["visible_label"] == "Em produção"
    assert detail.json()["delivery_confirmed_at"] is None
    board = _board(admin_client)
    assert _stage(board, "stage:in_production") == 1
    assert _stage(board, "stage:paid") == 0
    assert _stage(board, "stage:delivered") == 0
    paid = admin_client.get("/api/v1/admin/orders", params={"lens": "payment:paid"})
    assert paid.json()["total"] == 1
    assert paid.json()["items"][0]["visible_label"] == "Em produção"


def test_zero_amount_is_not_delinquency(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    order.total_cents = 0
    order.order_kind = "redemption"
    db.commit()
    waiting = admin_client.get(f"/api/v1/admin/orders/{order.id}")
    assert waiting.json()["visible_label"] == "Aceito"
    assert waiting.json()["payment_attention"] is None
    started = _start(admin_client, csrf, order)
    assert started.status_code == 200, started.text
    assert started.json()["visible_label"] == "Em produção"
    assert started.json()["payment_attention"] is None
    reasons = [row.reason for row in _history(db, order.id) if row.to_status == "in_production"]
    assert reasons == [None]
    board = _board(admin_client)
    other = {item["lens"]: item["count"] for item in board["payment_other"]}
    assert other["payment:no_amount"] == 1
    assert _stage(board, "stage:paid") == 0


def test_unknown_finance_is_not_treated_as_paid(admin_client: TestClient, db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    order.total_cents = None
    db.commit()
    blocked = _start(admin_client, csrf, order)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["uncertain"] is True
    assert blocked.json()["total_cents"] is None
    assert blocked.json()["detail"] == "O pagamento deste pedido não pôde ser confirmado."
    db.expire_all()
    assert db.get(Order, order.id).status == "confirmed"
    started = _start(admin_client, csrf, order, exception=True)
    assert started.status_code == 200, started.text
    assert started.json()["visible_label"] == "Em produção"
    assert started.json()["payment_attention"] == "Pagamento não confirmado"
    assert started.json()["payment_records"] == []
    reason = next(row.reason for row in _history(db, order.id) if row.to_status == "in_production")
    assert "desconhecido" in reason


def test_explicit_delivery_and_old_records_keep_their_meaning(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 4
    catalog["slot"].capacity_units = 4
    delivered = draft_order(db, catalog)
    delivered.customer_name = "Entrega Confirmada Ficticia"
    ready = draft_order(db, catalog)
    ready.customer_name = "Pronto Antigo Ficticio"
    finalized = draft_order(db, catalog)
    finalized.customer_name = "Finalizado Antigo Ficticio"
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    for order in (delivered, ready, finalized):
        _confirm(admin_client, csrf, order)
        db.expire_all()
        current = db.get(Order, order.id)
        _pay(db, current, "paid", paid=current.total_cents)
        assert _start(admin_client, csrf, current).status_code == 200

    ready_mark = admin_client.post(f"/api/v1/admin/orders/{ready.id}/mark-ready", headers=headers)
    assert ready_mark.status_code == 200, ready_mark.text
    assert ready_mark.json()["visible_label"] == "Pronto — aguardando confirmação de entrega"
    assert ready_mark.json()["delivery_confirmed_at"] is None

    old = admin_client.post(f"/api/v1/admin/orders/{finalized.id}/mark-ready", headers=headers)
    assert old.status_code == 200, old.text
    completed = admin_client.post(f"/api/v1/admin/orders/{finalized.id}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["visible_label"] == "Finalizado"
    assert completed.json()["delivery_confirmed_at"] is None
    refused = admin_client.post(
        f"/api/v1/admin/orders/{finalized.id}/confirm-delivery", headers=headers
    )
    assert refused.status_code == 409, refused.text
    db.expire_all()
    assert db.get(Order, finalized.id).delivery_confirmed_at is None

    mail_before = _counts(db)[1]
    first = admin_client.post(
        f"/api/v1/admin/orders/{delivered.id}/confirm-delivery", headers=headers
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["status"] == "completed"
    assert body["visible_stage"] == "delivered"
    assert body["visible_label"] == "Entregue"
    assert body["delivery_confirmed_at"]
    stamp = body["delivery_confirmed_at"]
    second = admin_client.post(
        f"/api/v1/admin/orders/{delivered.id}/confirm-delivery", headers=headers
    )
    assert second.status_code == 200, second.text
    assert second.json()["delivery_confirmed_at"] == stamp
    proofs = [
        row for row in _history(db, delivered.id) if row.reason == "entrega confirmada pelo gestor"
    ]
    assert len(proofs) == 1
    assert proofs[0].actor_ref.startswith("admin:")
    assert _counts(db)[1] == mail_before

    board = _board(admin_client)
    assert _stage(board, "stage:delivered") == 1
    assert _stage(board, "stage:finalized") == 1
    assert _stage(board, "stage:ready_legacy") == 1
    assert _stage(board, "stage:in_production") == 0
    assert board["operational_total"] == 1
    queue = admin_client.get("/api/v1/admin/orders")
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["public_reference"] == ready.public_reference
    found = admin_client.get(
        "/api/v1/admin/orders", params={"reference": "Entrega Confirmada Ficticia"}
    )
    assert found.json()["search_scope"] == "histórico completo"
    assert found.json()["items"][0]["visible_label"] == "Entregue"
    old_found = admin_client.get(
        "/api/v1/admin/orders", params={"reference": "Finalizado Antigo Ficticio"}
    )
    assert old_found.json()["items"][0]["visible_label"] == "Finalizado"
    ready_found = admin_client.get(
        "/api/v1/admin/orders", params={"reference": "Pronto Antigo Ficticio"}
    )
    assert ready_found.json()["items"][0]["visible_label"] == "Pronto — aguardando confirmação de entrega"


def test_rejection_and_cancellation_keep_distinct_reasons(
    admin_client: TestClient, db: Session
) -> None:
    today = bakery_today(get_settings())
    request = DateRequest(
        desired_date=today + timedelta(days=4),
        customer_name="Solicitacao Recusada",
        customer_email="recusada@example.test",
        intended_quantity=1,
        status="pending",
        idempotency_key=f"p101b-{uuid4().hex}",
        client_host="test",
    )
    db.add(request)
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    headers = _headers(csrf)
    closed = admin_client.post(
        f"/api/v1/admin/date-requests/{request.id}",
        headers=headers,
        json={"action": "close", "note": "não vamos produzir esta encomenda"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    _confirm(admin_client, csrf, order)
    cancelled = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel",
        headers=headers,
        json={"reason": "cliente desistiu da data"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["visible_label"] == "Cancelado"
    assert cancelled.json()["cancellation_reason"] == "cliente desistiu da data"
    board = _board(admin_client)
    assert _stage(board, "stage:rejected") == 1
    assert _stage(board, "stage:cancelled") == 1
    assert board["operational_total"] == 0
    rejected = admin_client.get("/api/v1/admin/orders", params={"lens": "stage:rejected"})
    assert rejected.json()["items"][0]["visible_label"] == "Rejeitado"
    db.expire_all()
    notice = db.scalars(
        select(EmailOutbox).where(EmailOutbox.date_request_id == request.id)
    ).one()
    assert notice.kind == "date_request_declined"
    assert notice.status != "sent"
    assert db.get(DateRequest, request.id).admin_note == "não vamos produzir esta encomenda"


def test_pronto_keeps_the_address_marker_and_is_not_delivered(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    db.expire_all()
    order = db.get(Order, order.id)
    order.fulfillment_modality = "delivery"
    order.delivery_street = None
    db.commit()
    _pay(db, order, "paid", paid=order.total_cents)
    headers = _headers(csrf)
    assert _start(admin_client, csrf, order).status_code == 200
    ready = admin_client.post(f"/api/v1/admin/orders/{order.id}/mark-ready", headers=headers)
    assert ready.status_code == 200, ready.text
    assert ready.json()["visible_label"] == "Pronto — aguardando confirmação de entrega"
    assert ready.json()["delivery_pending"] is True
    assert ready.json()["delivery_confirmed_at"] is None
    board = _board(admin_client)
    assert _stage(board, "stage:ready_legacy") == 1
    assert _stage(board, "stage:delivered") == 0
    assert board["operational_total"] == 1
    assert sum(item["count"] for item in board["stages"]) + _stage(board, "stage:ready_legacy") == 1
    address = admin_client.get("/api/v1/admin/orders", params={"lens": "pending:address"})
    assert address.json()["total"] == 1
    assert address.json()["items"][0]["visible_label"] == "Pronto — aguardando confirmação de entrega"


def test_reads_do_not_mutate_and_actions_require_admin(
    admin_client: TestClient, db: Session
) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    db.commit()
    anonymous_summary = admin_client.get("/api/v1/admin/ops/attendance-summary")
    anonymous_start = admin_client.post(f"/api/v1/admin/orders/{order.id}/start-production")
    anonymous_delivery = admin_client.post(f"/api/v1/admin/orders/{order.id}/confirm-delivery")
    assert anonymous_summary.status_code == 401
    assert anonymous_start.status_code == 401
    assert anonymous_delivery.status_code == 401
    csrf = login(admin_client)
    _confirm(admin_client, csrf, order)
    before = _counts(db)
    stamps = list(db.scalars(select(Order.delivery_confirmed_at)))
    first = _board(admin_client)
    second = _board(admin_client)
    assert first["operational_total"] == second["operational_total"]
    assert _counts(db) == before
    assert list(db.scalars(select(Order.delivery_confirmed_at))) == stamps
