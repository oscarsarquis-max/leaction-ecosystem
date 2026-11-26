"""BLOG-025 — rotas de integração fidelidade/vitrine (sem telefone nos logs)."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.domain.house_fidelity import CAMPAIGN_SLUG
from app.domain.integracoes_lepain import cliente_status, credit_stamp, list_vitrine
from app.models.house_fidelity import HouseFidelityEnrollment, HouseFidelityEvent
from app.models.orders import Order
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.test_house_fidelity_ledger import _account, _campaign, _order, _product, _settings


def _enroll(db: Session, account, campaign) -> None:
    db.add(
        HouseFidelityEnrollment(
            account_id=account.id,
            campaign_id=campaign.id,
            rules_version=campaign.rules_version,
            enrolled_at=datetime.now(UTC),
        )
    )
    db.flush()


def _phone_order(db: Session, account, campaign, variant, phone: str) -> Order:
    order = _order(db, account, campaign, variant)
    order.customer_phone = phone
    order.fidelity_account_id = account.id
    order.fidelity_opt_in = True
    db.flush()
    return order


def test_cliente_ausente(db: Session):
    settings = _settings()
    _campaign(db)
    out = cliente_status(db, settings, "11999990000")
    assert out == {"cliente": False, "pontos": 0, "total": 0}


def test_cliente_e_carimbo_idempotente(db: Session):
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    _enroll(db, account, campaign)
    _phone_order(db, account, campaign, variant, "11987654321")

    first = cliente_status(db, settings, "(11) 98765-4321")
    assert first["cliente"] is True
    assert first["pontos"] == 0

    a = credit_stamp(db, settings, telefone="11987654321", referencia="lepain-receita-1")
    assert a["creditado"] is True
    assert a["pontos"] == 1

    b = credit_stamp(db, settings, telefone="11987654321", referencia="lepain-receita-1")
    assert b["creditado"] is False
    assert b["pontos"] == 1

    events = list(
        db.scalars(
            select(HouseFidelityEvent).where(HouseFidelityEvent.actor_ref == "lepain-receita-1")
        )
    )
    assert len(events) == 1
    assert events[0].kind == "qualify"


def test_vitrine_lista_ativos(db: Session):
    _product(db)
    items = list_vitrine(db)
    assert items
    assert {"id", "nome", "url"} <= set(items[0].keys())
    assert "/paes/" in items[0]["url"]


def test_api_exige_chave(client, monkeypatch):
    monkeypatch.setenv("LOJADEPAES_INTEGRACOES_SERVICE_KEY", "teste-chave-025")
    from app.core.config import get_settings

    get_settings.cache_clear()
    denied = client.get("/api/v1/integracoes/fidelidade/cliente", params={"telefone": "11999990000"})
    assert denied.status_code == 401
    ok = client.get(
        "/api/v1/integracoes/fidelidade/cliente",
        params={"telefone": "11999990000"},
        headers={"X-Service-Key": "teste-chave-025"},
    )
    assert ok.status_code == 200
    assert ok.json()["cliente"] is False
    get_settings.cache_clear()
