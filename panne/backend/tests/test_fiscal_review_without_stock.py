"""Gravar a nota não lança estoque. A entrada no estoque é outra ação."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.db import get_runtime_session
from app.main import app
from app.modules.fiscal_inbound.models import FiscalCostAllocation, FiscalDocumentEvent
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.http import get_access_token_verifier
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    InventoryPolicy,
    ProcurementReceipt,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker
from tests import helpers
from tests.jwt_support import ISSUER
from tests.rls_support import ensure_runtime_role, runtime_postgres_url


def _ensure_head(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    _ensure_head(engine)


def _client(engine, fake: FakeAccessTokenVerifier) -> TestClient:
    ensure_runtime_role(engine)
    runtime = create_engine(runtime_postgres_url(), future=True, pool_pre_ping=True)
    factory = sessionmaker(bind=runtime, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_access_token_verifier] = lambda: fake
    client = TestClient(app)
    client.runtime_engine = runtime
    return client


def _headers(token: str, *, key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Correlation-Id": str(uuid4()),
    }
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _counts(engine, organization_id) -> dict[str, int]:
    session = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
    try:
        org = organization_id
        return {
            "ingredients": session.scalar(select(func.count()).select_from(Ingredient).where(Ingredient.organization_id == org)) or 0,
            "items": session.scalar(select(func.count()).select_from(InventoryItem).where(InventoryItem.organization_id == org)) or 0,
            "locations": session.scalar(select(func.count()).select_from(InventoryLocation).where(InventoryLocation.organization_id == org)) or 0,
            "policies": session.scalar(select(func.count()).select_from(InventoryPolicy).where(InventoryPolicy.organization_id == org)) or 0,
            "receipts": session.scalar(select(func.count()).select_from(ProcurementReceipt).where(ProcurementReceipt.organization_id == org)) or 0,
            "movements": session.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.organization_id == org)) or 0,
            "balances": session.scalar(select(func.count()).select_from(InventoryBalance).where(InventoryBalance.organization_id == org)) or 0,
            "costs": session.scalar(select(func.count()).select_from(FiscalCostAllocation).where(FiscalCostAllocation.organization_id == org)) or 0,
            "events": session.scalar(select(func.count()).select_from(FiscalDocumentEvent).where(FiscalDocumentEvent.organization_id == org)) or 0,
        }
    finally:
        session.close()


def _world(admin, slug: str, *, role: str = "owner"):
    organization = helpers.org(admin, slug)
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, role)
    place = helpers.establishment(admin, organization, "LOJA")
    other = helpers.establishment(admin, organization, "FILIAL")
    subject = f"sub-{slug}"
    helpers.auth_identity(admin, actor, ISSUER, subject)
    return organization, actor, place, other, subject


def _review_body(document: dict) -> dict:
    return {
        "expected_row_version": document["row_version"],
        "lines": [
            {
                "item_id": item["id"],
                "suggested_ingredient_name": item["supplier_description"] or "Insumo",
                "reviewed_quantity": item["invoiced_quantity"] or "1",
                "as_expected": True,
            }
            for item in document["items"]
        ],
    }


def test_save_review_does_not_touch_stock_then_receive_is_separate(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"nf{uuid4().hex[:6]}"
    organization, actor, place, other, subject = _world(admin, slug)
    helpers.gram(admin)
    helpers.kilogram(admin)
    helpers.each(admin)
    admin.commit()

    fake = FakeAccessTokenVerifier()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    client = _client(engine, fake)
    org = str(organization.id)
    base = f"/api/v1/organizations/{org}"
    try:
        created = client.post(
            f"{base}/fiscal/documents",
            headers=_headers(token, key=str(uuid4())),
            json={
                "establishment_id": str(place.id),
                "supplier_name": "Emitente novo",
                "document_number": "415",
                "series": "4",
                "items": [
                    {
                        "description": "Erva doce especial",
                        "quantity": "1",
                        "unit_code": "UN",
                        "unit_price": "18.84",
                        "gross_amount": "18.84",
                    },
                    {
                        "description": "Farinha tipo 1",
                        "quantity": "2",
                        "unit_code": "KG",
                        "unit_price": "3",
                        "gross_amount": "6",
                    },
                ],
            },
        )
        assert created.status_code == 200, created.text
        document = created.json()["data"]
        assert document["status"] != "reviewed"
        assert document["review_saved"] is False
        assert document["stock_applied"] is False
        assert document["next_action"] == "save_review"
        assert document["items"][0]["unit_code"] == "UN"
        before = _counts(engine, organization.id)

        early = client.post(
            f"{base}/fiscal/documents/{document['id']}/receive",
            headers=_headers(token, key=str(uuid4())),
            json={
                "new_location_name": "Despensa",
                "lines": [
                    {
                        "item_id": item["id"],
                        "new_ingredient_name": item["supplier_description"],
                        "stock_unit": "g" if item["unit_code"] == "UN" else "kg",
                        "conversion_factor": "250" if item["unit_code"] == "UN" else "1",
                        "received_quantity": "250" if item["unit_code"] == "UN" else "2",
                        "result": "ok",
                    }
                    for item in document["items"]
                ],
            },
        )
        assert early.status_code == 422, early.text
        assert _counts(engine, organization.id)["ingredients"] == before["ingredients"]

        review_key = str(uuid4())
        saved = client.post(
            f"{base}/fiscal/documents/{document['id']}/review",
            headers=_headers(token, key=review_key),
            json=_review_body(document),
        )
        assert saved.status_code == 200, saved.text
        payload = saved.json()["data"]
        assert payload["status"] == "reviewed"
        assert payload["status_label"] == "Nota gravada · estoque pendente"
        assert payload["review_saved"] is True
        assert payload["stock_pending"] is True
        assert payload["stock_applied"] is False
        assert payload["catalogs_created"] is False
        assert payload["next_action"] == "confirm_stock"
        assert payload["items"][0]["unit_code"] == "UN"
        assert payload["items"][0]["review"]["reviewed_quantity"]
        after_review = _counts(engine, organization.id)
        for key in ("ingredients", "items", "locations", "policies", "receipts", "movements", "balances", "costs"):
            assert after_review[key] == before[key], key
        assert after_review["events"] == before["events"] + 1

        reopened = client.get(f"{base}/fiscal/documents/{document['id']}", headers=_headers(token))
        assert reopened.status_code == 200, reopened.text
        again_doc = reopened.json()["data"]
        assert again_doc["status"] == "reviewed"
        assert again_doc["review_saved"] is True
        assert again_doc["stock_applied"] is False
        assert again_doc["items"][0]["review"]["suggested_ingredient_name"]

        replay = client.post(
            f"{base}/fiscal/documents/{document['id']}/review",
            headers=_headers(token, key=review_key),
            json=_review_body(document),
        )
        assert replay.status_code == 200, replay.text
        assert _counts(engine, organization.id)["events"] == after_review["events"]

        stale = client.post(
            f"{base}/fiscal/documents/{document['id']}/review",
            headers=_headers(token, key=str(uuid4())),
            json=_review_body(document),
        )
        assert stale.status_code == 409, stale.text
        assert _counts(engine, organization.id)["movements"] == before["movements"]

        continued = client.post(
            f"{base}/fiscal/documents/{document['id']}/review",
            headers=_headers(token, key=str(uuid4())),
            json=_review_body(again_doc),
        )
        assert continued.status_code == 200, continued.text
        current = continued.json()["data"]
        assert current["stock_applied"] is False
        assert _counts(engine, organization.id)["ingredients"] == before["ingredients"]

        receive_key = str(uuid4())
        receive_body = {
            "new_location_name": "Despensa da unidade",
            "accept_divergence": True,
            "lines": [
                {
                    "item_id": current["items"][0]["id"],
                    "new_ingredient_name": "Grao de erva doce",
                    "stock_unit": "g",
                    "conversion_factor": "250",
                    "received_quantity": "200",
                    "result": "shortage",
                },
                {
                    "item_id": current["items"][1]["id"],
                    "new_ingredient_name": "Farinha tipo 1",
                    "stock_unit": "kg",
                    "conversion_factor": "1",
                    "received_quantity": "2",
                    "result": "ok",
                },
            ],
        }
        launched = client.post(
            f"{base}/fiscal/documents/{document['id']}/receive",
            headers=_headers(token, key=receive_key),
            json=receive_body,
        )
        assert launched.status_code == 200, launched.text
        stock = launched.json()["data"]
        assert stock["stock_applied"] is True
        assert stock["catalogs_created"] is True
        assert stock["stock_pending"] is False
        assert stock["status"] in {"received", "partially_received", "confirmed"}
        assert stock["next_action"] == "none"
        after_stock = _counts(engine, organization.id)
        assert after_stock["ingredients"] == before["ingredients"] + 2
        assert after_stock["locations"] == before["locations"] + 1
        assert after_stock["items"] == before["items"] + 2
        assert after_stock["movements"] >= before["movements"] + 1
        assert after_stock["balances"] >= before["balances"] + 1
        assert after_stock["costs"] >= before["costs"] + 1
        assert after_stock["receipts"] == before["receipts"] + 1

        replay_stock = client.post(
            f"{base}/fiscal/documents/{document['id']}/receive",
            headers=_headers(token, key=receive_key),
            json=receive_body,
        )
        assert replay_stock.status_code == 200, replay_stock.text
        assert _counts(engine, organization.id)["movements"] == after_stock["movements"]
        assert _counts(engine, organization.id)["receipts"] == after_stock["receipts"]
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_legacy_note_and_save_only_profile_and_isolation(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug_a = f"nf{uuid4().hex[:6]}"
    slug_b = f"nf{uuid4().hex[:6]}"
    org_a, actor_a, place_a, _filial_a, subject_a = _world(admin, slug_a)
    org_b, actor_b, place_b, _filial_b, subject_b = _world(admin, slug_b)
    checker = helpers.user(admin, f"{slug_a}-ops@example.com")
    helpers.membership(admin, org_a, checker, "production")
    helpers.auth_identity(admin, checker, ISSUER, f"sub-{slug_a}-ops")
    viewer = helpers.user(admin, f"{slug_a}-view@example.com")
    helpers.membership(admin, org_a, viewer, "viewer")
    helpers.auth_identity(admin, viewer, ISSUER, f"sub-{slug_a}-view")
    helpers.gram(admin)
    helpers.each(admin)
    admin.commit()

    fake = FakeAccessTokenVerifier()
    token_a = f"token-{slug_a}"
    token_b = f"token-{slug_b}"
    token_ops = f"token-{slug_a}-ops"
    token_view = f"token-{slug_a}-view"
    fake.register(token_a, issuer=ISSUER, subject=subject_a)
    fake.register(token_b, issuer=ISSUER, subject=subject_b)
    fake.register(token_ops, issuer=ISSUER, subject=f"sub-{slug_a}-ops")
    fake.register(token_view, issuer=ISSUER, subject=f"sub-{slug_a}-view")
    client = _client(engine, fake)
    try:
        base_a = f"/api/v1/organizations/{org_a.id}"
        base_b = f"/api/v1/organizations/{org_b.id}"
        legacy = client.post(
            f"{base_a}/fiscal/documents",
            headers=_headers(token_a, key=str(uuid4())),
            json={
                "establishment_id": str(place_a.id),
                "supplier_name": "Emitente legado",
                "document_number": "100",
                "items": [
                    {
                        "description": "Item legado UN",
                        "quantity": "1",
                        "unit_code": "UN",
                        "unit_price": "1",
                        "gross_amount": "1",
                    }
                ],
            },
        )
        assert legacy.status_code == 200, legacy.text
        other = client.post(
            f"{base_b}/fiscal/documents",
            headers=_headers(token_b, key=str(uuid4())),
            json={
                "establishment_id": str(place_b.id),
                "supplier_name": "Outro cliente",
                "document_number": "200",
                "items": [
                    {
                        "description": "Item do outro cliente",
                        "quantity": "3",
                        "unit_code": "UN",
                        "unit_price": "2",
                        "gross_amount": "6",
                    }
                ],
            },
        )
        assert other.status_code == 200, other.text
        document = legacy.json()["data"]
        stranger = client.get(
            f"{base_a}/fiscal/documents/{other.json()['data']['id']}",
            headers=_headers(token_a),
        )
        assert stranger.status_code in {403, 404}

        denied = client.post(
            f"{base_a}/fiscal/documents/{document['id']}/review",
            headers=_headers(token_view, key=str(uuid4())),
            json=_review_body(document),
        )
        assert denied.status_code == 403, denied.text

        before_a = _counts(engine, org_a.id)
        before_b = _counts(engine, org_b.id)
        saved = client.post(
            f"{base_a}/fiscal/documents/{document['id']}/review",
            headers=_headers(token_ops, key=str(uuid4())),
            json=_review_body(document),
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()["data"]
        assert body["review_saved"] is True
        assert body["stock_applied"] is False
        after_a = _counts(engine, org_a.id)
        after_b = _counts(engine, org_b.id)
        for key in ("ingredients", "items", "locations", "policies", "receipts", "movements", "balances", "costs"):
            assert after_a[key] == before_a[key], key
            assert after_b[key] == before_b[key], key

        blocked = client.post(
            f"{base_a}/fiscal/documents/{document['id']}/receive",
            headers=_headers(token_ops, key=str(uuid4())),
            json={
                "new_location_name": "Despensa ops",
                "lines": [
                    {
                        "item_id": body["items"][0]["id"],
                        "new_ingredient_name": "Insumo ops",
                        "stock_unit": "un",
                        "conversion_factor": "1",
                        "received_quantity": "1",
                        "result": "ok",
                    }
                ],
            },
        )
        assert blocked.status_code == 403, blocked.text
        assert _counts(engine, org_a.id)["movements"] == before_a["movements"]
        assert client.get(f"{base_b}/fiscal/documents/{other.json()['data']['id']}", headers=_headers(token_b)).json()[
            "data"
        ]["review_saved"] is False
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_migration_0029_roundtrip(engine):
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0028_access_credential")
    columns = {column["name"] for column in inspect(engine).get_columns("fiscal_inbound_item")}
    assert "human_review" not in columns
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    columns = {column["name"] for column in inspect(engine).get_columns("fiscal_inbound_item")}
    assert "human_review" in columns
