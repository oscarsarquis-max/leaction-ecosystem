import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.house_fidelity_ledger import reconcile_order
from app.main import create_app
from app.models.customers import CustomerAccount
from app.models.email_outbox import EmailOutbox
from app.models.house_fidelity import HouseFidelityCredit, HouseFidelityEvent
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_USER, TEST_SESSION_SECRET, login
from tests.test_house_fidelity_ledger import (
    _account,
    _campaign,
    _close,
    _order,
    _pay,
    _product,
    _settings,
)
from tests.test_storefront import _next_wednesday
from tests.test_storefront import _product as _shop_product


@pytest.fixture
def fidelity_shop(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    from tests.admin_client import TEST_ADMIN_HASH

    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def _available_credit(db: Session, campaign, account, *, group_index: int = 0, status: str = "available"):
    event = HouseFidelityEvent(
        campaign_id=campaign.id,
        account_id=account.id,
        kind="manual_grant",
        status="applied",
        cycle_year=2026,
        cycle_month=9,
        eligible_at=datetime.now(UTC),
        reason="fixture",
    )
    db.add(event)
    db.flush()
    credit = HouseFidelityCredit(
        campaign_id=campaign.id,
        account_id=account.id,
        source_event_id=event.id,
        cycle_year=2026,
        cycle_month=9,
        group_index=group_index,
        status=status,
    )
    db.add(credit)
    db.flush()
    return credit


def _verify(client: TestClient, db: Session, name: str, email: str, cpf: str) -> None:
    created = client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": name, "email": email, "cpf": cpf},
    )
    assert created.status_code == 200, created.text
    mail = (
        db.query(EmailOutbox)
        .filter_by(to_address=email)
        .order_by(EmailOutbox.created_at.desc())
        .first()
    )
    code = re.search(r"é (\d{6})", mail.body).group(1)
    verified = client.post(
        "/api/v1/promotions/house-fidelity/verify",
        json={"email": email, "code": code},
    )
    assert verified.status_code == 200, verified.text


def test_fourth_order_grants_credit_without_admin(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(4):
        order = _order(db, account, campaign, variant)
        _pay(db, order)
        _close(db, order)
        reconcile_order(db, settings, order)
    credits = list(
        db.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.account_id == account.id,
                HouseFidelityCredit.status == "available",
            )
        )
    )
    assert len(credits) == 1
    reconcile_order(db, settings, order)
    assert (
        db.scalar(
            select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id)
        )
        is not None
    )
    assert (
        len(
            list(
                db.scalars(
                    select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id)
                )
            )
        )
        == 1
    )


def test_signup_alone_does_not_grant_credit(fidelity_shop: TestClient, db: Session) -> None:
    _campaign(db)
    db.commit()
    _verify(fidelity_shop, db, "Ana", "ana-cadastro@example.com", "390.533.447-05")
    me = fidelity_shop.get("/api/v1/promotions/house-fidelity/me")
    assert me.status_code == 200
    participant = me.json().get("participant")
    assert participant is not None
    assert participant["credits"] == 0
    assert db.scalar(select(HouseFidelityCredit)) is None


def test_manual_grant_works_with_zero_orders_and_reason(fidelity_shop: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    account = _account(db)
    db.commit()
    csrf = login(fidelity_shop)
    missing = fidelity_shop.post(
        "/api/v1/promotions/house-fidelity/admin/adjust",
        json={"account_id": str(account.id), "kind": "grant", "reason": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert missing.status_code == 422
    short = fidelity_shop.post(
        "/api/v1/promotions/house-fidelity/admin/adjust",
        json={"account_id": str(account.id), "kind": "grant", "reason": "ab"},
        headers={"X-CSRF-Token": csrf},
    )
    assert short.status_code == 422
    assert "informe por que" in short.json()["detail"]
    assert db.scalar(select(HouseFidelityCredit)) is None
    granted = fidelity_shop.post(
        "/api/v1/promotions/house-fidelity/admin/adjust",
        json={"account_id": str(account.id), "kind": "grant", "reason": "cortesia de aniversário"},
        headers={"X-CSRF-Token": csrf},
    )
    assert granted.status_code == 200, granted.text
    credit = db.scalar(select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id))
    assert credit is not None
    assert credit.status == "available"
    used = _available_credit(db, campaign, account, group_index=1, status="used")
    db.commit()
    blocked = fidelity_shop.post(
        "/api/v1/promotions/house-fidelity/admin/adjust",
        json={
            "account_id": str(account.id),
            "kind": "reverse",
            "reason": "tentativa sobre crédito usado",
            "credit_id": str(used.id),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert blocked.status_code == 422
    assert "já usado" in blocked.json()["detail"]
    assert db.get(HouseFidelityCredit, used.id).status == "used"


def test_admin_search_rejects_cpf_and_lists_month_orders(fidelity_shop: TestClient, db: Session) -> None:
    _campaign(db)
    account = _account(db)
    account.name = "Ana Silva"
    account.email = "ana-lista@example.com"
    db.commit()
    csrf = login(fidelity_shop)
    listed = fidelity_shop.get(
        "/api/v1/promotions/house-fidelity/admin/participants?q=Ana",
        headers={"X-CSRF-Token": csrf},
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["valid_orders"] == 0
    blocked = fidelity_shop.get(
        "/api/v1/promotions/house-fidelity/admin/participants?q=39053344705",
        headers={"X-CSRF-Token": csrf},
    )
    assert blocked.status_code == 200
    assert blocked.json()["items"] == []
    assert "CPF" in blocked.json()["search_note"]


def test_checkout_credit_is_optional_and_server_priced(fidelity_shop: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    variant = _shop_product(db)
    extra = _product(db)
    extra.price_cents = 2890
    _verify(fidelity_shop, db, "Ana", "ana-checkout@example.com", "390.533.447-05")
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.email == "ana-checkout@example.com"))
    _available_credit(db, campaign, account)
    db.commit()
    day = _next_wednesday()
    items = [{"variant_id": str(variant.id), "quantity": 2}]
    saved = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={"requested_date": day, "items": items, "apply_fidelity_credit": False},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["total_cents"] == 4980
    assert saved.json()["discount_cents"] == 0
    assert saved.json()["credit_applied"] is False
    guest = TestClient(create_app())
    leaked = guest.post(
        "/api/v1/storefront/quote",
        json={"requested_date": day, "items": items, "apply_fidelity_credit": True},
    )
    assert leaked.status_code == 200
    assert leaked.json()["discount_cents"] == 0
    assert "Identifique-se" in leaked.json()["credit_notice"]
    applied = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={
            "requested_date": day,
            "items": items,
            "apply_fidelity_credit": True,
        },
    )
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["subtotal_cents"] == 4980
    assert body["discount_cents"] == 2490
    assert body["total_cents"] == 2490
    assert body["credit_applied"] is True
    many = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={
            "requested_date": day,
            "items": [
                {"variant_id": str(variant.id), "quantity": 1},
                {"variant_id": str(extra.id), "quantity": 1},
            ],
            "apply_fidelity_credit": True,
        },
    )
    assert many.status_code == 200
    assert many.json()["credit_applied"] is False
    assert "Escolha qual pão" in many.json()["credit_notice"]
    chosen = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={
            "requested_date": day,
            "items": [
                {"variant_id": str(variant.id), "quantity": 1},
                {"variant_id": str(extra.id), "quantity": 1},
            ],
            "apply_fidelity_credit": True,
            "fidelity_variant_id": str(extra.id),
        },
    )
    assert chosen.json()["discount_cents"] == 2890
    assert chosen.json()["total_cents"] == 2490
    submitted = fidelity_shop.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 0,
            "customer_name": "Ana",
            "customer_email": "ana-checkout@example.com",
            "idempotency_key": f"credit-{uuid4().hex}",
            "apply_fidelity_credit": True,
            "fidelity_variant_id": str(variant.id),
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["total_cents"] == 0
    assert "Sem valor a pagar" in submitted.json()["notice"]
    assert submitted.json()["payment_available"] is False
    order_id = db.scalar(select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id)).reserved_order_id
    assert order_id is not None
    assert db.scalar(select(PaymentRecord).where(PaymentRecord.order_id == order_id)) is None
    again_quote = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={
            "requested_date": day,
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "apply_fidelity_credit": True,
            "fidelity_variant_id": str(variant.id),
        },
    )
    assert again_quote.status_code == 200
    assert again_quote.json()["credit_applied"] is False
    assert again_quote.json()["total_cents"] == 2490
    assert "não há crédito" in (again_quote.json().get("credit_notice") or "").lower()
    again = fidelity_shop.post(
        "/api/v1/storefront/orders",
        json={
            "requested_date": day,
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
            "quoted_cents": 0,
            "customer_name": "Ana",
            "customer_email": "ana-checkout@example.com",
            "idempotency_key": f"credit-dup-{uuid4().hex}",
            "apply_fidelity_credit": True,
            "fidelity_variant_id": str(variant.id),
        },
    )
    assert again.status_code == 409
    assert db.scalar(
        select(HouseFidelityCredit).where(
            HouseFidelityCredit.account_id == account.id,
            HouseFidelityCredit.status == "available",
        )
    ) is None


def test_quote_without_session_does_not_reveal_balance(fidelity_shop: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    account = _account(db)
    variant = _shop_product(db)
    _available_credit(db, campaign, account)
    db.commit()
    quoted = fidelity_shop.post(
        "/api/v1/storefront/quote",
        json={
            "requested_date": _next_wednesday(),
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert quoted.status_code == 200
    text = quoted.text
    assert "crédito disponível" not in text.lower() or quoted.json()["discount_cents"] == 0
    assert quoted.json()["credit_applied"] is False
    status = fidelity_shop.get("/api/v1/promotions/house-fidelity")
    assert status.json()["participant"] is None
