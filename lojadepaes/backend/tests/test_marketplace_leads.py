"""Leads /b2b: chave independente, validação, honeypot, limite por IP e lista admin."""

from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.marketplace.models import PartnerLead
from app.marketplace.service import hash_lead_ip
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture
def leads_db(db: Session) -> Session:
    db.execute(text("TRUNCATE marketplace.partner_leads RESTART IDENTITY CASCADE"))
    db.commit()
    return db


def _ligar_leads(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setenv("LOJADEPAES_MARKETPLACE_LEADS_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("LOJADEPAES_MARKETPLACE_ENABLED", "false")
    get_settings.cache_clear()


def _csrf(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def _lead(**extra) -> dict:
    body = {
        "name": "Ana Produtora",
        "brand": "Queijos do Vale",
        "category": "queijos",
        "city": "Fortaleza",
        "whatsapp": "85999887766",
        "email": f"ana-{uuid4().hex[:8]}@vale.test",
        "link": "https://instagram.com/queijos",
        "message": "Produzo queijo coalho artesanal na serra.",
        "consent": True,
        "website": "",
    }
    body.update(extra)
    return body


def test_chave_leads_desligada_responde_404(leads_db: Session, admin_client: TestClient, monkeypatch):
    del leads_db
    _ligar_leads(monkeypatch, False)
    post = admin_client.post("/api/v1/marketplace/public/leads", json=_lead())
    assert post.status_code == 404
    csrf = login(admin_client)
    lista = admin_client.get("/api/v1/admin/marketplace/leads", headers=_csrf(csrf))
    assert lista.status_code == 404


def test_validacao_recusa_campos_invalidos(leads_db: Session, admin_client: TestClient, monkeypatch):
    del leads_db
    _ligar_leads(monkeypatch, True)
    sem_consent = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(consent=False))
    assert sem_consent.status_code == 422
    whats = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(whatsapp="123"))
    assert whats.status_code == 422
    email = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(email="nao-email"))
    assert email.status_code == 422
    cat = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(category="pao"))
    assert cat.status_code == 422
    longo = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(name="x" * 121))
    assert longo.status_code == 422


def test_robo_descartado_responde_201(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    resp = admin_client.post(
        "/api/v1/marketplace/public/leads",
        json=_lead(website="http://spam.test"),
    )
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    leads_db.expire_all()
    assert leads_db.scalar(select(PartnerLead).limit(1)) is None


def test_limite_por_ip(leads_db: Session, admin_client: TestClient, monkeypatch):
    del leads_db
    _ligar_leads(monkeypatch, True)
    for i in range(5):
        ok = admin_client.post(
            "/api/v1/marketplace/public/leads",
            json=_lead(email=f"ip-{i}-{uuid4().hex[:6]}@vale.test"),
        )
        assert ok.status_code == 201, ok.text
    bloqueado = admin_client.post(
        "/api/v1/marketplace/public/leads",
        json=_lead(email=f"ip-extra-{uuid4().hex[:6]}@vale.test"),
    )
    assert bloqueado.status_code == 429


def test_admin_lista_mais_recentes(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    primeiro = admin_client.post(
        "/api/v1/marketplace/public/leads",
        json=_lead(brand="Marca A", email=f"a-{uuid4().hex[:6]}@vale.test"),
    )
    assert primeiro.status_code == 201
    segundo = admin_client.post(
        "/api/v1/marketplace/public/leads",
        json=_lead(brand="Marca B", email=f"b-{uuid4().hex[:6]}@vale.test"),
    )
    assert segundo.status_code == 201
    csrf = login(admin_client)
    lista = admin_client.get("/api/v1/admin/marketplace/leads", headers=_csrf(csrf))
    assert lista.status_code == 200, lista.text
    items = lista.json()
    assert len(items) >= 2
    assert items[0]["brand"] == "Marca B"
    assert items[1]["brand"] == "Marca A"
    assert "ip_hash" not in items[0]
    leads_db.expire_all()
    stored = leads_db.scalars(select(PartnerLead)).first()
    assert stored is not None
    assert stored.ip_hash == hash_lead_ip("testclient")
