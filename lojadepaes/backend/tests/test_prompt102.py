"""Prompt 102. Dados fictícios. Não envia mensagem e não libera reserva."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.core.config import get_settings
from app.domain.email_outbox import enqueue_admin_order_email
from app.domain.managerial_exclusion import apply_identified_tests, identity_class, reverse_subject
from app.domain.orders import new_public_reference
from app.domain.owner_alerts import notify_acceptance, retry_owner_alert
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsOwnerAlert
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import priced_catalog

assert admin_client
assert priced_catalog


def _order(db: Session, catalog: dict, **fields) -> Order:
    loaves = fields.pop("loaves", 1)
    order = Order(
        public_reference=new_public_reference(),
        currency="BRL",
        customer_note="",
        customer_name=fields.pop("customer_name", "Cliente Real"),
        customer_email=fields.pop("customer_email", f"c-{uuid4().hex[:8]}@example.test"),
        **fields,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            dough_type_id=catalog["dough"].id,
            bread_shape_id=catalog["shape"].id,
            dough_name_snapshot="Focaccia",
            quantity=loaves,
        )
    )
    db.flush()
    return order


def test_exact_name_leaves_the_operation_and_homonym_stays(db: Session, admin_client) -> None:
    catalog = priced_catalog(db)
    assert identity_class("Oscar") == "exact"
    assert identity_class("  Rastro ") == "exact"
    assert identity_class("Oscar Silva") == "ambiguous"
    assert identity_class("Rastreador") == "other"
    oscar = _order(
        db,
        catalog,
        customer_name="Oscar",
        status="confirmed",
        total_cents=1000,
        holds_capacity=True,
        production_local_date=date(2026, 10, 24),
    )
    rastro = _order(db, catalog, customer_name="Rastro", status="submitted", total_cents=500)
    silva = _order(
        db,
        catalog,
        customer_name="Oscar Silva",
        status="confirmed",
        total_cents=700,
        production_local_date=date(2026, 10, 24),
    )
    held = oscar.holds_capacity
    before_orders = db.scalar(select(func.count()).select_from(Order))
    db.commit()
    result = apply_identified_tests(db, author_ref="prompt-102")
    db.commit()
    assert result["ambiguous"]
    assert silva.public_reference not in {item["reference"] for item in result["exact"]}
    assert oscar.public_reference in result["still_holding_capacity"]
    db.refresh(oscar)
    assert oscar.holds_capacity is held
    assert db.scalar(select(func.count()).select_from(Order)) == before_orders
    login(admin_client)
    board = admin_client.get("/api/v1/admin/ops/attendance-summary").json()["board"]
    assert board["excluded_tests"] >= 2
    assert board["excluded_holding_capacity"] >= 1
    queue = admin_client.get("/api/v1/admin/orders", params={"status": "all", "page_size": 50})
    refs = {item["public_reference"] for item in queue.json()["items"]}
    assert oscar.public_reference not in refs
    assert rastro.public_reference not in refs
    assert silva.public_reference in refs
    audit = admin_client.get("/api/v1/admin/orders", params={"lens": "audit:tests", "page_size": 50})
    audit_refs = {item["public_reference"] for item in audit.json()["items"]}
    assert oscar.public_reference in audit_refs
    assert silva.public_reference not in audit_refs
    assert audit.json()["total"] == len(audit_refs)
    reverse_subject(db, "order", oscar.id, author_ref="prompt-102", reason="revisão")
    db.commit()
    restored = admin_client.get("/api/v1/admin/orders", params={"status": "all", "page_size": 50})
    assert oscar.public_reference in {item["public_reference"] for item in restored.json()["items"]}


def test_production_agenda_uses_bake_date_and_does_not_write(db: Session, admin_client) -> None:
    catalog = priced_catalog(db)
    day = date(2026, 10, 24)
    first = _order(
        db,
        catalog,
        status="confirmed",
        production_local_date=day,
        loaves=2,
        total_cents=2000,
        customer_name="Cliente Um",
    )
    second = _order(
        db,
        catalog,
        status="in_production",
        production_local_date=day,
        loaves=3,
        total_cents=3000,
        customer_name="Cliente Dois",
    )
    db.add(
        OrderItem(
            order_id=second.id,
            dough_type_id=catalog["dough"].id,
            bread_shape_id=catalog["shape"].id,
            dough_name_snapshot="Brioche",
            quantity=1,
        )
    )
    done = _order(
        db,
        catalog,
        status="completed",
        production_local_date=day,
        loaves=4,
        customer_name="Cliente Entregue",
    )
    cancelled = _order(
        db,
        catalog,
        status="cancelled",
        production_local_date=day,
        customer_name="Cliente Cancelado",
    )
    undated = _order(db, catalog, status="submitted", customer_name="Sem Data")
    desired = _order(
        db,
        catalog,
        status="submitted",
        proposed_production_date=day,
        customer_name="Só Desejada",
    )
    hidden = _order(
        db,
        catalog,
        status="confirmed",
        production_local_date=day,
        customer_name="Oscar",
    )
    year_edge = _order(
        db,
        catalog,
        status="confirmed",
        production_local_date=date(2026, 1, 1),
        created_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        customer_name="Virada",
    )
    request = DateRequest(
        customer_name="Solicitante Real",
        customer_email=f"s-{uuid4().hex[:6]}@example.test",
        idempotency_key=f"p102-{uuid4().hex}",
        client_host="test",
        desired_date=day,
        intended_quantity=1,
        status="pending",
    )
    converted = DateRequest(
        customer_name="Já Virou Pedido",
        customer_email=f"s-{uuid4().hex[:6]}@example.test",
        idempotency_key=f"p102-{uuid4().hex}",
        client_host="test",
        desired_date=day,
        status="converted",
        converted_order_id=first.id,
    )
    db.add_all([request, converted])
    db.commit()
    apply_identified_tests(db, author_ref="prompt-102")
    db.commit()
    login(admin_client)
    before = first.status
    agenda = admin_client.get("/api/v1/admin/ops/production-agenda", params={"year": 2026, "month": 10})
    assert agenda.status_code == 200, agenda.text
    body = agenda.json()
    assert body["timezone"] == "America/Sao_Paulo"
    assert body["today"]
    chosen = next(item for item in body["days"] if item["date"] == "2026-10-24")
    refs = {item["reference"] for item in chosen["open"]}
    assert first.public_reference in refs
    assert second.public_reference in refs
    assert chosen["open_orders"] == 2
    assert chosen["historical_orders"] == 1
    assert done.public_reference in {item["reference"] for item in chosen["historical"]}
    assert chosen["orders"] == 3
    assert chosen["bread_units"] == 2 + 4 + 4
    assert hidden.public_reference not in {
        item["reference"]
        for group in ("open", "historical", "pending", "cancelled")
        for item in chosen[group]
    }
    pending_refs = {item["reference"] for item in chosen["pending"]}
    assert desired.public_reference in pending_refs
    assert request.customer_name in {item["customer_name"] for item in chosen["pending"]}
    assert "Já Virou Pedido" not in {item["customer_name"] for item in chosen["pending"]}
    assert chosen["pending_requests"] == 2
    assert cancelled.public_reference in {item["reference"] for item in chosen["cancelled"]}
    assert cancelled.public_reference not in refs
    empty = next(item for item in body["days"] if item["date"] == "2026-10-01")
    assert empty["orders"] == 0
    assert empty["open"] == []
    assert undated.public_reference in {item["reference"] for item in body["undated"]}
    db.refresh(first)
    assert first.status == before
    january = admin_client.get("/api/v1/admin/ops/production-agenda", params={"year": 2026, "month": 1})
    new_year = next(item for item in january.json()["days"] if item["date"] == "2026-01-01")
    assert year_edge.public_reference in {item["reference"] for item in new_year["open"]}
    december = admin_client.get("/api/v1/admin/ops/production-agenda", params={"year": 2025, "month": 12})
    assert all(
        year_edge.public_reference not in {item["reference"] for item in day["open"]}
        for day in december.json()["days"]
    )
    composition = next(item for item in chosen["open"] if item["reference"] == second.public_reference)
    assert "Focaccia" in composition["composition"]
    assert "Brioche" in composition["composition"]
    assert "Rua" not in agenda.text


def test_owner_alerts_are_independent_and_whatsapp_stays_off(db: Session, admin_client, monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-102@example.test")
    monkeypatch.setenv("LOJADEPAES_WHATSAPP_PROVIDER", "")
    monkeypatch.setenv("LOJADEPAES_WHATSAPP_OPS_ENABLED", "false")
    settings = get_settings()
    order = _order(
        db,
        priced_catalog(db),
        status="submitted",
        customer_name="Cliente Novo",
        proposed_production_date=date(2026, 11, 2),
        total_cents=4500,
        delivery_street="Rua Sigilosa 10",
    )
    request = DateRequest(
        customer_name="Cliente Novo",
        customer_email=order.customer_email,
        idempotency_key=f"p102-{uuid4().hex}",
        client_host="test",
        desired_date=date(2026, 11, 2),
        status="converted",
        converted_order_id=order.id,
    )
    order.source_date_request_id = None
    db.add(request)
    db.commit()
    before_alerts = db.scalar(select(func.count()).select_from(OpsOwnerAlert))
    enqueue_admin_order_email(db, settings, order)
    enqueue_admin_order_email(db, settings, order)
    db.commit()
    emails = list(db.scalars(select(EmailOutbox).where(EmailOutbox.order_id == order.id)))
    assert len(emails) == 1
    alerts = list(db.scalars(select(OpsOwnerAlert).where(OpsOwnerAlert.order_id == order.id)))
    assert {row.channel for row in alerts} == {"email", "whatsapp"}
    whatsapp = next(row for row in alerts if row.channel == "whatsapp")
    assert whatsapp.status == "disabled"
    assert whatsapp.last_error
    joined = " ".join(row.summary for row in alerts)
    assert "Rua Sigilosa" not in joined
    assert order.customer_email not in joined
    assert "Data desejada" in joined
    notify_acceptance(db, settings, order, request)
    notify_acceptance(db, settings, order, request)
    db.commit()
    acceptance = list(
        db.scalars(select(EmailOutbox).where(EmailOutbox.kind == "acceptance_update_admin"))
    )
    assert len(acceptance) == 1
    assert acceptance[0].dedupe_key.startswith("acceptance:")
    again = retry_owner_alert(db, settings, whatsapp.id)
    assert again.status == "disabled"
    assert again.attempts == 0
    login_token = login(admin_client)
    summary = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert summary.status_code == 200
    assert db.scalar(select(func.count()).select_from(OpsOwnerAlert)) == before_alerts + 4
    assert summary.json()["owner_alerts"]["whatsapp"]["active"] is False
    saved = admin_client.post(
        "/api/v1/admin/ops/alert-channels/whatsapp",
        json={"number": "+5585999000000"},
        headers={"X-CSRF-Token": login_token},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["enabled"] is False
    hidden = _order(db, priced_catalog(db), customer_name="Oscar", status="submitted")
    apply_identified_tests(db, author_ref="prompt-102")
    db.commit()
    alerts_before = db.scalar(select(func.count()).select_from(OpsOwnerAlert))
    emails_before = db.scalar(select(func.count()).select_from(EmailOutbox))
    enqueue_admin_order_email(db, settings, hidden)
    db.commit()
    assert db.scalar(select(func.count()).select_from(OpsOwnerAlert)) == alerts_before
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == emails_before
    get_settings.cache_clear()


def test_reviewed_references_are_marked_without_a_name_rule(db: Session, admin_client) -> None:
    catalog = priced_catalog(db)
    chosen = _order(db, catalog, customer_name="Rastro 145", status="cancelled", holds_capacity=False)
    other = _order(db, catalog, customer_name="Oscar S G Braga", status="completed", holds_capacity=True)
    db.commit()
    from app.domain.managerial_exclusion import exclude_references

    result = exclude_references(db, [chosen.public_reference], author_ref="prompt-102")
    db.commit()
    assert result["marked"] == [chosen.public_reference]
    assert result["still_holding_capacity"] == []
    db.refresh(other)
    assert other.holds_capacity is True
    login(admin_client)
    queue = admin_client.get("/api/v1/admin/orders", params={"status": "all", "page_size": 50})
    refs = {item["public_reference"] for item in queue.json()["items"]}
    assert chosen.public_reference not in refs
    assert other.public_reference in refs
