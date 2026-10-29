"""Prompt 102B. Push isolado. Não envia rede real, e-mail real nem pedido de produção."""

from datetime import date
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.email_outbox import enqueue_admin_order_email
from app.domain.managerial_exclusion import apply_identified_tests
from app.domain.orders import new_public_reference
from app.domain.owner_alerts import notify_acceptance
from app.domain.web_push import (
    enqueue_event_pushes,
    enqueue_test_push,
    process_due_pushes,
    save_subscription,
)
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import AdminPushSubscription, OpsPushDelivery
from app.models.orders import Order, OrderItem
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import priced_catalog

assert admin_client
assert priced_catalog

_P256 = "B" * 80
_AUTH = "C" * 24


def _vapid_pair() -> tuple[str, str]:
    vapid = Vapid()
    vapid.generate_keys()
    private = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64urlencode(
        vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
    )
    return private, public


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    private, public = _vapid_pair()
    monkeypatch.setenv("LOJADEPAES_VAPID_PRIVATE_KEY", private)
    monkeypatch.setenv("LOJADEPAES_VAPID_PUBLIC_KEY", public)
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-102b@example.test")
    get_settings.cache_clear()


def _order(db: Session, catalog: dict, **fields) -> Order:
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
            quantity=1,
        )
    )
    db.flush()
    return order


def _device(db: Session, settings, suffix: str) -> AdminPushSubscription:
    return save_subscription(
        db,
        settings,
        actor_ref="admin:padaria",
        endpoint=f"https://fcm.googleapis.com/fcm/send/{suffix}",
        p256dh=_P256,
        auth_secret=_AUTH,
        label="Este aparelho",
    )


def test_push_follows_new_orders_without_history_or_phone(db: Session, admin_client, monkeypatch) -> None:
    _enable(monkeypatch)
    settings = get_settings()
    catalog = priced_catalog(db)
    old = _order(db, catalog, customer_name="Pedido Antigo")
    db.commit()
    enqueue_admin_order_email(db, settings, old)
    db.commit()
    assert db.scalar(select(func.count()).select_from(OpsPushDelivery)) == 0
    first = _device(db, settings, "um")
    second = _device(db, settings, "dois")
    again = save_subscription(
        db,
        settings,
        actor_ref="admin:padaria",
        endpoint=first.endpoint,
        p256dh=_P256,
        auth_secret=_AUTH,
        label="Este aparelho",
    )
    assert again.id == first.id
    assert db.scalar(select(func.count()).select_from(AdminPushSubscription)) == 2
    assert db.scalar(select(func.count()).select_from(OpsPushDelivery)) == 0
    order = _order(db, catalog, customer_name="Maria Forno")
    db.commit()
    enqueue_admin_order_email(db, settings, order)
    enqueue_admin_order_email(db, settings, order)
    db.commit()
    rows = list(db.scalars(select(OpsPushDelivery)))
    assert len(rows) == 2
    assert {row.subscription_id for row in rows} == {first.id, second.id}
    assert all(row.body.startswith(order.public_reference) for row in rows)
    assert all("Maria" not in row.body and "@" not in row.body for row in rows)
    assert all(row.path == f"/admin/pedidos/{order.id}" for row in rows)
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == 2

    calls = {"n": 0}

    def flaky(device, _payload, _settings):
        if device.id == second.id:
            return "inactive"
        calls["n"] += 1
        return "retry" if calls["n"] == 1 else "accepted"

    process_due_pushes(db, settings, sender=flaky)
    db.commit()
    process_due_pushes(db, settings, sender=flaky)
    db.commit()
    db.refresh(second)
    assert second.active is False
    statuses = {
        row.subscription_id: row.status
        for row in db.scalars(select(OpsPushDelivery).where(OpsPushDelivery.event_key == rows[0].event_key))
    }
    assert statuses[second.id] == "inactive"
    assert "accepted" in statuses.values()
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == 2
    hidden = _order(db, catalog, customer_name="Oscar", status="cancelled")
    db.commit()
    apply_identified_tests(db, author_ref="prompt-102b")
    db.commit()
    emails = db.scalar(select(func.count()).select_from(EmailOutbox))
    pushes = db.scalar(select(func.count()).select_from(OpsPushDelivery))
    enqueue_admin_order_email(db, settings, hidden)
    db.commit()
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == emails
    assert db.scalar(select(func.count()).select_from(OpsPushDelivery)) == pushes


def test_failures_stay_on_one_device_and_do_not_mail(db: Session, admin_client, monkeypatch) -> None:
    _enable(monkeypatch)
    settings = get_settings()
    device = _device(db, settings, "teste")
    db.commit()
    emails = db.scalar(select(func.count()).select_from(EmailOutbox))
    row = enqueue_test_push(db, settings, actor_ref="admin:padaria", device_id=device.id)
    process_due_pushes(db, settings, sender=lambda *_args: "ambiguous")
    db.commit()
    db.refresh(row)
    assert row.status == "failed"
    assert row.attempts == 1
    process_due_pushes(db, settings, sender=lambda *_args: "accepted")
    db.commit()
    db.refresh(row)
    assert row.status == "failed"
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == emails
    other = _device(db, settings, "outro")
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", "outra-conta")
    get_settings.cache_clear()
    renamed = get_settings()
    event = enqueue_event_pushes(
        db,
        renamed,
        event_key="pedido-novo",
        kind="order_submitted_admin",
        order_id=None,
        date_request_id=None,
    )
    process_due_pushes(db, renamed, sender=lambda *_args: "accepted")
    db.commit()
    assert event == 0
    db.refresh(device)
    db.refresh(other)
    assert device.active is False
    assert other.active is False


def test_acceptance_is_one_notice_and_bad_endpoint_is_refused(db: Session, admin_client, monkeypatch) -> None:
    _enable(monkeypatch)
    settings = get_settings()
    catalog = priced_catalog(db)
    device = _device(db, settings, "aceite")
    order = _order(db, catalog)
    request = DateRequest(
        desired_date=date(2026, 10, 30),
        customer_name="Cliente Real",
        customer_email="pessoa@example.test",
        status="converted",
        idempotency_key=uuid4().hex,
        client_host="test",
        converted_order_id=order.id,
    )
    db.add(request)
    db.commit()
    notify_acceptance(db, settings, order, request)
    notify_acceptance(db, settings, order, request)
    db.commit()
    rows = list(db.scalars(select(OpsPushDelivery).where(OpsPushDelivery.subscription_id == device.id)))
    assert len(rows) == 1
    assert rows[0].kind == "acceptance_update"
    assert rows[0].title == "Loja de Pães — Solicitação aceita"
    assert "pessoa@example.test" not in rows[0].body
    with pytest.raises(ValueError):
        save_subscription(
            db,
            settings,
            actor_ref="admin:padaria",
            endpoint="https://evil.example/push/hook",
            p256dh=_P256,
            auth_secret=_AUTH,
            label="Este aparelho",
        )
    assert admin_client.get("/api/v1/admin/ops/push").status_code == 401
    csrf = login(admin_client)
    blocked = admin_client.post(
        "/api/v1/admin/ops/push/subscriptions",
        json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/sem-csrf",
            "p256dh": _P256,
            "auth": _AUTH,
        },
    )
    assert blocked.status_code == 403
    saved = admin_client.post(
        "/api/v1/admin/ops/push/subscriptions",
        headers={"X-CSRF-Token": csrf},
        json={
            "endpoint": "https://web.push.apple.com/push/device",
            "p256dh": _P256,
            "auth": _AUTH,
            "label": "iPhone",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["receipt_confirmed"] is False
    assert "endpoint" not in body
    listed = admin_client.get("/api/v1/admin/ops/push/devices")
    assert "web.push.apple.com" not in listed.text
    revoke = admin_client.post(
        f"/api/v1/admin/ops/push/devices/{body['id']}/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoke.status_code == 200
    assert revoke.json()["active"] is False
