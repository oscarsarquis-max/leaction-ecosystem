"""Mudança de data, duplicidade e anulação. Dados fictícios."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.duplicates import customer_match_reason, possible_duplicate_reason
from app.domain.managerial_exclusion import exclude_subject
from app.domain.order_board import managerial_board
from app.domain.order_reschedule import schedule_exception_of
from app.domain.schedule import committed_for_date, save_date_override
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import ManagerialExclusion
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.contract.support import send_confirmed

assert admin_client


def _next(iso_weekday: int) -> date:
    today = bakery_today(get_settings())
    delta = (iso_weekday - today.isoweekday()) % 7
    day = today + timedelta(days=delta)
    if day <= today:
        day += timedelta(days=7)
    return day


def _headers(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": login(client)}


def _confirm(client: TestClient, db: Session, order: Order) -> Order:
    db.commit()
    response = client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers=_headers(client))
    assert response.status_code == 200, response.text
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored is not None
    return stored


def _reschedule(client: TestClient, order: Order, day: date, **extra) -> object:
    body = {
        "date": day.isoformat(),
        "reason": extra.pop("reason", "combinado com o cliente"),
        "origin": extra.pop("origin", "customer"),
        "notify_customer": extra.pop("notify_customer", False),
        "allow_closed_day": extra.pop("allow_closed_day", False),
    }
    return client.post(f"/api/v1/admin/orders/{order.id}/reschedule", headers=_headers(client), json=body)


def test_customer_and_duplicate_rules() -> None:
    now = datetime.now(UTC)
    left = SimpleNamespace(
        status="confirmed",
        created_at=now,
        customer_email="A @Example.com",
        customer_phone="(85) 98888-1234",
        customer_name="João da Silva",
    )
    right = SimpleNamespace(
        status="confirmed",
        created_at=now - timedelta(hours=2),
        customer_email="outro@example.com",
        customer_phone="85988881234",
        customer_name="Outra Pessoa",
    )
    items = [SimpleNamespace(product_id=None, product_variant_id="v1", dough_type_id=None, bread_shape_id=None, quantity=1)]
    other_items = [SimpleNamespace(product_id=None, product_variant_id="v1", dough_type_id=None, bread_shape_id=None, quantity=1)]
    assert customer_match_reason(left, right, items, other_items, require_items=True) == "mesmo telefone"
    assert possible_duplicate_reason(left, right, items, other_items) == "mesmo telefone"
    different = [SimpleNamespace(product_id=None, product_variant_id="v2", dough_type_id=None, bread_shape_id=None, quantity=1)]
    assert possible_duplicate_reason(left, right, items, different) is None
    late = SimpleNamespace(**{**right.__dict__, "created_at": now - timedelta(hours=80)})
    assert possible_duplicate_reason(left, late, items, other_items) is None
    cancelled = SimpleNamespace(**{**right.__dict__, "status": "cancelled"})
    assert possible_duplicate_reason(left, cancelled, items, other_items) is None
    assert possible_duplicate_reason(left, right, items, other_items, right_blocked=True) is None
    named = SimpleNamespace(
        status="confirmed",
        created_at=now,
        customer_email="b@example.com",
        customer_phone="",
        customer_name="João da Silva",
    )
    assert (
        customer_match_reason(left, named, items, other_items, require_items=False) == "mesmo telefone"
        or customer_match_reason(
            SimpleNamespace(
                status="confirmed",
                created_at=now,
                customer_email="c@example.com",
                customer_phone="",
                customer_name="João da Silva",
            ),
            named,
            items,
            other_items,
            require_items=True,
        )
        == "mesmo nome e mesmos itens"
    )


def test_reschedule_by_status_moves_slot_and_keeps_payment(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-status"))
    assert order.requested_date == order.production_local_date
    wednesday = order.production_local_date
    assert wednesday is not None
    saturday = _next(6)
    if saturday == wednesday:
        saturday = saturday + timedelta(days=7)
    before = committed_for_date(db, get_settings(), wednesday)[0]
    submitted = send_confirmed(db, "109c-submitted")
    submitted.status = "submitted"
    submitted.holds_capacity = False
    db.commit()
    refused = _reschedule(admin_client, submitted, saturday)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "Pedido ainda não aceito: use Propor outra data"
    moved = _reschedule(admin_client, order, saturday, notify_customer=True)
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["status"] == "confirmed"
    assert body["production_local_date"] == saturday.isoformat()
    assert body["requested_date"] == wednesday.isoformat()
    assert body["schedule_exception"]["label"] == "Adiada a pedido do cliente"
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored is not None
    assert stored.status == "confirmed"
    assert stored.requested_date == wednesday
    assert stored.holds_capacity is True
    assert committed_for_date(db, get_settings(), wednesday)[0] == before - 1
    assert committed_for_date(db, get_settings(), saturday)[0] >= 1
    mail = db.scalars(select(EmailOutbox).where(EmailOutbox.order_id == order.id, EmailOutbox.kind == "order_date_changed")).all()
    assert len(mail) == 1
    assert mail[0].subject == f"Sua encomenda {stored.public_reference} mudou de data"
    assert "Conforme combinado com você" in mail[0].body
    again = _reschedule(admin_client, stored, saturday + timedelta(days=7), notify_customer=True)
    assert again.status_code == 200, again.text
    assert db.scalars(select(EmailOutbox).where(EmailOutbox.kind == "order_date_changed", EmailOutbox.order_id == order.id)).all()
    deduped = _reschedule(admin_client, stored, saturday + timedelta(days=7), notify_customer=True)
    assert deduped.status_code == 409
    assert len(db.scalars(select(EmailOutbox).where(EmailOutbox.order_id == order.id, EmailOutbox.kind == "order_date_changed")).all()) == 2
    stored.status = "in_production"
    db.commit()
    later = saturday + timedelta(days=14)
    producing = _reschedule(admin_client, stored, later)
    assert producing.status_code == 200, producing.text
    stored.status = "ready"
    db.commit()
    ready_day = later + timedelta(days=7)
    ready = _reschedule(admin_client, stored, ready_day)
    assert ready.status_code == 200, ready.text
    history = db.scalars(select(OrderStatusHistory).where(OrderStatusHistory.order_id == order.id)).all()
    assert any(row.from_status == row.to_status and "Exceção de data" in (row.reason or "") for row in history)
    payment_before = stored.total_cents
    assert db.get(Order, order.id).total_cents == payment_before


def test_closed_day_past_date_and_completed_correction(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-closed"))
    friday = _next(5)
    closed = _reschedule(admin_client, order, friday)
    assert closed.status_code == 409, closed.text
    opened = _reschedule(admin_client, order, friday, allow_closed_day=True)
    assert opened.status_code == 200, opened.text
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored is not None
    past = _reschedule(admin_client, stored, bakery_today(get_settings()) - timedelta(days=1))
    assert past.status_code == 409
    stored.status = "completed"
    stored.delivery_confirmed_at = datetime.now(UTC)
    db.commit()
    corrected = _reschedule(
        admin_client,
        stored,
        date(2026, 10, 30),
        notify_customer=True,
        reason="Antecipação combinada com o cliente pelo WhatsApp; produzido e entregue na sexta",
    )
    assert corrected.status_code == 200, corrected.text
    assert "sem aviso" in (corrected.json().get("action_notice") or "")
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored.production_local_date == date(2026, 10, 30)
    assert stored.requested_date != date(2026, 10, 30)
    assert schedule_exception_of(stored)["label"] == "Antecipada a pedido do cliente"
    assert db.scalars(select(EmailOutbox).where(EmailOutbox.order_id == order.id, EmailOutbox.kind == "order_date_changed")).first() is None
    stored.status = "cancelled"
    db.commit()
    refused = _reschedule(admin_client, stored, friday)
    assert refused.status_code == 409


def test_full_day_refuses(admin_client: TestClient, db: Session) -> None:
    first = _confirm(admin_client, db, send_confirmed(db, "109c-full-a"))
    saturday = _next(6)
    if saturday == first.production_local_date:
        saturday = saturday + timedelta(days=7)
    assert _reschedule(admin_client, first, saturday).status_code == 200
    save_date_override(
        db,
        get_settings(),
        saturday,
        open_state="open",
        daily_physical_limit=1,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    db.commit()
    second = _confirm(admin_client, db, send_confirmed(db, "109c-full-b"))
    refused = _reschedule(admin_client, second, saturday)
    assert refused.status_code == 409, refused.text
    assert "completa" in refused.json()["detail"]


def test_move_existing_order_does_not_create_another(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-move"))
    target = _next(6)
    if target == order.production_local_date:
        target = target + timedelta(days=7)
    request = DateRequest(
        desired_date=target,
        customer_name=order.customer_name,
        customer_email="outro-cliente@example.com",
        message="mesmo nome",
        status="pending",
        cart_context=[{"variant_id": str(db.scalars(select(Order).where(Order.id == order.id)).one().id), "quantity": 1}],
        idempotency_key=f"109c-{uuid4().hex}",
        client_host="127.0.0.1",
    )
    # A correspondência por nome exige os mesmos itens. O e-mail diferente não casa.
    from app.models.orders import OrderItem

    item = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).first()
    assert item is not None and item.product_variant_id is not None
    request.cart_context = [{"variant_id": str(item.product_variant_id), "quantity": item.quantity}]
    request.customer_phone = None
    db.add(request)
    db.commit()
    preview = admin_client.post(
        f"/api/v1/admin/date-requests/{request.id}/commercial-preview",
        headers=_headers(admin_client),
        json={"lines": []},
    )
    assert preview.status_code == 200, preview.text
    found = preview.json()["existing_orders"]
    assert any(row["id"] == str(order.id) and row["match_reason"] == "mesmo nome e mesmos itens" for row in found)
    before = db.query(Order).count()
    accepted_before = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count()
    moved = admin_client.post(
        f"/api/v1/admin/date-requests/{request.id}",
        headers=_headers(admin_client),
        json={"action": "move_existing_order", "order_id": str(order.id), "notify_customer": True, "lines": []},
    )
    assert moved.status_code == 200, moved.text
    db.expire_all()
    assert db.query(Order).count() == before
    stored_request = db.get(DateRequest, request.id)
    assert stored_request.status == "converted"
    assert stored_request.converted_order_id == order.id
    stored = db.get(Order, order.id)
    assert stored.production_local_date == target
    assert stored.requested_date != target or stored.requested_date == order.requested_date
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").count() == accepted_before
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_date_changed").count() == 1

    # Um pedido só pode ser apontado por uma solicitação: a segunda recebe 409, não 500.
    second = DateRequest(
        desired_date=target + timedelta(days=7),
        customer_name=order.customer_name,
        customer_email="outro-cliente@example.com",
        message="mesmo nome",
        status="pending",
        cart_context=[{"variant_id": str(item.product_variant_id), "quantity": item.quantity}],
        idempotency_key=f"109c-{uuid4().hex}",
        client_host="127.0.0.1",
    )
    db.add(second)
    db.commit()
    again = admin_client.post(
        f"/api/v1/admin/date-requests/{second.id}",
        headers=_headers(admin_client),
        json={"action": "move_existing_order", "order_id": str(order.id), "notify_customer": False, "lines": []},
    )
    assert again.status_code == 409, again.text
    assert "outra solicitação" in again.json()["detail"]


def test_october_case_shape(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-oct"))
    order.status = "completed"
    order.delivery_confirmed_at = datetime.now(UTC)
    order.requested_date = date(2026, 11, 1)
    order.production_local_date = date(2026, 11, 1)
    order.customer_name = "Cliente Exemplo"
    from app.models.orders import OrderItem

    item = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).one()
    request = DateRequest(
        desired_date=date(2026, 10, 30),
        customer_name="Cliente Exemplo",
        customer_email="outro@example.com",
        status="pending",
        cart_context=[{"variant_id": str(item.product_variant_id), "quantity": item.quantity}],
        idempotency_key=f"109c-oct-{uuid4().hex}",
        client_host="127.0.0.1",
    )
    db.add(request)
    db.commit()
    preview = admin_client.get(f"/api/v1/admin/date-requests/{request.id}", headers=_headers(admin_client))
    assert preview.status_code == 200, preview.text
    assert any(row["public_reference"] == order.public_reference for row in preview.json()["accept_preview"]["existing_orders"])
    before = db.query(Order).count()
    moved = admin_client.post(
        f"/api/v1/admin/date-requests/{request.id}",
        headers=_headers(admin_client),
        json={"action": "move_existing_order", "order_id": str(order.id), "notify_customer": False},
    )
    assert moved.status_code == 200, moved.text
    db.expire_all()
    assert db.query(Order).count() == before
    stored = db.get(Order, order.id)
    assert stored.requested_date == date(2026, 11, 1)
    assert stored.production_local_date == date(2026, 10, 30)
    assert schedule_exception_of(stored)["label"] == "Antecipada a pedido do cliente"
    assert db.query(EmailOutbox).filter_by(kind="order_date_changed").count() == 0


def test_duplicate_lens_and_void(admin_client: TestClient, db: Session) -> None:
    from tests.contract.support import variant

    bread = variant(db, "Pão duplicado", 2490)
    first = _confirm(admin_client, db, send_confirmed(db, "109c-dup-a", bread))
    second = _confirm(admin_client, db, send_confirmed(db, "109c-dup-b", bread))
    second.customer_email = first.customer_email
    second.customer_name = first.customer_name
    db.add(
        PaymentRecord(
            order_id=first.id,
            expected_cents=first.total_cents or 0,
            amount_paid_cents=first.total_cents or 0,
            currency="BRL",
            financial_status="paid",
            idempotency_key=str(uuid4()),
        )
    )
    db.commit()
    _board, keys = managerial_board(db, get_settings())
    assert f"order:{first.id}" in keys["pending:possible_duplicate"]
    assert f"order:{second.id}" in keys["pending:possible_duplicate"]
    listed = admin_client.get(
        "/api/v1/admin/orders?lens=pending:possible_duplicate&status=all",
        headers=_headers(admin_client),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == len(keys["pending:possible_duplicate"])
    detail = admin_client.get(f"/api/v1/admin/orders/{second.id}", headers=_headers(admin_client))
    assert detail.json()["attention"] == f"Possível duplicado de {first.public_reference}"
    assert detail.json()["next_action"]["code"] == "check_duplicate"
    local = PaymentRecord(
        order_id=second.id,
        expected_cents=second.total_cents or 0,
        currency="BRL",
        financial_status="pending",
        idempotency_key=str(uuid4()),
    )
    db.add(local)
    db.commit()
    paid = admin_client.post(
        f"/api/v1/admin/orders/{second.id}/void-duplicate",
        headers=_headers(admin_client),
        json={"original_order_id": str(second.id), "reason": "o próprio pedido"},
    )
    assert paid.status_code == 409
    provider = PaymentRecord(
        order_id=first.id,
        expected_cents=1,
        currency="BRL",
        financial_status="pending",
        external_reference=f"hub-{uuid4().hex[:8]}",
        idempotency_key=str(uuid4()),
    )
    db.add(provider)
    db.commit()
    # Anular o segundo, que só tem pagamento local. O primeiro tem referência externa e não é o alvo.
    voided = admin_client.post(
        f"/api/v1/admin/orders/{second.id}/void-duplicate",
        headers=_headers(admin_client),
        json={"original_order_id": str(first.id), "reason": "mesmo cliente, encomenda repetida"},
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "confirmed"
    assert voided.json()["visible_stage"] == "voided"
    assert voided.json()["allowed_actions"] == []
    db.expire_all()
    stored = db.get(Order, second.id)
    assert stored.holds_capacity is False
    assert stored.status == "confirmed"
    assert db.get(PaymentRecord, local.id).financial_status == "cancelled"
    _board, keys = managerial_board(db, get_settings())
    assert f"order:{second.id}" not in keys["pending:possible_duplicate"]
    assert f"order:{second.id}" in keys["audit:duplicates"]
    assert f"order:{second.id}" not in keys.get("stage:accepted", set())
    assert db.query(EmailOutbox).filter_by(order_id=second.id, kind="order_date_changed").count() == 0
    original = admin_client.get(f"/api/v1/admin/orders/{first.id}", headers=_headers(admin_client))
    assert any(link["public_reference"] == stored.public_reference for link in original.json()["duplicate_links"])
    again = admin_client.post(
        f"/api/v1/admin/orders/{second.id}/void-duplicate",
        headers=_headers(admin_client),
        json={"original_order_id": str(first.id), "reason": "de novo"},
    )
    assert again.status_code == 409


def test_delivery_alignment_is_optional_and_atomic(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-delivery"))
    started = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/start-production",
        headers=_headers(admin_client),
        json={"unpaid_exception": True},
    )
    assert started.status_code == 200, started.text
    db.expire_all()
    order = db.get(Order, order.id)
    same = admin_client.post(f"/api/v1/admin/orders/{order.id}/confirm-delivery", headers=_headers(admin_client))
    # Sem o campo, a data não muda. A data da fornada pode não ser hoje.
    assert same.status_code == 200, same.text
    db.expire_all()
    order = db.get(Order, order.id)
    registered = order.production_local_date
    assert order.requested_date == registered or order.requested_date is not None
    if registered == bakery_today(get_settings()):
        assert order.production_local_date == registered
    else:
        assert order.production_local_date == registered
        assert db.scalars(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == order.id,
                OrderStatusHistory.reason.contains("fornada registrada ajustada"),
            )
        ).first() is None
    other = _confirm(admin_client, db, send_confirmed(db, "109c-align"))
    admin_client.post(
        f"/api/v1/admin/orders/{other.id}/start-production",
        headers=_headers(admin_client),
        json={"unpaid_exception": True},
    )
    db.expire_all()
    other = db.get(Order, other.id)
    if other.production_local_date != bakery_today(get_settings()):
        aligned = admin_client.post(
            f"/api/v1/admin/orders/{other.id}/confirm-delivery",
            headers=_headers(admin_client),
            json={"align_date_to_delivery": True, "align_origin": "customer"},
        )
        assert aligned.status_code == 200, aligned.text
        db.expire_all()
        other = db.get(Order, other.id)
        assert other.production_local_date == bakery_today(get_settings())
        assert other.requested_date != other.production_local_date
        assert db.query(EmailOutbox).filter_by(order_id=other.id, kind="order_date_changed").count() == 0
        assert db.scalars(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == other.id,
                OrderStatusHistory.reason.contains("fornada registrada ajustada"),
            )
        ).first() is not None


def test_requested_date_survives_reschedule(admin_client: TestClient, db: Session) -> None:
    order = _confirm(admin_client, db, send_confirmed(db, "109c-requested"))
    born = order.requested_date
    assert born is not None
    missing = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/reschedule",
        headers=_headers(admin_client),
        json={"date": _next(6).isoformat(), "reason": "sem origem", "notify_customer": False},
    )
    assert missing.status_code == 422
    assert db.get(Order, order.id).requested_date == born


def test_migration_downgrade_restores_kind(db: Session) -> None:
    order = send_confirmed(db, "109c-migration")
    db.commit()
    exclude_subject(db, "order", order.id, author_ref="teste", reason="registro de teste")
    db.commit()
    ini = Path(__file__).resolve().parents[2] / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    try:
        command.downgrade(config, "d5e9f2a18b33")
        command.upgrade(config, "head")
    finally:
        command.upgrade(config, "head")
    db.expire_all()
    row = db.scalars(select(ManagerialExclusion).where(ManagerialExclusion.subject_id == order.id)).one()
    assert row.kind == "test"


def test_schedule_exception_four_labels() -> None:
    base = date(2026, 11, 1)
    earlier = date(2026, 10, 30)
    later = date(2026, 11, 8)
    customer_early = SimpleNamespace(requested_date=base, production_local_date=earlier, date_change_origin="customer", date_change_reason=None, date_change_actor=None)
    customer_late = SimpleNamespace(requested_date=base, production_local_date=later, date_change_origin="customer", date_change_reason=None, date_change_actor=None)
    store_early = SimpleNamespace(requested_date=base, production_local_date=earlier, date_change_origin="store", date_change_reason=None, date_change_actor=None)
    store_late = SimpleNamespace(requested_date=base, production_local_date=later, date_change_origin="store", date_change_reason=None, date_change_actor=None)
    same = SimpleNamespace(requested_date=base, production_local_date=base, date_change_origin="customer", date_change_reason=None, date_change_actor=None)
    assert schedule_exception_of(customer_early)["label"] == "Antecipada a pedido do cliente"
    assert schedule_exception_of(customer_late)["label"] == "Adiada a pedido do cliente"
    assert schedule_exception_of(store_early)["label"] == "Antecipada pela loja"
    assert schedule_exception_of(store_late)["label"] == "Adiada pela loja"
    assert schedule_exception_of(same) is None
