"""Percurso manual de vínculo, abertura e receita honesta. Não altera produção."""

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
from app.modules.ingredient_catalog.consolidate import recipe_quantity_from_lot
from app.modules.ingredient_catalog.models import Ingredient, IngredientLinkReassignment
from app.modules.inventory_procurement.models import InventoryBalance, InventoryLot, InventoryMovement
from app.modules.production_planning.errors import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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


def _world(admin, slug: str, *, role: str = "owner"):
    organization = helpers.org(admin, slug)
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, role)
    place = helpers.establishment(admin, organization, "LOJA")
    subject = f"sub-{slug}"
    helpers.auth_identity(admin, actor, ISSUER, subject)
    return organization, actor, place, subject


def _counts(engine, organization_id) -> dict[str, int]:
    session = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
    try:
        org = organization_id
        return {
            "ingredients": session.scalar(select(func.count()).select_from(Ingredient).where(Ingredient.organization_id == org)) or 0,
            "lots": session.scalar(select(func.count()).select_from(InventoryLot).where(InventoryLot.organization_id == org)) or 0,
            "movements": session.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.organization_id == org)) or 0,
            "balances": session.scalar(select(func.count()).select_from(InventoryBalance).where(InventoryBalance.organization_id == org)) or 0,
            "links": session.scalar(
                select(func.count()).select_from(IngredientLinkReassignment).where(
                    IngredientLinkReassignment.organization_id == org
                )
            )
            or 0,
        }
    finally:
        session.close()


def _receive_two_gtin_lines(client, base, token, place_id, *, number: str, gtin: str, qty_a: str, qty_b: str):
    created = client.post(
        f"{base}/fiscal/documents",
        headers=_headers(token, key=str(uuid4())),
        json={
            "establishment_id": place_id,
            "supplier_name": "Fornecedor ensaio",
            "document_number": number,
            "items": [
                {
                    "description": "Farinha de Trigo de 1 Kg, Tipo 0",
                    "gtin": gtin,
                    "quantity": qty_a,
                    "unit_code": "UN",
                    "unit_price": "10",
                    "gross_amount": "10",
                },
                {
                    "description": "Farinha de Trigo de 1 Kg, Tipo 0",
                    "gtin": gtin,
                    "quantity": qty_b,
                    "unit_code": "UN",
                    "unit_price": "10",
                    "gross_amount": "30",
                },
            ],
        },
    )
    assert created.status_code == 200, created.text
    document = created.json()["data"]
    reviewed = client.post(
        f"{base}/fiscal/documents/{document['id']}/review",
        headers=_headers(token, key=str(uuid4())),
        json={
            "expected_row_version": document["row_version"],
            "lines": [
                {
                    "item_id": item["id"],
                    "suggested_ingredient_name": item["supplier_description"],
                    "reviewed_quantity": item["invoiced_quantity"],
                    "as_expected": True,
                }
                for item in document["items"]
            ],
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    current = reviewed.json()["data"]
    pending = client.post(
        f"{base}/fiscal/documents/{current['id']}/receive",
        headers=_headers(token, key=str(uuid4())),
        json={
            "new_location_name": "Despensa ensaio",
            "lines": [
                {
                    "item_id": item["id"],
                    "new_ingredient_name": item["supplier_description"],
                    "stock_unit": "un",
                    "conversion_factor": "1",
                    "received_quantity": item["invoiced_quantity"],
                    "result": "ok",
                }
                for item in current["items"]
            ],
        },
    )
    assert pending.status_code >= 400, pending.text
    received = client.post(
        f"{base}/fiscal/documents/{current['id']}/receive",
        headers=_headers(token, key=str(uuid4())),
        json={
            "new_location_name": "Despensa ensaio",
            "lines": [
                {
                    "item_id": item["id"],
                    "create_ingredient": True,
                    "new_ingredient_name": f"{item['supplier_description']} {index + 1}",
                    "stock_unit": "un",
                    "conversion_factor": "1",
                    "received_quantity": item["invoiced_quantity"],
                    "result": "ok",
                }
                for index, item in enumerate(current["items"])
            ],
        },
    )
    assert received.status_code == 200, received.text
    return received.json()["data"]


def test_two_gtin_lines_require_manual_consolidate_without_mutating_note(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"lnk{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
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
        before = _counts(engine, organization.id)
        document = _receive_two_gtin_lines(
            client,
            base,
            token,
            str(place.id),
            number="103219",
            gtin="8014601028747",
            qty_a="1",
            qty_b="3",
        )
        after_receive = _counts(engine, organization.id)
        assert after_receive["ingredients"] == before["ingredients"] + 2
        assert after_receive["lots"] == before["lots"] + 2
        assert after_receive["movements"] == before["movements"] + 2

        ingredients = client.get(f"{base}/ingredients?limit=50", headers=_headers(token)).json()["items"]
        destination = ingredients[0]
        other = ingredients[1]
        entries = client.get(
            f"{base}/ingredients/{destination['id']}/linkable-entries",
            headers=_headers(token),
        )
        assert entries.status_code == 200, entries.text
        rows = entries.json()["items"]
        assert len(rows) >= 2
        assert all(row.get("gtin") == "8014601028747" or row.get("document_number") == "103219" for row in rows[:2])
        snap = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
        try:
            lots_before = {
                str(lot.id): (str(lot.received_quantity), lot.unit_code, lot.inventory_item_id)
                for lot in snap.scalars(select(InventoryLot).where(InventoryLot.organization_id == organization.id))
            }
        finally:
            snap.close()

        key = str(uuid4())
        body = {
            "expected_row_version": int(destination.get("row_version") or 1),
            "entries": [
                {
                    "inventory_lot_id": row["inventory_lot_id"],
                    **(
                        {"fiscal_inbound_item_id": row["fiscal_inbound_item_id"]}
                        if row.get("fiscal_inbound_item_id")
                        else {}
                    ),
                }
                for row in rows
                if row.get("inventory_lot_id")
            ],
        }
        first = client.post(
            f"{base}/ingredients/{destination['id']}/links/consolidate",
            headers=_headers(token, key=key),
            json=body,
        )
        assert first.status_code == 200, first.text
        assert first.json()["replayed"] is False
        replay = client.post(
            f"{base}/ingredients/{destination['id']}/links/consolidate",
            headers=_headers(token, key=key),
            json=body,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["replayed"] is True
        after = _counts(engine, organization.id)
        assert after["ingredients"] == after_receive["ingredients"]
        assert after["lots"] == after_receive["lots"]
        assert after["movements"] == after_receive["movements"]
        newly = [row for row in rows if not row.get("already_linked")]
        assert after["links"] == after_receive["links"] + len(newly)

        probe = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
        try:
            still = probe.get(Ingredient, other["id"])
            assert still is not None
            for lot in probe.scalars(select(InventoryLot).where(InventoryLot.organization_id == organization.id)):
                before_lot = lots_before[str(lot.id)]
                assert str(lot.received_quantity) == before_lot[0]
                assert lot.unit_code == before_lot[1]
        finally:
            probe.close()

        stale = client.post(
            f"{base}/ingredients/{destination['id']}/links/consolidate",
            headers=_headers(token, key=str(uuid4())),
            json={"expected_row_version": destination["row_version"], "entries": body["entries"]},
        )
        assert stale.status_code == 409, stale.text
        assert document["document_number"] == "103219"
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_opening_known_and_unknown_cost_and_package_content(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"opn{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
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
        gram = helpers.gram(admin)
        created = client.post(
            f"{base}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"LIM-{slug[-4:]}",
                "display_name": "Limão siciliano",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": str(gram.id),
            },
        )
        assert created.status_code == 200, created.text
        ingredient_id = created.json()["data"]["id"]
        location = client.post(
            f"{base}/inventory/locations",
            headers=_headers(token, key=str(uuid4())),
            json={
                "establishment_id": str(place.id),
                "code": "DESP",
                "display_name": "Despensa",
                "kind": "warehouse",
            },
        )
        assert location.status_code == 200, location.text
        location_id = location.json()["data"]["id"]
        refused = client.post(
            f"{base}/inventory/openings",
            headers=_headers(token, key=str(uuid4())),
            json={
                "ingredient_id": ingredient_id,
                "inventory_location_id": location_id,
                "quantity": "2",
                "unit_code": "un",
                "origin": "contagem física",
                "confirmed": False,
            },
        )
        assert refused.status_code >= 400, refused.text
        known = client.post(
            f"{base}/inventory/openings",
            headers=_headers(token, key=str(uuid4())),
            json={
                "ingredient_id": ingredient_id,
                "inventory_location_id": location_id,
                "quantity": "2",
                "unit_code": "un",
                "origin": "contagem física da despensa",
                "unit_cost": "4.50",
                "confirmed": True,
            },
        )
        assert known.status_code == 200, known.text
        lot_a = known.json()["data"]["id"]
        unknown = client.post(
            f"{base}/inventory/openings",
            headers=_headers(token, key=str(uuid4())),
            json={
                "ingredient_id": ingredient_id,
                "inventory_location_id": location_id,
                "quantity": "1",
                "unit_code": "un",
                "origin": "sobra sem nota",
                "cost_unknown": True,
                "confirmed": True,
            },
        )
        assert unknown.status_code == 200, unknown.text
        lot_b = unknown.json()["data"]["id"]
        declared = client.post(
            f"{base}/inventory/lots/{lot_a}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "0.8", "package_content_unit": "kg"},
        )
        assert declared.status_code == 200, declared.text
        other = client.post(
            f"{base}/inventory/lots/{lot_b}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "1.1", "package_content_unit": "kg"},
        )
        assert other.status_code == 200, other.text
        probe = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
        try:
            first = probe.get(InventoryLot, lot_a)
            second = probe.get(InventoryLot, lot_b)
            assert first.cost_status == "known"
            assert first.declared_unit_cost == Decimal("4.50")
            assert first.package_content_quantity == Decimal("0.8")
            assert second.cost_status == "unknown"
            assert second.declared_unit_cost is None
            assert second.package_content_quantity == Decimal("1.1")
            converted, evidence = recipe_quantity_from_lot(
                first, wanted_quantity=Decimal("800"), wanted_unit="g"
            )
            assert converted == Decimal("1")
            assert evidence["source"] == "declared_package_content"
            with pytest.raises(ValidationError, match="conteudo_embalagem_ausente"):
                empty = InventoryLot(unit_code="un", package_content_quantity=None, package_content_unit=None)
                recipe_quantity_from_lot(empty, wanted_quantity=Decimal("100"), wanted_unit="g")
        finally:
            probe.close()
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_local_trial_recipe_by_published_name(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"rcp{uuid4().hex[:6]}"
    organization, _actor, _place, subject = _world(admin, slug)
    unit = helpers.gram(admin)
    helpers.kilogram(admin)
    helpers.each(admin)
    protein = helpers.nutrient(admin, unit, f"prot-{slug[-6:]}")
    admin.commit()
    fake = FakeAccessTokenVerifier()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    client = _client(engine, fake)
    org = str(organization.id)
    base = f"/api/v1/organizations/{org}"
    try:
        created = client.post(
            f"{base}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"FAR-{slug[-4:]}",
                "display_name": "Farinha de trigo ensaio",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": str(unit.id),
            },
        )
        assert created.status_code == 200, created.text
        ingredient_id = created.json()["data"]["id"]
        detail = client.get(f"{base}/ingredients/{ingredient_id}", headers=_headers(token)).json()
        version_id = detail["data"]["versions"][0]["id"]
        row_version = detail["data"]["versions"][0]["row_version"]
        nutrient = client.post(
            f"{base}/ingredients/{ingredient_id}/versions/{version_id}/nutrients",
            headers={**_headers(token), "If-Match": str(row_version)},
            json={"nutrient_id": str(protein.id), "value": "10", "value_status": "measured"},
        )
        assert nutrient.status_code == 200, nutrient.text
        published = client.post(
            f"{base}/ingredients/{ingredient_id}/versions/{version_id}/publish",
            headers=_headers(token, key=str(uuid4())) | {"If-Match": str(row_version + 1)},
        )
        assert published.status_code == 200, published.text
        found = client.get(
            f"{base}/ingredients?q=Farinha de trigo ensaio&version_status=published",
            headers=_headers(token),
        )
        assert found.status_code == 200, found.text
        assert any(row["display_name"] == "Farinha de trigo ensaio" for row in found.json()["items"])
        recipe = client.post(
            f"{base}/recipes",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"LIMAO-{slug[-4:]}",
                "display_name": "Pão de Limão Siciliano [ensaio local · quantidades fictícias]",
            },
        )
        assert recipe.status_code == 200, recipe.text
        recipe_id = recipe.json()["data"]["id"]
        recipe_detail = client.get(f"{base}/recipes/{recipe_id}", headers=_headers(token)).json()
        recipe_version = recipe_detail["data"]["versions"][0]
        item = client.post(
            f"{base}/recipes/{recipe_id}/versions/{recipe_version['id']}/items",
            headers=_headers(token, key=str(uuid4())) | {"If-Match": str(recipe_version["row_version"])},
            json={
                "ingredient_version_id": version_id,
                "sequence": 1,
                "net_quantity": "500",
                "measurement_unit_id": str(unit.id),
                "is_flour_basis": True,
                "role": "ingredient",
            },
        )
        assert item.status_code == 200, item.text
        assert recipe.json()["data"]["display_name"].endswith("ensaio local · quantidades fictícias]")
        assert recipe_detail["data"]["current_version"]["status"] == "draft"
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_other_organization_cannot_consolidate(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"iso{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
    other_org, _other_actor, _other_place, other_subject = _world(admin, f"{slug}b")
    helpers.gram(admin)
    helpers.each(admin)
    admin.commit()
    fake = FakeAccessTokenVerifier()
    token = f"token-{slug}"
    other_token = f"token-{slug}b"
    fake.register(token, issuer=ISSUER, subject=subject)
    fake.register(other_token, issuer=ISSUER, subject=other_subject)
    client = _client(engine, fake)
    try:
        gram = helpers.gram(admin)
        created = client.post(
            f"/api/v1/organizations/{organization.id}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": "X",
                "display_name": "Insumo isolado",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": str(gram.id),
            },
        )
        assert created.status_code == 200, created.text
        ingredient_id = created.json()["data"]["id"]
        hidden = client.get(
            f"/api/v1/organizations/{organization.id}/ingredients/{ingredient_id}/linkable-entries",
            headers=_headers(other_token),
        )
        assert hidden.status_code in {403, 404}
        foreign = client.post(
            f"/api/v1/organizations/{other_org.id}/ingredients/{ingredient_id}/links/consolidate",
            headers=_headers(other_token, key=str(uuid4())),
            json={"expected_row_version": 1, "entries": [{"inventory_lot_id": str(uuid4())}]},
        )
        assert foreign.status_code in {403, 404, 422}
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()
        _ = place


def _open_lot(client, base, token, place_id, ingredient_id, *, qty: str, cost_unknown: bool, unit_cost: str | None, lot_code: str):
    location = client.post(
        f"{base}/inventory/locations",
        headers=_headers(token, key=str(uuid4())),
        json={
            "establishment_id": place_id,
            "code": f"D{lot_code[-4:]}",
            "display_name": f"Despensa {lot_code}",
            "kind": "warehouse",
        },
    )
    if location.status_code != 200:
        locations = client.get(f"{base}/inventory/locations", headers=_headers(token))
        location_id = locations.json()["items"][0]["id"]
    else:
        location_id = location.json()["data"]["id"]
    body = {
        "ingredient_id": ingredient_id,
        "inventory_location_id": location_id,
        "quantity": qty,
        "unit_code": "un",
        "origin": "ensaio descartável de conteúdo",
        "internal_lot_code": lot_code,
        "confirmed": True,
        "cost_unknown": cost_unknown,
    }
    if unit_cost is not None:
        body["unit_cost"] = unit_cost
    opened = client.post(
        f"{base}/inventory/openings",
        headers=_headers(token, key=str(uuid4())),
        json=body,
    )
    assert opened.status_code == 200, opened.text
    return opened.json()["data"], location_id


def test_package_content_blocked_after_consume_reserve_and_idempotent_replay(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"pkg{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
    helpers.gram(admin)
    helpers.each(admin)
    admin.commit()
    fake = FakeAccessTokenVerifier()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    client = _client(engine, fake)
    org = str(organization.id)
    base = f"/api/v1/organizations/{org}"
    try:
        gram = helpers.gram(admin)
        created = client.post(
            f"{base}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"PKG-{slug[-4:]}",
                "display_name": "Insumo conteúdo",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": str(gram.id),
            },
        )
        assert created.status_code == 200, created.text
        ingredient_id = created.json()["data"]["id"]
        lot, location_id = _open_lot(
            client, base, token, str(place.id), ingredient_id, qty="4", cost_unknown=False, unit_cost="3.20", lot_code=f"LOT-{slug[-4:]}A"
        )
        first = client.post(
            f"{base}/inventory/lots/{lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "0.8", "package_content_unit": "kg", "expected_row_version": lot["row_version"]},
        )
        assert first.status_code == 200, first.text
        version = first.json()["row_version"]
        stale = client.post(
            f"{base}/inventory/lots/{lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "0.9", "package_content_unit": "kg", "expected_row_version": lot["row_version"]},
        )
        assert stale.status_code == 409, stale.text
        corrected = client.post(
            f"{base}/inventory/lots/{lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "0.9", "package_content_unit": "kg", "expected_row_version": version},
        )
        assert corrected.status_code == 200, corrected.text

        consume = client.post(
            f"{base}/inventory/movements",
            headers=_headers(token, key=str(uuid4())),
            json={
                "movement_type": "production_consume",
                "inventory_item_id": lot["inventory_item_id"],
                "inventory_lot_id": lot["id"],
                "from_location_id": location_id,
                "quantity": "1",
                "unit_code": "un",
            },
        )
        assert consume.status_code == 200, consume.text
        refused = client.post(
            f"{base}/inventory/lots/{lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "1.1", "package_content_unit": "kg"},
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["code"] == "conteudo_embalagem_ja_usado"
        replay = client.post(
            f"{base}/inventory/lots/{lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "0.9", "package_content_unit": "kg"},
        )
        assert replay.status_code == 200, replay.text

        reserved_lot, _ = _open_lot(
            client, base, token, str(place.id), ingredient_id, qty="2", cost_unknown=True, unit_cost=None, lot_code=f"LOT-{slug[-4:]}B"
        )
        declared = client.post(
            f"{base}/inventory/lots/{reserved_lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "1.0", "package_content_unit": "kg"},
        )
        assert declared.status_code == 200, declared.text
        probe = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
        try:
            balance = probe.scalar(
                select(InventoryBalance).where(InventoryBalance.inventory_lot_id == reserved_lot["id"])
            )
            assert balance is not None
            balance.reserved_quantity = Decimal("1")
            probe.commit()
        finally:
            probe.close()
        reserved_refuse = client.post(
            f"{base}/inventory/lots/{reserved_lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "1.4", "package_content_unit": "kg"},
        )
        assert reserved_refuse.status_code == 422, reserved_refuse.text
        assert reserved_refuse.json()["code"] == "conteudo_embalagem_ja_usado"
        reserved_replay = client.post(
            f"{base}/inventory/lots/{reserved_lot['id']}/package-content",
            headers=_headers(token, key=str(uuid4())),
            json={"package_content_quantity": "1.0", "package_content_unit": "kg"},
        )
        assert reserved_replay.status_code == 200, reserved_replay.text
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_consolidate_package_content_respects_use_and_two_lines_reconcile(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"rcl{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
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
        before = _counts(engine, organization.id)
        document = _receive_two_gtin_lines(
            client,
            base,
            token,
            str(place.id),
            number="221190",
            gtin="8014601028747",
            qty_a="1",
            qty_b="3",
        )
        after_receive = _counts(engine, organization.id)
        lots = client.get(f"{base}/inventory/lots", headers=_headers(token)).json()["items"]
        assert len(lots) >= 2
        by_qty = {Decimal(row["received_quantity"]): row for row in lots}
        lot_a = by_qty[Decimal("1")]
        lot_b = by_qty[Decimal("3")]
        before_a = client.get(f"{base}/inventory/lots/{lot_a['id']}/reconciliation", headers=_headers(token))
        before_b = client.get(f"{base}/inventory/lots/{lot_b['id']}/reconciliation", headers=_headers(token))
        assert before_a.status_code == 200, before_a.text
        assert before_b.status_code == 200, before_b.text
        assert before_a.json()["matched"] is True
        assert before_b.json()["matched"] is True
        assert Decimal(before_a.json()["physical_quantity"]) == Decimal("1")
        assert Decimal(before_b.json()["physical_quantity"]) == Decimal("3")
        recorded_a = [row["inventory_item_id"] for row in client.get(f"{base}/inventory/movements", headers=_headers(token)).json()["items"] if row["inventory_lot_id"] == lot_a["id"]]

        consume = client.post(
            f"{base}/inventory/movements",
            headers=_headers(token, key=str(uuid4())),
            json={
                "movement_type": "production_consume",
                "inventory_item_id": lot_a["inventory_item_id"],
                "inventory_lot_id": lot_a["id"],
                "from_location_id": lot_a["inventory_location_id"],
                "quantity": "1",
                "unit_code": lot_a["unit_code"],
            },
        )
        assert consume.status_code == 200, consume.text

        ingredients = client.get(f"{base}/ingredients?limit=50", headers=_headers(token)).json()["items"]
        preview = client.get(f"{base}/inventory/linkable-entries", headers=_headers(token)).json()["items"]
        used_entry = next(row for row in preview if row["inventory_lot_id"] == lot_a["id"])
        assert used_entry["has_downstream_use"] is True
        destination = next(row for row in ingredients if row["id"] != used_entry["current_ingredient_id"])
        entries = client.get(
            f"{base}/ingredients/{destination['id']}/linkable-entries",
            headers=_headers(token),
        ).json()["items"]
        used_entry = next(row for row in entries if row["inventory_lot_id"] == lot_a["id"])
        refused = client.post(
            f"{base}/ingredients/{destination['id']}/links/consolidate",
            headers=_headers(token, key=str(uuid4())),
            json={
                "expected_row_version": int(destination.get("row_version") or 1),
                "entries": [
                    {
                        "inventory_lot_id": lot_a["id"],
                        "package_content_quantity": "2.5",
                        "package_content_unit": "kg",
                    }
                ],
            },
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["code"] == "conteudo_embalagem_ja_usado"

        first = client.post(
            f"{base}/ingredients/{destination['id']}/links/consolidate",
            headers=_headers(token, key=str(uuid4())),
            json={
                "expected_row_version": int(destination.get("row_version") or 1),
                "entries": [
                    {"inventory_lot_id": lot_a["id"], "fiscal_inbound_item_id": used_entry.get("fiscal_inbound_item_id")},
                    {
                        "inventory_lot_id": lot_b["id"],
                        "package_content_quantity": "1.0",
                        "package_content_unit": "kg",
                    },
                ],
            },
        )
        assert first.status_code == 200, first.text
        after = _counts(engine, organization.id)
        assert after["movements"] == after_receive["movements"] + 1
        assert after["lots"] == after_receive["lots"]
        assert after["ingredients"] == after_receive["ingredients"]

        after_a = client.get(f"{base}/inventory/lots/{lot_a['id']}/reconciliation", headers=_headers(token)).json()
        after_b = client.get(f"{base}/inventory/lots/{lot_b['id']}/reconciliation", headers=_headers(token)).json()
        assert after_a["matched"] is True
        assert after_b["matched"] is True
        assert Decimal(after_a["physical_quantity"]) == Decimal("0")
        assert Decimal(after_b["physical_quantity"]) == Decimal("3")
        assert after_a["current_ingredient_id"] == destination["id"]
        assert after_b["current_ingredient_id"] == destination["id"]
        assert after_a["hidden_chain"] is False
        assert after_a["reclassified"] is True
        assert after_a["recorded_inventory_items"]

        movements = client.get(f"{base}/inventory/movements", headers=_headers(token)).json()["items"]
        inbound_a = [row for row in movements if row["inventory_lot_id"] == lot_a["id"] and row["movement_type"] == "receipt"]
        assert inbound_a
        assert inbound_a[0]["reclassified"] is True
        assert inbound_a[0]["recorded_inventory_item_id"] in recorded_a
        assert inbound_a[0]["current_inventory_item_id"] == after_a["current_inventory_item_id"]
        assert inbound_a[0]["inventory_item_id"] == inbound_a[0]["recorded_inventory_item_id"]

        probe = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
        try:
            for movement in probe.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.organization_id == organization.id,
                    InventoryMovement.inventory_lot_id == lot_a["id"],
                    InventoryMovement.movement_type == "receipt",
                )
            ):
                assert str(movement.inventory_item_id) == inbound_a[0]["recorded_inventory_item_id"]
        finally:
            probe.close()
        assert document["document_number"] == "221190"
        assert before["lots"] == after_receive["lots"] - 2
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()


def test_mixed_unknown_cost_is_not_complete_price(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"unk{uuid4().hex[:6]}"
    organization, _actor, place, subject = _world(admin, slug)
    unit = helpers.gram(admin)
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
            f"{base}/ingredients",
            headers=_headers(token, key=str(uuid4())),
            json={
                "code": f"UNK-{slug[-4:]}",
                "display_name": "Farinha mista ensaio",
                "ingredient_type": "simple",
                "nutrition_basis_unit_id": str(unit.id),
            },
        )
        assert created.status_code == 200, created.text
        ingredient_id = created.json()["data"]["id"]
        known, _ = _open_lot(
            client, base, token, str(place.id), ingredient_id, qty="2", cost_unknown=False, unit_cost="4.50", lot_code=f"LOT-{slug[-4:]}K"
        )
        unknown, _ = _open_lot(
            client, base, token, str(place.id), ingredient_id, qty="1", cost_unknown=True, unit_cost=None, lot_code=f"LOT-{slug[-4:]}U"
        )
        assert known["cost_status"] == "known"
        assert unknown["cost_status"] == "unknown"
        assert unknown["cost_cut"] == "lote"
        detail = client.get(f"{base}/ingredients/{ingredient_id}", headers=_headers(token)).json()
        version_id = detail["data"]["versions"][0]["id"]
        from app.modules.costing_pricing.valuation import select_price
        from datetime import UTC, datetime

        probe = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
        try:
            chosen = select_price(
                probe,
                ingredient_version_id=version_id,
                valuation_at=datetime.now(UTC),
                currency="BRL",
                criterion="latest_observed",
            )
            assert chosen is None
            known_row = probe.get(InventoryLot, known["id"])
            unknown_row = probe.get(InventoryLot, unknown["id"])
            assert known_row.declared_unit_cost == Decimal("4.50")
            assert unknown_row.declared_unit_cost is None
            assert unknown_row.cost_status == "unknown"
        finally:
            probe.close()
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
        admin.close()

