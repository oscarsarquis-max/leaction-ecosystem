from datetime import UTC, datetime
from uuid import uuid4

from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from sqlalchemy.orm import sessionmaker
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
    protein = helpers.nutrient(admin, unit, f"prot-{slug[-6:]}")
    gluten = helpers.allergen(admin, f"glu-{slug[-6:]}")
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
        "protein": protein,
        "allergen": gluten,
        "token": token,
    }


def _create_ingredient(ctx, code="FAR-1", name="Farinha"):
    response = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=_headers(ctx["token"], ctx["organization"].id, key=uuid4()),
        json={
            "code": code,
            "display_name": name,
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": str(ctx["unit"].id),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_permissions_and_rls(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "ing-own", "owner", fake=fake)
    baker = _setup(engine, "ing-bak", "baker_operator", fake=fake, client=owner["client"])
    created = _create_ingredient(owner)
    listed = baker["client"].get(
        f"/api/v1/organizations/{owner['organization'].id}/ingredients",
        headers=_headers(baker["token"], baker["organization"].id),
    )
    assert listed.status_code == 403
    denied = baker["client"].post(
        f"/api/v1/organizations/{baker['organization'].id}/ingredients",
        headers=_headers(baker["token"], baker["organization"].id, key=uuid4()),
        json={
            "code": "X",
            "display_name": "X",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": str(baker["unit"].id),
        },
    )
    assert denied.status_code == 403
    visible = owner["client"].get(
        f"/api/v1/organizations/{owner['organization'].id}/ingredients",
        headers=_headers(owner["token"], owner["organization"].id),
    )
    assert visible.status_code == 200
    assert any(item["id"] == created["data"]["id"] for item in visible.json()["items"])
    hidden = owner["client"].get(
        f"/api/v1/organizations/{baker['organization'].id}/ingredients",
        headers=_headers(owner["token"], owner["organization"].id),
    )
    assert hidden.status_code == 403
    _cleanup(owner["client"])
    _cleanup(baker["client"])
    owner["admin"].close()
    baker["admin"].close()


def test_lifecycle_composition_nutrition_supplier(engine):
    ctx = _setup(engine, "ing-life")

    def headers(**extra):
        return _headers(ctx["token"], ctx["organization"].id, **extra)

    created = _create_ingredient(ctx, "FER-1", "Fermento")
    ingredient_id = created["data"]["id"]
    detail = (
        ctx["client"]
        .get(
            f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}",
            headers=headers(),
        )
        .json()
    )
    version_id = detail["data"]["versions"][0]["id"]
    row_version = detail["data"]["versions"][0]["row_version"]
    unit_id = str(ctx["unit"].id)

    again = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=headers(key=uuid4()),
        json={
            "code": "FER-1",
            "display_name": "Fermento",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": unit_id,
        },
    )
    # unique code is a domain/db error, not silent overwrite
    assert again.status_code in {400, 409, 422}

    nutrient = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}/nutrients",
        headers=headers(match=row_version),
        json={
            "nutrient_id": str(ctx["protein"].id),
            "value": "12.5",
            "value_status": "measured",
            "method_or_source": "rótulo do fabricante",
        },
    )
    assert nutrient.status_code == 200, nutrient.text
    row_version += 1
    loq = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}/nutrients",
        headers=headers(match=row_version),
        json={
            "nutrient_id": str(ctx["protein"].id),
            "value_status": "below_loq",
            "limit_of_quantification": "0.1",
            "loq_unit_id": unit_id,
        },
    )
    assert loq.status_code == 200
    assert loq.json()["data"]["value"] is None
    row_version += 1
    allergen = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}/allergens",
        headers=headers(match=row_version),
        json={
            "allergen_id": str(ctx["allergen"].id),
            "presence": "contains",
            "evidence_note": "rótulo",
        },
    )
    assert allergen.status_code == 200
    row_version += 1
    published = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}/publish",
        headers=headers(key=uuid4(), match=row_version),
    )
    assert published.status_code == 200, published.text
    assert published.json()["data"]["status"] == "published"
    frozen = ctx["client"].patch(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}",
        headers=headers(match=published.json()["row_version"]),
        json={"notes": "não pode"},
    )
    assert frozen.status_code == 409
    key = uuid4()
    first = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions",
        headers=headers(key=key),
        json={"source_version_id": version_id, "nutrition_basis_unit_id": unit_id},
    )
    second = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions",
        headers=headers(key=key),
        json={"source_version_id": version_id, "nutrition_basis_unit_id": unit_id},
    )
    assert first.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]
    stale = ctx["client"].patch(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{first.json()['data']['id']}",
        headers=headers(match=999),
        json={"notes": "stale"},
    )
    assert stale.status_code == 409
    retired = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{version_id}/retire",
        headers=headers(key=uuid4(), match=published.json()["row_version"]),
    )
    assert retired.status_code == 200
    assert retired.json()["data"]["status"] == "retired"
    flour = _create_ingredient(ctx, "FAR-C", "Farinha base")
    flour_version = (
        ctx["client"]
        .get(
            f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{flour['data']['id']}",
            headers=headers(),
        )
        .json()["data"]["versions"][0]["id"]
    )
    draft_id = first.json()["data"]["id"]
    draft_rv = first.json()["row_version"]
    cycle = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{draft_id}/composition",
        headers=headers(match=draft_rv),
        json={
            "component_version_id": draft_id,
            "component_type": "constituent",
            "quantity": "10",
            "measurement_unit_id": unit_id,
            "sequence": 1,
        },
    )
    assert cycle.status_code == 422
    composed = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{draft_id}/composition",
        headers=headers(match=draft_rv),
        json={
            "component_version_id": flour_version,
            "component_type": "constituent",
            "quantity": "80",
            "measurement_unit_id": unit_id,
            "sequence": 1,
        },
    )
    assert composed.status_code == 200, composed.text
    supplier = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/suppliers",
        headers=headers(key=uuid4()),
        json={"code": "FOR-1", "display_name": "Moinho Central"},
    )
    assert supplier.status_code == 200
    item = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/suppliers/{supplier.json()['data']['id']}/items",
        headers=headers(key=uuid4()),
        json={
            "ingredient_id": ingredient_id,
            "supplier_sku": "SKU-1",
            "package_quantity": "25",
            "measurement_unit_id": unit_id,
        },
    )
    assert item.status_code == 200
    price = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/items/{item.json()['data']['id']}/prices",
        headers=headers(key=uuid4()),
        json={
            "unit_price": "18.40",
            "currency": "BRL",
            "observed_at": datetime.now(UTC).isoformat(),
            "source": "nota",
        },
    )
    assert price.status_code == 200
    history = ctx["client"].get(
        f"/api/v1/organizations/{ctx['organization'].id}/items/{item.json()['data']['id']}/prices",
        headers=headers(),
    )
    assert len(history.json()["data"]) == 1
    completeness = ctx["client"].get(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients/{ingredient_id}/versions/{draft_id}/completeness",
        headers=headers(),
    )
    assert completeness.status_code == 200
    catalog = ctx["client"].get(
        f"/api/v1/organizations/{ctx['organization'].id}/catalog/units",
        headers=headers(),
    )
    assert catalog.status_code == 200
    search = ctx["client"].get(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=headers(),
        params={"q": "Fermento", "limit": 10, "offset": 0},
    )
    assert search.json()["total"] >= 1
    _cleanup(ctx["client"])
    ctx["admin"].close()
