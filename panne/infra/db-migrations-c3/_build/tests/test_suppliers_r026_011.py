"""R026-011 — fornecedores, itens comerciais e preços sem N+1."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.ingredient_catalog.models import Ingredient, Supplier, SupplierItem, SupplierItemPrice
from app.modules.ingredient_catalog.queries import active_item_counts_by_supplier, prices_of
from app.modules.ingredient_http.serialize import load_ingredient_refs, load_item_enrichments
from tests import helpers
from tests.jwt_support import ISSUER
from tests.test_production_api import _cleanup, _client, _headers


def _setup(engine, slug_prefix: str, role: str = "owner", fake=None, client=None):
    fake = fake or FakeAccessTokenVerifier()
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"{slug_prefix}-{uuid4().hex[:6]}"
    organization = helpers.org(admin, slug)
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, role)
    unit = helpers.gram(admin)
    subject = f"sub-{slug}"
    helpers.auth_identity(admin, actor, ISSUER, subject)
    admin.commit()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    if client is None:
        client = _client(engine, fake)
    return {
        "client": client,
        "admin": admin,
        "organization": organization,
        "actor": actor,
        "unit": unit,
        "token": token,
        "fake": fake,
    }


def test_suppliers_list_and_detail_enriched_without_n_plus_one(engine):
    ctx = _setup(engine, "r011")
    headers = lambda **kw: _headers(ctx["token"], ctx["organization"].id, **kw)
    admin = ctx["admin"]
    org = ctx["organization"]
    kg = helpers.kilogram(admin)
    flour_version = helpers.published_ingredient(admin, org, kg, "FAR-R011")
    flour = admin.get(Ingredient, flour_version.ingredient_id)
    flour.display_name = "Farinha R011"
    empty = Supplier(
        organization_id=org.id, code="FOR-VAZIO", display_name="Vazio Demo", status="active"
    )
    moinho = Supplier(
        organization_id=org.id, code="FOR-MOINHO", display_name="Moinho Demo", status="active"
    )
    admin.add_all([empty, moinho])
    admin.flush()
    item = SupplierItem(
        organization_id=org.id,
        supplier_id=moinho.id,
        ingredient_id=flour.id,
        supplier_sku="SKU-FAR-25",
        description="saco",
        package_quantity=Decimal("25"),
        measurement_unit_id=kg.id,
        status="active",
    )
    admin.add(item)
    admin.flush()
    older = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    mid = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    latest = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    admin.add_all(
        [
            SupplierItemPrice(
                supplier_item_id=item.id,
                unit_price=Decimal("12.50"),
                currency="BRL",
                observed_at=older,
                source="seed-demo",
            ),
            SupplierItemPrice(
                supplier_item_id=item.id,
                unit_price=Decimal("13.10"),
                currency="BRL",
                observed_at=mid,
                source="seed-demo",
            ),
            SupplierItemPrice(
                supplier_item_id=item.id,
                unit_price=Decimal("13.00"),
                currency="BRL",
                observed_at=latest,
                source="receipt:demo",
            ),
        ]
    )
    admin.commit()

    listed = ctx["client"].get(
        f"/api/v1/organizations/{org.id}/suppliers",
        headers=headers(),
    )
    assert listed.status_code == 200, listed.text
    by_code = {row["code"]: row for row in listed.json()["data"]}
    # Regressão R026-011 2ª: lista sem active_item_count → UI “Nenhum item ativo”.
    assert "active_item_count" in by_code["FOR-MOINHO"]
    assert by_code["FOR-MOINHO"]["active_item_count"] == 1
    assert by_code["FOR-MOINHO"]["active_item_count"] != 0
    assert by_code["FOR-VAZIO"]["active_item_count"] == 0
    assert by_code["FOR-MOINHO"]["display_name"] == "Moinho Demo"

    detail = ctx["client"].get(
        f"/api/v1/organizations/{org.id}/suppliers/{moinho.id}",
        headers=headers(),
    )
    # Regressão R026-011 2ª: API antiga → 405 Method Not Allowed no detalhe.
    assert detail.status_code != 405, detail.text
    assert detail.status_code == 200, detail.text
    body = detail.json()["data"]
    assert body["code"] == "FOR-MOINHO"
    assert body["price_access"] is True
    assert len(body["items"]) == 1
    card = body["items"][0]
    assert card["supplier_sku"] == "SKU-FAR-25"
    assert card["unit"]["symbol"] == "kg"
    assert card["ingredient"]["display_name"] == "Farinha R011"
    assert card["latest_purchase"]["unit_price"].startswith("13")
    assert card["latest_purchase"]["observed_at"].startswith("2026-08-24")

    history = ctx["client"].get(
        f"/api/v1/organizations/{org.id}/items/{item.id}/prices",
        headers=headers(),
    )
    assert history.status_code == 200
    rows = history.json()["data"]
    assert len(rows) == 3
    assert [row["unit_price"][:4] for row in rows] == ["13.0", "13.1", "12.5"]
    assert rows[0]["is_latest"] is True
    assert all(row["is_latest"] is False for row in rows[1:])
    assert rows[0]["supplier_item_id"] == str(item.id)

    counts = active_item_counts_by_supplier(admin, org.id, {moinho.id, empty.id})
    assert counts[moinho.id] == 1
    assert counts.get(empty.id, 0) == 0

    items = [item]
    enrichments = load_item_enrichments(admin, org.id, items)
    ingredients = load_ingredient_refs(admin, org.id, items)
    assert enrichments[item.id][0]["code"] == "kg"
    assert ingredients[item.id]["display_name"] == "Farinha R011"
    ordered = prices_of(admin, item.id)
    assert Decimal(ordered[0].unit_price) == Decimal("13.00")

    missing = ctx["client"].get(
        f"/api/v1/organizations/{org.id}/suppliers/{uuid4()}",
        headers=headers(),
    )
    assert missing.status_code == 404

    _cleanup(ctx["client"])
    ctx["admin"].close()


def test_price_history_omitted_without_cost_permission(engine):
    """production: supplier.read sem price.record / costing.read / order.manage."""
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "r011-own", "owner", fake=fake)
    reader = _setup(engine, "r011-ps", "production", fake=fake, client=owner["client"])
    admin = owner["admin"]
    org = owner["organization"]
    kg = helpers.kilogram(admin)
    flour_version = helpers.published_ingredient(admin, org, kg, "FAR-V")
    supplier = Supplier(
        organization_id=org.id, code="FOR-V", display_name="Fornecedor V", status="active"
    )
    admin.add(supplier)
    admin.flush()
    item = SupplierItem(
        organization_id=org.id,
        supplier_id=supplier.id,
        ingredient_id=flour_version.ingredient_id,
        supplier_sku="SKU-V",
        package_quantity=Decimal("1"),
        measurement_unit_id=kg.id,
        status="active",
    )
    admin.add(item)
    admin.flush()
    admin.add(
        SupplierItemPrice(
            supplier_item_id=item.id,
            unit_price=Decimal("9.99"),
            currency="BRL",
            observed_at=datetime.now(UTC),
            source="seed-demo",
        )
    )
    helpers.membership(admin, org, reader["actor"], "production")
    admin.commit()

    detail = owner["client"].get(
        f"/api/v1/organizations/{org.id}/suppliers/{supplier.id}",
        headers=_headers(reader["token"], org.id),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()["data"]
    assert body["price_access"] is False
    assert body["items"][0]["latest_purchase"] is None

    history = owner["client"].get(
        f"/api/v1/organizations/{org.id}/items/{item.id}/prices",
        headers=_headers(reader["token"], org.id),
    )
    assert history.status_code == 200
    assert history.json()["data"] == []
    assert history.json()["price_access"] is False

    _cleanup(owner["client"])
    owner["admin"].close()
    reader["admin"].close()


def test_duplicate_supplier_code_rejected(engine):
    ctx = _setup(engine, "r011-dup")
    headers = lambda key=None: _headers(ctx["token"], ctx["organization"].id, key=key or uuid4())
    first = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/suppliers",
        headers=headers(),
        json={"code": "FOR-DUP", "display_name": "Um"},
    )
    assert first.status_code == 200, first.text
    second = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/suppliers",
        headers=headers(),
        json={"code": "FOR-DUP", "display_name": "Dois"},
    )
    assert second.status_code == 422, second.text
    _cleanup(ctx["client"])
    ctx["admin"].close()
