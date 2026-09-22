import json
from uuid import uuid4

import httpx
import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.crm_tracking import build_hub_body, emit_order_fact, sanitize_dados
from app.domain.orders import confirm_order
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.db_fixtures import draft_order, priced_catalog
from tests.test_storefront import _next_wednesday, _product

SESSION = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def tracking_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    del db
    monkeypatch.setenv("LOJADEPAES_CRM_TRACKING_SECRET", "segredo-teste")
    monkeypatch.setenv("LOJADEPAES_CRM_TRACKING_SYNC", "1")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "loja-test-secret")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def test_dados_nao_levam_pessoa_nem_valor() -> None:
    cleaned = sanitize_dados(
        {
            "pagina": "/paes/limao",
            "data_fornada": "2026-09-23",
            "quantidade": 2,
            "email": "ana@padaria.com",
            "telefone": "11999999999",
            "pix": "00020126",
            "valor": 2490,
            "customer_name": "Ana",
            "endereco": "Rua das Flores",
        }
    )
    assert cleaned == {"pagina": "/paes/limao", "data_fornada": "2026-09-23", "quantidade": 2}
    body = build_hub_body(
        id_sessao=SESSION,
        tipo_evento="pedido_enviar",
        id_usuario="ana@padaria.com",
        dados={"pedido_id": str(uuid4()), "situacao": "submitted", "total_cents": 2490},
    )
    assert body is not None
    assert "id_usuario" not in body
    assert "instituicao_id" not in body
    assert body["sistema_origem"] == "lojadepaes"
    assert body["dados"]["situacao"] == "submitted"
    assert "total_cents" not in body["dados"]


def test_proxy_nao_espera_o_hub(tracking_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("hub fora")

    monkeypatch.setattr("app.domain.crm_tracking.httpx.post", boom)
    response = tracking_client.post(
        "/api/tracking/enviar",
        json={
            "id_sessao": SESSION,
            "tipo_evento": "pageview",
            "id_usuario": "ana@padaria.com",
            "instituicao_id": "11111111-1111-4111-8111-111111111111",
            "dados": {"pagina": "/", "email": "ana@padaria.com"},
        },
    )
    assert response.status_code == 202
    assert response.json()["ok"] is True


def test_pedido_guarda_sessao_e_hub_fora_nao_impede_envio(
    tracking_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict] = []

    def record(*_args, **kwargs):
        sent.append(kwargs["json"])

        class Response:
            status_code = 201

        return Response()

    monkeypatch.setattr("app.domain.crm_tracking.httpx.post", record)
    variant = _product(db)
    db.commit()
    day = _next_wednesday()
    payload = {
        "requested_date": day,
        "items": [{"variant_id": str(variant.id), "quantity": 1}],
        "quoted_cents": 2490,
        "customer_name": "Ana",
        "customer_email": "ana@padaria.com",
        "idempotency_key": "crm-submit-1",
        "id_sessao": SESSION,
    }
    first = tracking_client.post("/api/v1/storefront/orders", json=payload)
    second = tracking_client.post("/api/v1/storefront/orders", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json()["holds_capacity"] is False
    from app.models.orders import Order

    stored = db.query(Order).one()
    assert stored.crm_id_sessao == SESSION
    assert stored.holds_capacity is False
    assert stored.customer_email == "ana@padaria.com"
    assert len(sent) == 1
    body = sent[0]
    assert body["id_sessao"] == SESSION
    assert body["tipo_evento"] == "pedido_enviar"
    assert body["id_usuario"] == str(stored.id)
    assert "@" not in json.dumps(body)
    assert "instituicao_id" not in body
    assert body["dados"]["situacao"] == "submitted"
    assert "ana@padaria.com" not in json.dumps(body)

    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("hub fora")

    monkeypatch.setattr("app.domain.crm_tracking.httpx.post", boom)
    other = tracking_client.post(
        "/api/v1/storefront/orders",
        json={**payload, "idempotency_key": "crm-submit-2"},
    )
    assert other.status_code == 200, other.text
    assert other.json()["holds_capacity"] is False
    assert db.query(Order).count() == 2


def test_aceite_reusa_sessao_e_pagamento_nao_leva_valor(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict] = []

    def record(*_args, **kwargs):
        sent.append(kwargs["json"])

        class Response:
            status_code = 201

        return Response()

    monkeypatch.setenv("LOJADEPAES_CRM_TRACKING_SECRET", "segredo-teste")
    monkeypatch.setenv("LOJADEPAES_CRM_TRACKING_SYNC", "1")
    get_settings.cache_clear()
    monkeypatch.setattr("app.domain.crm_tracking.httpx.post", record)

    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    order.crm_id_sessao = SESSION
    order.customer_email = "ana@padaria.com"
    confirm_order(db, order.id)
    db.commit()
    assert order.holds_capacity is True
    assert sent[-1]["tipo_evento"] == "pedido_aceitar"
    assert sent[-1]["id_sessao"] == SESSION
    assert sent[-1]["id_usuario"] == str(order.id)
    assert "ana@padaria.com" not in json.dumps(sent[-1])

    orphan = draft_order(db, catalog)
    orphan.crm_id_sessao = None
    confirm_order(db, orphan.id)
    assert sent[-1]["id_sessao"] != SESSION
    assert sent[-1]["dados"]["sessao_origem_ausente"] is True

    emit_order_fact(db, get_settings(), order, "pagamento_registrar", situacao="paid")
    paid = sent[-1]
    assert paid["tipo_evento"] == "pagamento_registrar"
    assert paid["id_sessao"] == SESSION
    assert paid["dados"] == {"pedido_id": str(order.id), "situacao": "paid"}
    assert order.total_cents not in paid["dados"].values()
    blob = json.dumps(paid)
    assert "pix" not in blob
    assert "@" not in blob
