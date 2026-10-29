"""Alertas, capacidade da recuperação, confirmação tardia e identificador Mercado Pago."""

import time
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import get_settings
from app.domain.actionhub_client import HubCheckoutResult, HubUnavailableError
from app.domain.errors import ConfirmationError
from app.domain.payment_webhooks import apply_actionhub_observation
from app.domain.payment_worker import BATCH_SIZE, process_payment_checks
from app.domain.storefront_orders import start_checkout
from app.domain.web_push import save_subscription
from app.models.email_outbox import EmailOutbox
from app.models.house_fidelity import HouseFidelityEvent
from app.models.managerial import OpsOwnerAlert, OpsPushDelivery
from app.models.orders import OrderStatusHistory
from app.models.payments import PaymentRecord
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.test_prompt105a_payments import approved, make_order


def _enable_ops(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-105a@example.test")
    get_settings.cache_clear()
    monkeypatch.setattr("app.domain.web_push.vapid_configured", lambda settings: True)
    monkeypatch.setattr("app.domain.web_push.actor_may_receive", lambda settings, actor: True)


def _device(db) -> None:
    save_subscription(
        db,
        get_settings(),
        actor_ref="admin:teste",
        endpoint="https://fcm.googleapis.com/fcm/send/alerta-105a",
        p256dh="B" * 80,
        auth_secret="C" * 24,
        label="Aparelho de teste",
    )
    db.commit()


def test_waiting_for_the_customer_is_not_a_sync_failure(db, monkeypatch):
    _enable_ops(monkeypatch)
    order, record = make_order(db)
    db.commit()
    pending = replace(
        approved(order, record),
        status="PENDING",
        provider_status="pending",
        paid_amount_cents=None,
        mp_payment_id=None,
    )
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: pending,
    )
    now = datetime.now(UTC) + timedelta(minutes=2)
    process_payment_checks(db, get_settings(), now=now)
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=120))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    assert record.financial_status == "pending"


def test_persistent_sync_failure_alerts_once_and_closes(db, monkeypatch):
    _enable_ops(monkeypatch)
    _device(db)
    order, record = make_order(db)
    db.commit()
    now = datetime.now(UTC) + timedelta(minutes=2)

    def unavailable(*a, **k):
        raise HubUnavailableError("offline")

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", unavailable)
    process_payment_checks(db, get_settings(), now=now)
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=89))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 0
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=90))
    db.commit()
    mail = db.query(EmailOutbox).filter_by(kind="payment_sync_alert").one()
    assert order.public_reference in mail.body
    assert "não significa que o cliente deixou de pagar" in mail.body
    assert f"/admin/pedidos/{order.id}" in mail.body
    assert "Última verificação" in mail.body
    pushes = db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").all()
    assert len(pushes) == 1
    assert pushes[0].path == f"/admin/pedidos/{order.id}"
    assert "Não conclua que o cliente não pagou." in pushes[0].body
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=150))
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    assert db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").count() == 1
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order, record),
    )
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=181))
    db.commit()
    assert record.financial_status == "paid"
    assert db.query(EmailOutbox).filter_by(kind="payment_sync_alert").count() == 1
    assert db.query(OpsPushDelivery).filter_by(kind="payment_sync_alert").count() == 1
    closed = db.query(OpsOwnerAlert).filter_by(event_key=mail.dedupe_key).all()
    assert closed
    assert all("encerrada" in row.summary for row in closed)


def test_new_pending_checks_are_not_blocked_by_historical_paid(db, monkeypatch):
    orders = []
    pending_keys = []
    paid_keys = []
    for index in range(12):
        order, record = make_order(db)
        record.financial_status = "paid"
        record.amount_paid_cents = 7000
        record.mp_payment_id = f"old-{index}"
        paid_keys.append(record.idempotency_key)
        orders.append((order, record))
    for _ in range(3):
        order, record = make_order(db)
        pending_keys.append(record.idempotency_key)
        orders.append((order, record))
    db.commit()
    seen = []

    def lookup(settings, *, payment_request_id):
        seen.append(payment_request_id)
        time.sleep(0.01)
        match = next(record for order, record in orders if record.idempotency_key == payment_request_id)
        parent = next(order for order, record in orders if record.id == match.id)
        return approved(parent, match)

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup)
    started = time.perf_counter()
    result = process_payment_checks(db, get_settings(), now=datetime.now(UTC) + timedelta(hours=2))
    elapsed = time.perf_counter() - started
    print(f"CAPACITY elapsed_s={elapsed:.3f} checked={result['checked']} pending_first={seen[:3] == pending_keys}")
    assert result["checked"] == BATCH_SIZE
    assert set(seen[:3]) == set(pending_keys)
    assert set(seen[3:]).issubset(set(paid_keys))
    assert elapsed < 30
    assert elapsed >= 0.05


def test_slow_hub_measures_the_cycle_and_recovers(db, monkeypatch):
    order, record = make_order(db)
    db.commit()
    now = datetime.now(UTC) + timedelta(minutes=2)

    def slow(*a, **k):
        time.sleep(0.2)
        raise HubUnavailableError("lento")

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", slow)
    started = time.perf_counter()
    assert process_payment_checks(db, get_settings(), now=now)["failures"] == 1
    elapsed = time.perf_counter() - started
    print(f"SLOW_HUB elapsed_s={elapsed:.3f}")
    assert 0.2 <= elapsed < 30
    assert record.financial_status == "pending"
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order, record),
    )
    process_payment_checks(db, get_settings(), now=now + timedelta(seconds=31))
    assert record.financial_status == "paid"


def test_webhook_is_not_blocked_by_a_slow_lookup(db, monkeypatch):
    order, record = make_order(db)
    db.commit()
    engine = db.get_bind()
    settings = get_settings()
    waited = {}

    def lookup(*a, **k):
        other = Session(engine)
        started = time.perf_counter()
        try:
            other.execute(text("SET lock_timeout = '250ms'"))
            result = apply_actionhub_observation(
                other,
                settings,
                {
                    "app_id": settings.actionhub_app_id,
                    "outbox_id": "webhook-during-lookup",
                    "event_type": "PAYMENT_CONFIRMED",
                    "payload": {
                        "order_id": record.external_reference,
                        "order_reference": order.public_reference,
                        "financial_status": "paid",
                        "paid_amount_cents": 7000,
                        "mp_payment_id": "185349985529",
                        "mp_status": "approved",
                        "method": "card",
                        "provider_approved_at": "2026-10-27T17:10:26-03:00",
                    },
                },
            )
            other.commit()
        finally:
            other.close()
        waited["seconds"] = time.perf_counter() - started
        assert result["process_status"] == "applied"
        assert waited["seconds"] < 0.25
        time.sleep(0.3)
        return approved(order, record)

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup)
    process_payment_checks(db, settings, now=datetime.now(UTC) + timedelta(minutes=2))
    print(f"WEBHOOK_DURING_LOOKUP elapsed_s={waited['seconds']:.3f}")
    db.expire_all()
    fresh = db.get(PaymentRecord, record.id)
    assert fresh.financial_status == "paid"
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1


def test_legacy_payment_confirmed_after_the_accept_lock(db):
    order, record = make_order(db, state="submitted")
    before = order.confirmed_at
    result = apply_actionhub_observation(
        db,
        get_settings(),
        {
            "app_id": get_settings().actionhub_app_id,
            "outbox_id": "legacy-paid",
            "event_type": "PAYMENT_CONFIRMED",
            "payload": {
                "order_id": record.external_reference,
                "order_reference": order.public_reference,
                "financial_status": "paid",
                "paid_amount_cents": 7000,
                "mp_payment_id": "185349985529",
                "mp_status": "approved",
                "method": "card",
                "provider_approved_at": "2026-10-27T17:10:26-03:00",
            },
        },
    )
    assert result["process_status"] == "applied"
    assert record.financial_status == "paid"
    assert record.mp_payment_id == "185349985529"
    assert record.confirmed_at.hour == 17
    assert order.status == "submitted"
    assert order.confirmed_at == before
    assert order.production_started_at is None
    assert db.query(OrderStatusHistory).count() == 0
    with pytest.raises(ConfirmationError, match="depois do aceite"):
        start_checkout(db, get_settings(), order, "card")


def test_empty_provider_id_is_filled_without_repeating_effects(db, monkeypatch):
    order, record = make_order(db, state="confirmed")
    settings = get_settings()
    apply_actionhub_observation(
        db,
        settings,
        {
            "app_id": settings.actionhub_app_id,
            "outbox_id": "paid-without-provider-id",
            "event_type": "PAYMENT_CONFIRMED",
            "payload": {
                "order_id": record.external_reference,
                "order_reference": order.public_reference,
                "financial_status": "paid",
                "paid_amount_cents": 7000,
                "mp_status": "approved",
                "method": "card",
                "provider_approved_at": "2026-10-27T17:10:26-03:00",
            },
        },
    )
    db.flush()
    assert record.financial_status == "paid"
    assert record.mp_payment_id is None
    original_confirmed = record.confirmed_at
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1
    monkeypatch.setattr(
        "app.domain.storefront_orders.lookup_amount_checkout",
        lambda *a, **k: approved(order, record),
    )
    from app.domain.storefront_orders import reconcile_payment_record

    reconcile_payment_record(db, settings, order, record)
    db.flush()
    assert record.mp_payment_id == "test-" + record.id.hex
    assert record.confirmed_at == original_confirmed
    assert order.status == "confirmed"
    assert order.production_started_at is None
    assert order.confirmed_at is None
    assert db.query(EmailOutbox).filter_by(order_id=order.id, kind="payment_approved").count() == 1
    assert db.query(HouseFidelityEvent).count() == 0
    assert db.query(OrderStatusHistory).count() == 0


def _stamp_due_order(engine, first_id, second_id) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE payment_records DISABLE TRIGGER trg_payment_records_updated_at"))
        conn.execute(
            text("UPDATE payment_records SET updated_at = now() - interval '10 minutes' WHERE id = :id"),
            {"id": first_id},
        )
        conn.execute(
            text("UPDATE payment_records SET updated_at = now() - interval '9 minutes' WHERE id = :id"),
            {"id": second_id},
        )
        conn.execute(text("ALTER TABLE payment_records ENABLE TRIGGER trg_payment_records_updated_at"))


def test_webhook_for_a_is_not_blocked_while_b_is_still_in_lookup(db, monkeypatch):
    order_a, record_a = make_order(db)
    order_b, record_b = make_order(db)
    db.commit()
    engine = db.get_bind()
    _stamp_due_order(engine, record_a.id, record_b.id)
    settings = get_settings()
    b_waiting = threading.Event()
    release_b = threading.Event()
    worker_result = {}

    def lookup(_settings, *, payment_request_id):
        if payment_request_id == record_a.idempotency_key:
            return approved(order_a, record_a)
        if payment_request_id == record_b.idempotency_key:
            b_waiting.set()
            assert release_b.wait(5)
            return approved(order_b, record_b)
        raise AssertionError(payment_request_id)

    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup)

    def run_worker():
        worker = Session(engine)
        try:
            worker_result["value"] = process_payment_checks(
                worker, settings, now=datetime.now(UTC) + timedelta(hours=2)
            )
        finally:
            worker.close()

    thread = threading.Thread(target=run_worker)
    thread.start()
    try:
        assert b_waiting.wait(5)
        seen = Session(engine)
        try:
            assert seen.get(PaymentRecord, record_a.id).financial_status == "paid"
            assert seen.get(PaymentRecord, record_b.id).financial_status == "pending"
        finally:
            seen.close()
        other = Session(engine)
        started = time.perf_counter()
        try:
            other.execute(text("SET lock_timeout = '250ms'"))
            webhook = apply_actionhub_observation(
                other,
                settings,
                {
                    "app_id": settings.actionhub_app_id,
                    "outbox_id": "webhook-a-while-b-looks-up",
                    "event_type": "PAYMENT_CONFIRMED",
                    "payload": {
                        "order_id": record_a.external_reference,
                        "order_reference": order_a.public_reference,
                        "financial_status": "paid",
                        "paid_amount_cents": 7000,
                        "mp_payment_id": "test-" + record_a.id.hex,
                        "mp_status": "approved",
                        "method": "card",
                        "provider_approved_at": "2026-10-27T17:10:26-03:00",
                    },
                },
            )
            other.commit()
        finally:
            other.close()
        elapsed = time.perf_counter() - started
        print(f"WEBHOOK_A_WHILE_B elapsed_s={elapsed:.3f} b_still_waiting={not release_b.is_set()}")
        assert not release_b.is_set()
        assert elapsed < 0.25
        assert webhook["process_status"] == "applied"
    finally:
        release_b.set()
        thread.join(5)
    assert not thread.is_alive()
    assert worker_result["value"]["checked"] == 2
    final = Session(engine)
    try:
        fresh_a = final.get(PaymentRecord, record_a.id)
        fresh_b = final.get(PaymentRecord, record_b.id)
        assert fresh_a.financial_status == "paid"
        assert fresh_b.financial_status == "paid"
        assert final.query(PaymentRecord).count() == 2
        assert final.query(EmailOutbox).filter_by(order_id=order_a.id, kind="payment_approved").count() == 1
        assert final.query(EmailOutbox).filter_by(order_id=order_b.id, kind="payment_approved").count() == 1
        assert final.get(type(order_a), order_a.id).status == "confirmed"
        assert final.get(type(order_b), order_b.id).status == "confirmed"
        assert final.query(HouseFidelityEvent).count() == 0
        assert final.query(OrderStatusHistory).count() == 0
    finally:
        final.close()


def _published_loja_handler():
    import importlib.util
    import os
    import subprocess
    from pathlib import Path

    override = os.environ.get("LOJA_27F_WEBHOOK", "").strip()
    path = Path(override) if override else Path(r"C:\Temp\loja_payment_webhooks_27f.py")
    if not override:
        source = subprocess.check_output(
            ["git", "show", "HEAD:lojadepaes/backend/app/domain/payment_webhooks.py"],
            cwd=r"C:\Projetos",
        )
        path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("loja_payment_webhooks_27f", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sign_hub_event(event: dict, secret: str) -> str:
    import base64
    import hashlib
    import hmac
    import json

    def pack(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = pack({"alg": "HS256", "typ": "JWT"})
    body = pack({**event, "exp": 4_102_444_800})
    signature = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    signed = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{body}.{signed}"


def test_approval_during_return_is_applied_once(db, monkeypatch):
    from app.domain.payment_return import (
        FORBIDDEN_HUB_RETURN,
        HUB_FINANCIAL_RETURN,
        LOJA_FINANCIAL_RETURN,
        durable_card_event,
    )

    assert HUB_FINANCIAL_RETURN == "hub-confirm-durable-20261028"
    assert LOJA_FINANCIAL_RETURN == "lojadepaes:prod-20261027f"
    assert FORBIDDEN_HUB_RETURN == "hub-card-paid-without-outbox"
    secret = "return-window-secret"
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", secret)
    get_settings.cache_clear()
    settings = get_settings()
    published = _published_loja_handler()
    returned_order, returned_record = make_order(db, state="confirmed")
    forward_order, forward_record = make_order(db, state="confirmed")
    silent_order, silent_record = make_order(db, state="confirmed")
    db.commit()
    returned_event = durable_card_event(
        outbox_id="return-window-loja-27f",
        hub_order_id=returned_record.external_reference,
        order_reference=returned_order.public_reference,
        paid_amount_cents=7000,
        mp_payment_id="186395637864",
        app_id=settings.actionhub_app_id,
    )
    first = published.apply_actionhub_webhook(db, settings, _sign_hub_event(returned_event, secret))
    assert first["process_status"] == "applied"
    assert returned_record.financial_status == "paid"
    replay = published.apply_actionhub_webhook(db, settings, _sign_hub_event(returned_event, secret))
    assert replay["duplicate"] is True
    forward_event = durable_card_event(
        outbox_id="return-window-loja-105a",
        hub_order_id=forward_record.external_reference,
        order_reference=forward_order.public_reference,
        paid_amount_cents=7000,
        mp_payment_id="185349985529",
        app_id=settings.actionhub_app_id,
    )
    forward = apply_actionhub_observation(db, settings, forward_event)
    assert forward["process_status"] == "applied"
    assert forward_record.financial_status == "paid"
    again = apply_actionhub_observation(db, settings, forward_event)
    assert again["duplicate"] is True
    assert silent_record.financial_status == "pending"
    db.flush()
    assert db.query(PaymentRecord).count() == 3
    assert db.query(EmailOutbox).filter_by(order_id=returned_order.id, kind="payment_approved").count() == 1
    assert db.query(EmailOutbox).filter_by(order_id=forward_order.id, kind="payment_approved").count() == 1
    assert db.query(EmailOutbox).filter_by(order_id=silent_order.id).count() == 0
    assert returned_order.status == "confirmed"
    assert forward_order.status == "confirmed"
    assert silent_order.status == "confirmed"
    assert returned_order.production_started_at is None
    assert forward_order.production_started_at is None
    get_settings.cache_clear()
