"""94A: identificação capturada, webhook de planos e cabeçalho. Sem e-mail externo."""

import re
import time
from collections.abc import Iterator

import pytest
from app.api.v1.conta import account_situation
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubUnavailableError
from app.domain.baker_library.access import can_use_ai
from app.domain.customer_identity import start_resume, start_signup, verify_code
from app.domain.storefront_orders import apply_subscriber_discount
from app.main import create_app
from app.models.baker_library import HubPlansEvent
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_SESSION_SECRET
from tests.test_prompt94 import _sign

TEST_SECRET = "loja-test-secret"


@pytest.fixture
def shop_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", TEST_SECRET)
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def _latest_code(db: Session) -> str:
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    match = re.search(r"é (\d{6})", mail.body)
    assert match
    return match.group(1)


def test_identify_sends_code_to_registered_email_and_header_stays_visitor_until_verify(
    db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    settings = get_settings()
    started = start_signup(db, settings, "Ana 94A", "ana.94a@example.com", "390.533.447-05")
    assert started["ok"] is True
    assert started["needs_verification"] is True
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    assert mail.to_address == "ana.94a@example.com"
    assert re.search(r"é \d{6}", mail.body)
    visitor = account_situation(db, settings, None)
    assert visitor["identified"] is False
    assert visitor["assinatura"]["status"] == "unidentified"
    assert visitor["assinatura"]["status_label"] == "Identifique-se"
    assert visitor["consultas_ia"]["credits"] is None
    account, _token = verify_code(db, settings, "ana.94a@example.com", _latest_code(db), enroll_fidelity=False)
    resumed = start_resume(db, settings, "ana.94a@example.com")
    assert resumed["email_masked"]
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_entitlement",
        lambda *_a, **_k: {
            "active": True,
            "app_id": "lojadepaes",
            "entitlement": {
                "credits": 19,
                "principal_credits": 19,
                "pack_credits": 10,
                "direitos": {"biblioteca": True, "assinatura": True},
            },
            "valid_until": "2030-01-01T00:00:00Z",
        },
    )
    monkeypatch.setattr("app.domain.baker_library.access._list_subscriptions", lambda *_a, **_k: [])
    monkeypatch.setattr("app.domain.baker_library.access._fetch_catalog", lambda *_a, **_k: {"plans": []})
    situation = account_situation(db, settings, account)
    assert situation["identified"] is True
    assert situation["assinatura"]["authorized"] is True
    assert situation["consultas_ia"]["monthly_credits"] == 19
    assert situation["consultas_ia"]["pack_credits"] == 10
    assert situation["consultas_ia"]["pack_expires"] is False
    assert situation["fidelidade"]["label"] == "Fidelidade / créditos de pão"
    get_settings.cache_clear()


def test_valid_plans_event_then_duplicate_and_invalid_signature(shop_client, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.plans_webhooks.hub_plans_invoke",
        lambda *_a, **_k: {
            "active": True,
            "entitlement": {"credits": 20, "principal_credits": 20, "pack_credits": 0},
        },
    )
    token = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CONTRACT_ACTIVATED",
            "app_id": "lojadepaes",
            "outbox_id": "94a-outbox-valid",
            "iat": int(time.time()),
            "payload": {"subject_id": "ana.94a@example.com", "sku": "LOJADEPAES_BIBLIOTECA_MENSAL"},
        },
        TEST_SECRET,
    )
    first = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert first.json()["domain"] == "plans"
    second = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert second.json()["duplicate"] is True
    bad = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CONTRACT_ACTIVATED",
            "app_id": "lojadepaes",
            "outbox_id": "94a-bad",
            "payload": {"subject_id": "ana.94a@example.com"},
        },
        "wrong-secret",
    )
    assert shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": bad}).status_code in {401, 403}
    pay = shop_client.post("/api/v1/webhooks/actionhub", json={"token": token})
    assert pay.status_code == 200
    assert db.query(HubPlansEvent).filter_by(event_id="94a-outbox-valid").count() == 1
    assert db.query(Order).count() == 0


def test_plans_webhook_persists_when_hub_reconcile_fails(shop_client, db: Session, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise HubUnavailableError("ActionHub indisponível")

    monkeypatch.setattr("app.domain.baker_library.plans_webhooks.hub_plans_invoke", boom)
    token = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CREDITS_GRANTED",
            "app_id": "lojadepaes",
            "outbox_id": "94a-outbox-retry",
            "iat": int(time.time()),
            "payload": {"subject_id": "ana.94a@example.com", "sku": "LOJADEPAES_BIBLIOTECA_CREDITOS"},
        },
        TEST_SECRET,
    )
    first = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert first.status_code == 200
    row = db.query(HubPlansEvent).filter_by(event_id="94a-outbox-retry").one()
    assert row.process_status in {"applied", "received"}
    monkeypatch.setattr(
        "app.domain.baker_library.plans_webhooks.hub_plans_invoke",
        lambda *_a, **_k: {
            "active": False,
            "entitlement": {"credits": 10, "principal_credits": 0, "pack_credits": 10},
        },
    )
    again = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert again.status_code == 200
    assert again.json()["duplicate"] is True
    assert db.query(HubPlansEvent).filter_by(event_id="94a-outbox-retry").count() == 1


def test_pack_only_can_use_ai_without_subscriber_discount(monkeypatch, db: Session) -> None:
    access = {
        "identified": True,
        "authorized": False,
        "ai_credits": 10,
        "pack_credits": 10,
        "monthly_credits": 0,
        "can_use_ai": True,
    }
    assert can_use_ai(access)
    account = type("A", (), {"id": 94, "email": "avulso.94a@example.com", "name": "Avulso"})()
    monkeypatch.setattr("app.domain.baker_library.access.access_for_account", lambda *_a, **_k: access)
    quote = apply_subscriber_discount(
        db,
        get_settings(),
        {"_fidelity_account": account},
        {"subtotal_cents": 7000, "discount_cents": 0, "total_cents": 7000, "credit_applied": False},
    )
    assert quote["subscriber_discount_cents"] == 0
    monkeypatch.setattr(
        "app.domain.baker_library.access.access_for_account",
        lambda *_a, **_k: {"authorized": True, "identified": True, "subscription_status": "active"},
    )
    stacked = apply_subscriber_discount(
        db,
        get_settings(),
        {"_fidelity_account": account},
        {
            "subtotal_cents": 14000,
            "discount_cents": 7000,
            "total_cents": 7000,
            "credit_applied": True,
        },
    )
    assert stacked["subscriber_discount_cents"] == 1400
    assert stacked["fidelity_discount_cents"] == 7000
