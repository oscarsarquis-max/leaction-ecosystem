import re
from collections.abc import Iterator
from datetime import datetime

import pytest
from app.core.config import Settings, get_settings
from app.db.session import reset_engine
from app.domain.bakery_time import bakery_zone
from app.domain.house_fidelity import next_cycle_start, parse_demo_state, status_payload
from app.main import create_app
from app.models.email_outbox import EmailOutbox
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_SESSION_SECRET

SECRET = TEST_SESSION_SECRET


@pytest.fixture
def fidelity_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", SECRET)
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "false")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_public_status_never_activates_or_exposes_demo(fidelity_client: TestClient) -> None:
    body = fidelity_client.get("/api/v1/promotions/house-fidelity?demo=credit").json()
    assert body["campaign_active"] is False
    assert body["preview"] is False
    assert body["stamps"] == "neutral"
    assert body["participant"] is None
    assert "pending_criteria" not in body or not body.get("pending_criteria")
    assert "1º de" in body["restart_label"]
    assert "500 g" in body["how_it_works"]
    assert "fechada e paga" in body["how_it_works"]
    assert "não entram depois" in body["how_it_works"]
    assert "Frete" in body["benefit"]


def test_signup_sends_code_without_confirming(fidelity_client: TestClient, db: Session) -> None:
    denied = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "Ana", "email": "ana@example.com"},
    )
    assert denied.status_code == 422

    created = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "Ana", "email": "ana@example.com", "cpf": "390.533.447-05"},
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["ok"] is True
    assert payload["needs_verification"] is True
    assert "cpf" not in payload
    assert "Se este cadastro puder ser confirmado" in payload["message"]
    mail = db.query(EmailOutbox).filter_by(kind="customer_verify").one()
    assert "390" not in mail.body
    assert re.search(r"é \d{6}", mail.body)

    resume_denied = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/resume",
        json={"email": "ana@example.com", "cpf": "39053344705"},
    )
    assert resume_denied.status_code == 422

    resumed = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/resume",
        json={"email": "desconhecida@example.com"},
    )
    assert resumed.status_code == 200
    assert "não abre saldo" in resumed.json()["message"]


def test_verify_session_hides_third_party(fidelity_client: TestClient, db: Session) -> None:
    first = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "Ana", "email": "ana@example.com", "cpf": "390.533.447-05"},
    )
    assert first.status_code == 200
    mail = db.query(EmailOutbox).filter_by(to_address="ana@example.com").order_by(EmailOutbox.created_at.desc()).first()
    code = re.search(r"é (\d{6})", mail.body).group(1)
    verified = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/verify",
        json={"email": "ana@example.com", "code": code},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["verified"] is True
    assert verified.json()["cpf_masked"].endswith("-05")
    me = fidelity_client.get("/api/v1/promotions/house-fidelity/me")
    assert me.status_code == 200
    fidelity_client.post("/api/v1/promotions/house-fidelity/logout")
    denied = fidelity_client.get("/api/v1/promotions/house-fidelity/me")
    assert denied.status_code == 401

    fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "Bia", "email": "bia@example.com", "cpf": "529.982.247-25"},
    )
    other = db.query(EmailOutbox).filter_by(to_address="bia@example.com").order_by(EmailOutbox.created_at.desc()).first()
    other_code = re.search(r"é (\d{6})", other.body).group(1)
    fidelity_client.post(
        "/api/v1/promotions/house-fidelity/verify",
        json={"email": "bia@example.com", "code": other_code},
    )
    leaked = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "X", "email": "x@example.com", "cpf": "390.533.447-05"},
    )
    assert leaked.json()["message"].startswith("Se este cadastro")
    assert "ana@" not in leaked.text


def test_preview_only_returns_demonstrative_progress(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert parse_demo_state("credit", preview=False) == "visitor"
    public = status_payload(db, Settings(preview_protection=False), demo="credit")
    assert public["participant"] is None
    preview = status_payload(db, settings, demo="partial")
    assert preview["preview"] is True
    assert preview["campaign_active"] is False
    assert preview["participant"]["valid_orders"] == 2
    assert preview["participant"]["credits"] == 0
    credit = status_payload(db, settings, demo="credit")
    assert credit["participant"]["credits"] == 1
    get_settings.cache_clear()


def test_invalid_code_keeps_purchase_available(fidelity_client: TestClient, db: Session) -> None:
    created = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/signup",
        json={"name": "Ana", "email": "ana@example.com", "cpf": "390.533.447-05"},
    )
    assert created.status_code == 200
    failed = fidelity_client.post(
        "/api/v1/promotions/house-fidelity/verify",
        json={"email": "ana@example.com", "code": "000000"},
    )
    assert failed.status_code in {400, 409, 422}
    assert fidelity_client.get("/api/v1/promotions/house-fidelity/me").status_code == 401
    assert fidelity_client.get("/api/v1/catalog/showcase").status_code == 200


def test_cycle_restarts_on_first_of_next_month() -> None:
    settings = Settings(bakery_timezone="America/Sao_Paulo")
    zone = bakery_zone(settings)
    restart = next_cycle_start(settings, datetime(2026, 9, 28, 15, 0, tzinfo=zone))
    assert restart == datetime(2026, 10, 1, 0, 0, tzinfo=zone)
    december = next_cycle_start(settings, datetime(2026, 12, 31, 23, 30, tzinfo=zone))
    assert december == datetime(2027, 1, 1, 0, 0, tzinfo=zone)
