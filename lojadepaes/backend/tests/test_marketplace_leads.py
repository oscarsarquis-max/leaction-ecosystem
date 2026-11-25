"""Leads /b2b: chave, validação, honeypot, limite, PATCH, aviso e lista admin."""

from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.marketplace.models import PartnerLead
from app.marketplace.service import hash_lead_ip
from app.models.email_outbox import EmailOutbox
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture
def leads_db(db: Session) -> Session:
    db.execute(text("TRUNCATE marketplace.partner_leads RESTART IDENTITY CASCADE"))
    db.execute(text("DELETE FROM email_outbox WHERE kind = 'partner_lead_admin'"))
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
        "terms_version": "2026-11-25",
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
    patch = admin_client.patch(
        f"/api/v1/admin/marketplace/leads/{uuid4()}",
        json={"status": "contacting"},
        headers=_csrf(csrf),
    )
    assert patch.status_code == 404


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


def test_robo_descartado_responde_201_sem_aviso(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    resp = admin_client.post(
        "/api/v1/marketplace/public/leads",
        json=_lead(website="http://spam.test"),
    )
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    leads_db.expire_all()
    assert leads_db.scalar(select(PartnerLead).limit(1)) is None
    assert leads_db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "partner_lead_admin").limit(1)) is None


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
    secret = get_settings().admin_session_secret
    assert stored.ip_hash == hash_lead_ip("testclient", secret)


def test_patch_status_valido_e_invalido(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    criado = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(brand="Patch Marca"))
    assert criado.status_code == 201
    csrf = login(admin_client)
    lista = admin_client.get("/api/v1/admin/marketplace/leads", headers=_csrf(csrf))
    lead_id = lista.json()[0]["id"]
    ok = admin_client.patch(
        f"/api/v1/admin/marketplace/leads/{lead_id}",
        json={"status": "contacting"},
        headers=_csrf(csrf),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "contacting"
    ruim = admin_client.patch(
        f"/api/v1/admin/marketplace/leads/{lead_id}",
        json={"status": "arquivado"},
        headers=_csrf(csrf),
    )
    assert ruim.status_code == 422
    del leads_db


def test_aviso_enfileirado_ao_criar(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops@loja.test")
    get_settings.cache_clear()
    brand = f"Aviso-{uuid4().hex[:6]}"
    resp = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(brand=brand))
    assert resp.status_code == 201
    leads_db.expire_all()
    row = leads_db.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.kind == "partner_lead_admin")
        .order_by(EmailOutbox.created_at.desc())
    ).first()
    assert row is not None
    assert row.subject == f"Novo interessado: {brand}"
    assert "Abrir na Gestão: https://lojadepaes.com.br/admin/interessados" in row.body
    assert brand in row.body


def test_falha_no_banco_do_aviso_mantem_interessado(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)

    def _boom(*_args, **_kwargs):
        raise IntegrityError("INSERT INTO email_outbox", {}, Exception("ck"))

    monkeypatch.setattr("app.marketplace.service.enqueue_partner_lead_notice", _boom)
    brand = f"Falha-{uuid4().hex[:6]}"
    resp = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(brand=brand))
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    leads_db.expire_all()
    stored = leads_db.scalars(select(PartnerLead).where(PartnerLead.brand == brand)).first()
    assert stored is not None
    assert (
        leads_db.scalar(
            select(EmailOutbox).where(EmailOutbox.kind == "partner_lead_admin", EmailOutbox.subject.contains(brand))
        )
        is None
    )


def test_assunto_sem_quebra_de_linha(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops@loja.test")
    get_settings.cache_clear()
    brand = "Queijos\r\nBcc: evil@x.test"
    resp = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(brand=brand))
    assert resp.status_code == 201
    leads_db.expire_all()
    row = leads_db.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.kind == "partner_lead_admin")
        .order_by(EmailOutbox.created_at.desc())
    ).first()
    assert row is not None
    assert "\n" not in row.subject
    assert "\r" not in row.subject
    assert row.subject == "Novo interessado: Queijos Bcc: evil@x.test"
    assert row.subject.count("Novo interessado:") == 1


def test_termos_ausentes_422_e_versao_errada_409(leads_db: Session, admin_client: TestClient, monkeypatch):
    del leads_db
    _ligar_leads(monkeypatch, True)
    sem = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(terms_version=None))
    assert sem.status_code == 422
    assert sem.json()["detail"] == "Para enviar, aceite os termos de parceria."
    vazio = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(terms_version=""))
    assert vazio.status_code == 422
    errada = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(terms_version="2020-01-01"))
    assert errada.status_code == 409
    assert errada.json()["detail"] == "Os termos mudaram. Recarregue a página."


def test_termos_gravados_e_listagem(leads_db: Session, admin_client: TestClient, monkeypatch):
    _ligar_leads(monkeypatch, True)
    brand = f"Termos-{uuid4().hex[:6]}"
    resp = admin_client.post("/api/v1/marketplace/public/leads", json=_lead(brand=brand))
    assert resp.status_code == 201
    leads_db.expire_all()
    stored = leads_db.scalars(select(PartnerLead).where(PartnerLead.brand == brand)).one()
    assert stored.terms_version == "2026-11-25"
    assert stored.terms_accepted_at is not None
    csrf = login(admin_client)
    lista = admin_client.get("/api/v1/admin/marketplace/leads", headers=_csrf(csrf))
    assert lista.status_code == 200
    item = next(row for row in lista.json() if row["brand"] == brand)
    assert item["terms_version"] == "2026-11-25"
    assert item["terms_accepted_at"]
    assert item["terms_accepted_at"].startswith(stored.terms_accepted_at.date().isoformat())


def test_migracao_b2b3_desce_e_sobe(test_engine, leads_db: Session):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    del leads_db
    ini = Path(__file__).resolve().parents[2] / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    revision = "f7c2e9a14b60"
    try:
        command.downgrade(config, "d8b3f1a65c92")
        cols = {col["name"] for col in inspect(test_engine).get_columns("partner_leads", schema="marketplace")}
        assert "terms_version" not in cols
        assert "terms_accepted_at" not in cols
    finally:
        command.upgrade(config, "head")
    cols = {col["name"] for col in inspect(test_engine).get_columns("partner_leads", schema="marketplace")}
    assert {"terms_version", "terms_accepted_at"} <= cols
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == revision
