import base64
import hashlib
import hmac
import json
import time
from collections.abc import Iterator

import httpx
import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.baker_library.access import (
    CYCLE_RULES,
    can_use_ai,
    public_plan,
    start_subscription_checkout,
)
from app.domain.baker_library.credits import reserve_credit
from app.domain.baker_library.hub_plans import invoke as hub_plans_invoke
from app.domain.actionhub_client import request_amount_checkout
from app.main import create_app
from app.models.baker_library import HubPlansEvent
from app.models.orders import Order
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _sign(payload: dict, secret: str) -> str:
    def b64(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64({"alg": "HS256", "typ": "JWT"})
    body = b64(payload)
    signature = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def test_cycle_rules_pack_is_cumulative_and_independent() -> None:
    notes = " ".join(CYCLE_RULES["notes"])
    assert CYCLE_RULES["accumulate"] is False
    assert CYCLE_RULES["pack_accumulate"] is True
    assert CYCLE_RULES["pack_expires"] is False
    assert CYCLE_RULES["pack_requires_principal"] is False
    assert "cumulativo" in notes
    assert "não expira" in notes
    assert "não exige assinatura vigente" in notes
    assert "R$ 10,00 / mês" not in notes


def test_can_use_ai_allows_pack_only_without_subscription() -> None:
    assert can_use_ai({"identified": True, "authorized": False, "ai_credits": 10, "pack_credits": 10})
    assert can_use_ai({"identified": True, "can_use_ai": True, "ai_credits": 1})
    assert not can_use_ai({"identified": True, "authorized": False, "ai_credits": 0})
    assert not can_use_ai({"identified": True, "authorized": True, "balance_source": "unavailable"})
    assert not can_use_ai({"identified": False, "authorized": False})


def test_hub_plans_uses_catalog_and_credits_not_amount_checkout(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "plans-secret")
    get_settings.cache_clear()
    settings = get_settings()
    captured: dict = {}

    class Response:
        status_code = 200
        content = b"{}"

        def json(self):
            return {"app_id": "lojadepaes", "plans": []}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        assert "/v1/checkout/amount" not in url
        assert "/v1/satellites" not in url
        return Response()

    monkeypatch.setattr("app.domain.baker_library.hub_plans.httpx.request", fake_request)
    payload = hub_plans_invoke(
        settings,
        "LIST_HUB_CATALOG",
        {},
        correlation_id="plans-catalog",
        idempotency_key="catalog:lojadepaes",
    )
    assert payload["app_id"] == "lojadepaes"
    assert captured["url"].endswith("/v1/catalog/lojadepaes")
    assert captured["headers"]["Authorization"] == "Bearer plans-secret"
    get_settings.cache_clear()


@pytest.fixture
def shop_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "loja-test-secret")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_access_catalog_goes_through_hub_plans_not_spider(monkeypatch) -> None:
    import app.domain.baker_library.access as access_mod

    called = {"hub": 0, "spider": 0}

    def hub(*_a, **_k):
        called["hub"] += 1
        return {"plans": []}

    def spider(*_a, **_k):
        called["spider"] += 1
        raise AssertionError("planos não podem passar pela Spider nesta etapa")

    monkeypatch.setattr(access_mod, "hub_plans_invoke", hub)
    monkeypatch.setattr("app.domain.baker_library.spider.invoke", spider)

    def real_fetch(settings):
        return access_mod.hub_plans_invoke(
            settings,
            "LIST_HUB_CATALOG",
            {},
            correlation_id="loja-catalog-test",
            idempotency_key="catalog:test",
        )

    monkeypatch.setattr(access_mod, "_fetch_catalog", real_fetch)
    plan = public_plan(get_settings())
    assert plan["source"] == "hub"
    assert called["hub"] == 1
    assert called["spider"] == 0
    source = open(access_mod.__file__, encoding="utf-8").read()
    assert "hub_plans_invoke" in source
    assert "spider_invoke" not in source


def test_checkout_and_reserve_keep_same_capability_ids(monkeypatch) -> None:
    import app.domain.baker_library.credits as credits_mod

    seen: list[str] = []

    def fake(settings, capability, inputs, **_k):
        seen.append(capability)
        if capability == "START_HUB_CATALOG_CHECKOUT":
            return {
                "checkout_url": "https://actionhub.com.br/checkout/x",
                "order_id": "ord-1",
                "sku": inputs["sku"],
                "checkout_mode": "subscription",
                "amount": 19,
                "currency": "BRL",
            }
        if capability == "RESERVE_HUB_CREDITS":
            return {"ok": True, "status": "reserved", "credits": 19}
        return {}

    monkeypatch.setattr("app.domain.baker_library.access.hub_plans_invoke", fake)
    monkeypatch.setattr(credits_mod, "hub_plans_invoke", fake)

    def real_call(settings, action, email, operation_id, *, amount=None):
        return credits_mod._call.__wrapped__(settings, action, email, operation_id, amount=amount) if hasattr(credits_mod._call, "__wrapped__") else _real_credit_call(settings, action, email, operation_id, amount=amount, invoke=fake)

    def _real_credit_call(settings, action, email, operation_id, *, amount=None, invoke=fake):
        capability = {
            "reserve": "RESERVE_HUB_CREDITS",
            "confirm": "CONFIRM_HUB_CREDITS",
            "release": "RELEASE_HUB_CREDITS",
        }[action]
        inputs = {"subject_id": email, "operation_id": operation_id}
        if amount is not None:
            inputs["amount"] = amount
        return invoke(settings, capability, inputs)

    monkeypatch.setattr(credits_mod, "_call", lambda settings, action, email, operation_id, amount=None: _real_credit_call(settings, action, email, operation_id, amount=amount))
    monkeypatch.setattr(
        "app.domain.baker_library.access.public_plan",
        lambda _s: {
            "configured": True,
            "checkout_ready": True,
            "sku": "LOJADEPAES_BIBLIOTECA_MENSAL",
            "principal": {"sku": "LOJADEPAES_BIBLIOTECA_MENSAL", "checkout_ready": True},
            "pack": {"sku": "LOJADEPAES_BIBLIOTECA_CREDITOS", "checkout_ready": True},
            "price": 19,
        },
    )
    account = type("A", (), {"id": "acc-1", "email": "ana@example.com"})()
    start_subscription_checkout(None, get_settings(), account, return_to="/#biblioteca")
    reserve_credit(get_settings(), account, "op-1")
    assert seen == ["START_HUB_CATALOG_CHECKOUT", "RESERVE_HUB_CREDITS"]


def test_pay_amount_checkout_helper_still_exists() -> None:
    assert request_amount_checkout.__module__ == "app.domain.actionhub_client"


def test_plans_webhook_isolated_from_pay(shop_client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.plans_webhooks.hub_plans_invoke",
        lambda *_a, **_k: {"active": False, "reason": "pack_only", "entitlement": {"credits": 10, "pack_credits": 10}},
    )
    token = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CREDITS_GRANTED",
            "app_id": "lojadepaes",
            "outbox_id": "plans-outbox-1",
            "iat": int(time.time()),
            "payload": {
                "subject_id": "ana@example.com",
                "sku": "LOJADEPAES_BIBLIOTECA_CREDITOS",
                "credits_added": 10,
            },
        },
        "loja-test-secret",
    )
    first = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert first.status_code == 200, first.text
    assert first.json()["domain"] == "plans"
    assert first.json()["duplicate"] is False
    second = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": token})
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert db.query(HubPlansEvent).count() == 1
    assert db.query(Order).count() == 0


def test_plans_webhook_rejects_bad_signature_and_wrong_app(shop_client: TestClient) -> None:
    bad = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CREDITS_GRANTED",
            "app_id": "lojadepaes",
            "outbox_id": "plans-bad",
            "payload": {"subject_id": "ana@example.com"},
        },
        "wrong-secret",
    )
    assert shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": bad}).status_code in {401, 403}
    other = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CREDITS_GRANTED",
            "app_id": "inove4us",
            "outbox_id": "plans-other",
            "payload": {"subject_id": "ana@example.com"},
        },
        "loja-test-secret",
    )
    assert shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": other}).status_code in {401, 403}


def test_pay_webhook_still_ignores_plans_event(shop_client: TestClient, db: Session) -> None:
    token = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "CREDITS_GRANTED",
            "app_id": "lojadepaes",
            "outbox_id": "pay-should-ignore-plans",
            "payload": {"subject_id": "ana@example.com", "credits_added": 10},
        },
        "loja-test-secret",
    )
    hooked = shop_client.post("/api/v1/webhooks/actionhub", json={"token": token})
    assert hooked.status_code == 200
    assert hooked.json()["process_status"] in {"ignored", "received"}
    assert db.query(HubPlansEvent).count() == 0
    assert db.query(Order).count() == 0


def test_stale_plans_event_does_not_override_newer(shop_client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.plans_webhooks.hub_plans_invoke",
        lambda *_a, **_k: {"active": True, "entitlement": {"credits": 20, "principal_credits": 20}},
    )
    now = int(time.time())
    newer = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "SUBSCRIPTION_STATUS",
            "app_id": "lojadepaes",
            "outbox_id": "plans-new",
            "iat": now,
            "payload": {"subject_id": "ana@example.com", "status": "cancelled"},
        },
        "loja-test-secret",
    )
    older = _sign(
        {
            "iss": "leaction-hub",
            "event_type": "SUBSCRIPTION_STATUS",
            "app_id": "lojadepaes",
            "outbox_id": "plans-old",
            "iat": now - 3600,
            "payload": {"subject_id": "ana@example.com", "status": "authorized"},
        },
        "loja-test-secret",
    )
    assert shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": newer}).status_code == 200
    late = shop_client.post("/api/v1/webhooks/actionhub/plans", json={"token": older})
    assert late.status_code == 200
    assert late.json()["process_status"] == "ignored_stale"


def test_hub_timeout_is_uncertain_not_cancelled(monkeypatch) -> None:
    def timeout(*_a, **_k):
        raise httpx.TimeoutException("slow")

    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "plans-secret")
    get_settings.cache_clear()
    monkeypatch.setattr("app.domain.baker_library.hub_plans.httpx.request", timeout)
    from app.domain.actionhub_client import HubUnavailableError

    try:
        hub_plans_invoke(
            get_settings(),
            "GET_HUB_ENTITLEMENTS",
            {"subject_id": "ana@example.com"},
            correlation_id="timeout-ent",
            idempotency_key="ent:timeout",
        )
        raise AssertionError("timeout deveria ser incerto")
    except HubUnavailableError as exc:
        assert "timeout" in str(exc)
    get_settings.cache_clear()
