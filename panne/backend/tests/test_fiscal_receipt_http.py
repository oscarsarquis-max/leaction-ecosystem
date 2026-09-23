"""Ensaio HTTP da entrada fiscal num banco descartável, sem insumo e sem local prévios."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.db import get_runtime_session
from app.main import app
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.http import get_access_token_verifier
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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


def test_new_client_receipt_through_the_api(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"nf{uuid4().hex[:6]}"
    organization = helpers.org(admin, slug)
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, "owner")
    place = helpers.establishment(admin, organization, "LOJA")
    other = helpers.establishment(admin, organization, "FILIAL")
    helpers.gram(admin)
    subject = f"sub-{slug}"
    helpers.auth_identity(admin, actor, ISSUER, subject)
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
                "document_number": "900",
                "series": "1",
                "items": [
                    {
                        "description": "Pao frances 250g",
                        "quantity": "1",
                        "unit_code": "UN",
                        "unit_price": "4.50",
                        "gross_amount": "4.50",
                    }
                ],
            },
        )
        assert created.status_code == 200, created.text
        document = created.json()["data"]
        assert document["stock_applied"] is False
        item = document["items"][0]
        assert Decimal(item["invoice_unit_price"]) == Decimal("4.50")
        assert item["stock_unit_cost"] is None
        assert item["unit_code"] == "UN"

        units = client.get(f"{base}/catalog/units", headers=_headers(token))
        assert units.status_code == 200, units.text
        gram = next(row for row in units.json()["data"] if row["code"] == "g")
        ingredient = client.post(
            f"{base}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"pao-{slug}",
                "display_name": "Pao frances",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": gram["id"],
            },
        )
        assert ingredient.status_code == 200, ingredient.text
        ingredient_id = ingredient.json()["data"]["id"]

        stock_item = client.post(
            f"{base}/inventory/items",
            headers=_headers(token, key=str(uuid4())),
            json={"ingredient_id": ingredient_id, "unit_code": "g", "lot_control": "optional"},
        )
        assert stock_item.status_code == 200, stock_item.text
        stock_item_id = stock_item.json()["data"]["id"]

        location = client.post(
            f"{base}/inventory/locations",
            headers=_headers(token, key=str(uuid4())),
            json={
                "establishment_id": str(place.id),
                "code": f"dep-{slug}",
                "display_name": "Despensa",
                "kind": "warehouse",
            },
        )
        assert location.status_code == 200, location.text
        location_id = location.json()["data"]["id"]

        foreign = client.post(
            f"{base}/inventory/locations",
            headers=_headers(token, key=str(uuid4())),
            json={
                "establishment_id": str(other.id),
                "code": f"out-{slug}",
                "display_name": "Estoque da filial",
                "kind": "warehouse",
            },
        )
        assert foreign.status_code == 200, foreign.text

        matched = client.post(
            f"{base}/fiscal/documents/{document['id']}/items/{item['id']}/match",
            headers=_headers(token, key=str(uuid4())),
            json={
                "target_type": "ingredient",
                "target_id": ingredient_id,
                "inventory_item_id": stock_item_id,
                "unit_code": "g",
                "conversion_factor": "250",
            },
        )
        assert matched.status_code == 200, matched.text
        assert matched.json()["data"]["stock_applied"] is False

        rejected = client.post(
            f"{base}/fiscal/documents/{document['id']}/items/{item['id']}/physical",
            headers=_headers(token, key=str(uuid4())),
            json={"received_quantity": "1 UN", "unit_code": "g", "result": "ok"},
        )
        assert rejected.status_code >= 400, rejected.text
        movements = client.get(f"{base}/inventory/movements", headers=_headers(token))
        assert movements.json()["items"] == []

        checked = client.post(
            f"{base}/fiscal/documents/{document['id']}/items/{item['id']}/physical",
            headers=_headers(token, key=str(uuid4())),
            json={"received_quantity": "250", "unit_code": "g", "result": "ok"},
        )
        assert checked.status_code == 200, checked.text
        assert checked.json()["data"]["stock_applied"] is False
        movements = client.get(f"{base}/inventory/movements", headers=_headers(token))
        assert movements.status_code == 200, movements.text
        assert movements.json()["items"] == []

        confirm_key = str(uuid4())
        confirmed = client.post(
            f"{base}/fiscal/documents/{document['id']}/confirm",
            headers=_headers(token, key=confirm_key),
            json={"inventory_location_id": location_id},
        )
        assert confirmed.status_code == 200, confirmed.text
        body = confirmed.json()["data"]
        assert body["stock_applied"] is True
        line = body["items"][0]
        assert Decimal(line["invoice_unit_price"]) == Decimal("4.50")
        assert line["unit_code"] == "UN"
        assert Decimal(line["stock_unit_cost"]) == Decimal("0.018")
        assert line["stock_unit_code"] == "g"
        assert body["storage_location_label"] == "Despensa"

        balances = client.get(f"{base}/inventory/balances", headers=_headers(token))
        assert balances.status_code == 200, balances.text
        assert Decimal(balances.json()["items"][0]["physical_quantity"]) == Decimal("250")
        movements = client.get(f"{base}/inventory/movements", headers=_headers(token))
        assert len(movements.json()["items"]) == 1

        again = client.post(
            f"{base}/fiscal/documents/{document['id']}/confirm",
            headers=_headers(token, key=confirm_key),
            json={"inventory_location_id": location_id},
        )
        assert again.status_code == 200, again.text
        assert again.json()["data"]["id"] == document["id"]
        movements = client.get(f"{base}/inventory/movements", headers=_headers(token))
        assert len(movements.json()["items"]) == 1

        refused = client.post(
            f"{base}/fiscal/documents",
            headers=_headers(token, key=str(uuid4())),
            json={
                "establishment_id": str(place.id),
                "supplier_name": "Emitente novo",
                "document_number": "901",
                "items": [
                    {
                        "description": "Outro pao",
                        "quantity": "1",
                        "unit_code": "g",
                        "unit_price": "1",
                        "gross_amount": "1",
                    }
                ],
            },
        )
        assert refused.status_code == 200, refused.text
        second = refused.json()["data"]
        second_item = second["items"][0]
        client.post(
            f"{base}/fiscal/documents/{second['id']}/items/{second_item['id']}/match",
            headers=_headers(token, key=str(uuid4())),
            json={
                "target_type": "ingredient",
                "target_id": ingredient_id,
                "inventory_item_id": stock_item_id,
                "unit_code": "g",
                "conversion_factor": "1",
            },
        )
        client.post(
            f"{base}/fiscal/documents/{second['id']}/items/{second_item['id']}/physical",
            headers=_headers(token, key=str(uuid4())),
            json={"received_quantity": "1", "unit_code": "g", "result": "ok"},
        )
        denied = client.post(
            f"{base}/fiscal/documents/{second['id']}/confirm",
            headers=_headers(token, key=str(uuid4())),
            json={"inventory_location_id": foreign.json()["data"]["id"]},
        )
        assert denied.status_code >= 400, denied.text
        movements = client.get(f"{base}/inventory/movements", headers=_headers(token))
        assert len(movements.json()["items"]) == 1
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()
