"""P1-Loja: recebimento do parceiro (MP) — chave desligada/ligada, connect e 409 ao confirmar."""

from uuid import UUID, uuid4
from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.marketplace.models import Partner
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login  # noqa: F401 — fixture
from tests.test_marketplace import _abrir, _csrf, _ligar
from tests.test_marketplace_combo_orders import _cenario, _pedir, _partner_orders

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture
def market(db: Session) -> Session:
    db.execute(text("TRUNCATE marketplace.partners RESTART IDENTITY CASCADE"))
    db.commit()
    return db


def _seller_flag(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setenv(
        "LOJADEPAES_MARKETPLACE_SELLER_PAYMENTS_ENABLED",
        "true" if enabled else "false",
    )
    get_settings.cache_clear()


def test_mp_desligado_abre_em_breve_e_me_traz_null(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    _seller_flag(monkeypatch, False)
    csrf = login(admin_client)
    created, portal = _abrir(admin_client, csrf, f"mp-{uuid4().hex[:6]}", "Queijaria MP")
    me = portal.get("/api/v1/partner/me")
    assert me.status_code == 200
    assert me.json()["partner"]["mp_connected"] is None

    status = portal.get("/api/v1/partner/mp")
    assert status.status_code == 200
    body = status.json()
    assert body["available"] is False
    assert body["connected"] is False

    connect = portal.post("/api/v1/partner/mp/connect", headers=_csrf(portal.csrf))  # type: ignore[attr-defined]
    assert connect.status_code == 404

    detail = admin_client.get(f"/api/v1/admin/marketplace/partners/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["mp_connected"] is None


def test_mp_ligado_connect_devolve_url_do_pay(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    _seller_flag(monkeypatch, True)
    csrf = login(admin_client)
    _created, portal = _abrir(admin_client, csrf, f"mp-{uuid4().hex[:6]}", "Queijaria Link")

    with patch(
        "app.marketplace.sellers_client.connect_link",
        return_value="https://auth.mercadopago.com.br/authorization?x=1",
    ):
        response = portal.post(
            "/api/v1/partner/mp/connect",
            headers=_csrf(portal.csrf),  # type: ignore[attr-defined]
        )
    assert response.status_code == 200, response.text
    assert response.json()["url"].startswith("https://auth.mercadopago.com.br/")


def test_mp_ligado_status_atualiza_cache(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    _seller_flag(monkeypatch, True)
    csrf = login(admin_client)
    created, portal = _abrir(admin_client, csrf, f"mp-{uuid4().hex[:6]}", "Queijaria Cache")

    with patch(
        "app.marketplace.sellers_client.get_seller",
        return_value={
            "connected": True,
            "nickname": "PadariaX",
            "connected_at": "2026-11-25T12:00:00+00:00",
            "status": "connected",
        },
    ):
        status = portal.get("/api/v1/partner/mp")
    assert status.status_code == 200
    body = status.json()
    assert body["available"] is True
    assert body["connected"] is True
    assert body["nickname"] == "PadariaX"

    partner = market.get(Partner, created["id"])
    assert partner is not None
    assert partner.mp_connected is True
    assert partner.mp_nickname == "PadariaX"
    assert partner.mp_checked_at is not None

    me = portal.get("/api/v1/partner/me")
    assert me.json()["partner"]["mp_connected"] is True
    assert me.json()["partner"]["mp_nickname"] == "PadariaX"


def test_confirmar_sem_conta_so_com_chave_ligada(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    _seller_flag(monkeypatch, True)
    cen = _cenario(admin_client, market)
    assert _pedir(admin_client, cen).status_code == 200
    portal: TestClient = cen["portal"]
    order_id = _partner_orders(cen)[0]["id"]

    blocked = portal.post(
        f"/api/v1/partner/orders/{order_id}/accept",
        headers=_csrf(portal.csrf),  # type: ignore[attr-defined]
    )
    assert blocked.status_code == 409
    assert "Mercado Pago" in blocked.json()["detail"]

    partner = market.get(Partner, UUID(cen["partner"]["id"]))
    assert partner is not None
    partner.mp_connected = True
    market.commit()

    ok = portal.post(
        f"/api/v1/partner/orders/{order_id}/accept",
        headers=_csrf(portal.csrf),  # type: ignore[attr-defined]
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "accepted"


def test_confirmar_com_chave_desligada_segue_como_hoje(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    _seller_flag(monkeypatch, False)
    cen = _cenario(admin_client, market)
    assert _pedir(admin_client, cen).status_code == 200
    portal: TestClient = cen["portal"]
    order_id = _partner_orders(cen)[0]["id"]

    ok = portal.post(
        f"/api/v1/partner/orders/{order_id}/accept",
        headers=_csrf(portal.csrf),  # type: ignore[attr-defined]
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "accepted"


def test_migracao_p1_loja_sobe(test_engine, market: Session):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    del market
    ini = Path(__file__).resolve().parents[2] / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    revision = "f7c2e9a14b60"
    try:
        command.downgrade(config, "e1f4a2b90c83")
        cols = {col["name"] for col in inspect(test_engine).get_columns("partners", schema="marketplace")}
        assert "mp_connected" not in cols
    finally:
        command.upgrade(config, "head")
    cols = {col["name"] for col in inspect(test_engine).get_columns("partners", schema="marketplace")}
    assert {"mp_connected", "mp_nickname", "mp_checked_at"} <= cols
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == revision
