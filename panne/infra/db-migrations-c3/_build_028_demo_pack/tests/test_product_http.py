from uuid import uuid4

import pytest
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.product_catalog.commands import assert_product_allows_production
from app.modules.production_planning.errors import ValidationError
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
        "token": token,
        "fake": fake,
    }


def _h(ctx, **extra):
    return _headers(ctx["token"], ctx["organization"].id, **extra)


def _base(ctx, path: str) -> str:
    return f"/api/v1/organizations/{ctx['organization'].id}{path}"


def test_product_crud_and_filters(engine):
    ctx = _setup(engine, "prod-crud")
    try:
        created = ctx["client"].post(
            _base(ctx, "/products"),
            headers=_h(ctx, key=uuid4()),
            json={
                "code": "SUCO-1",
                "display_name": "Suco engarrafado",
                "supply_mode": "purchased",
                "purpose": "final",
            },
        )
        assert created.status_code == 200, created.text
        product_id = created.json()["data"]["id"]
        assert created.json()["data"]["recipe_status_label"] == "Não se aplica"

        produced = ctx["client"].post(
            _base(ctx, "/products"),
            headers=_h(ctx, key=uuid4()),
            json={
                "code": "PAO-X",
                "display_name": "Pão teste",
                "supply_mode": "produced",
                "purpose": "final",
            },
        )
        assert produced.status_code == 200, produced.text
        assert produced.json()["data"]["recipe_status_label"] == "Sem receita vigente"

        listed = ctx["client"].get(
            _base(ctx, "/products"),
            headers=_h(ctx),
            params={"supply_mode": "purchased"},
        )
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1
        assert all(item["supply_mode"] == "purchased" for item in listed.json()["items"])

        detail = ctx["client"].get(_base(ctx, f"/products/{product_id}"), headers=_h(ctx))
        assert detail.status_code == 200
        row_version = detail.json()["row_version"]
        patched = ctx["client"].patch(
            _base(ctx, f"/products/{product_id}"),
            headers=_h(ctx, key=uuid4(), match=row_version),
            json={"display_name": "Suco de laranja"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["data"]["display_name"] == "Suco de laranja"

        summary = ctx["client"].get(_base(ctx, "/products/summary"), headers=_h(ctx))
        assert summary.status_code == 200
        data = summary.json()["data"]
        assert data["total"] >= 2
        assert data["purchased"] >= 1
        assert data["produced_without_recipe"] >= 1
    finally:
        _cleanup(ctx["client"])
        ctx["admin"].close()


def test_product_rls_and_permissions(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "prod-own", "owner", fake=fake)
    baker = _setup(engine, "prod-bak", "baker_operator", fake=fake, client=owner["client"])
    try:
        created = owner["client"].post(
            _base(owner, "/products"),
            headers=_h(owner, key=uuid4()),
            json={"code": "X1", "display_name": "Item A", "supply_mode": "produced"},
        )
        assert created.status_code == 200
        listed = baker["client"].get(
            _base(owner, "/products"),
            headers=_headers(baker["token"], baker["organization"].id),
        )
        assert listed.status_code == 403
        denied = baker["client"].post(
            _base(baker, "/products"),
            headers=_headers(baker["token"], baker["organization"].id, key=uuid4()),
            json={"code": "X2", "display_name": "Item B"},
        )
        assert denied.status_code == 403
    finally:
        _cleanup(owner["client"])
        owner["admin"].close()
        baker["admin"].close()


def test_family_cycle_rejected(engine):
    ctx = _setup(engine, "prod-fam")
    try:
        parent = ctx["client"].post(
            _base(ctx, "/product-families"),
            headers=_h(ctx, key=uuid4()),
            json={"code": "PADARIA", "display_name": "Padaria"},
        )
        assert parent.status_code == 200, parent.text
        parent_id = parent.json()["data"]["id"]
        child = ctx["client"].post(
            _base(ctx, "/product-families"),
            headers=_h(ctx, key=uuid4()),
            json={"code": "PAES", "display_name": "Pães", "parent_id": parent_id},
        )
        assert child.status_code == 200, child.text
        child_id = child.json()["data"]["id"]
        cycle = ctx["client"].patch(
            _base(ctx, f"/product-families/{parent_id}"),
            headers=_h(ctx, key=uuid4(), match=parent.json()["row_version"]),
            json={"parent_id": child_id},
        )
        assert cycle.status_code == 409
    finally:
        _cleanup(ctx["client"])
        ctx["admin"].close()


def test_purchased_and_produced_without_recipe_block_order(engine):
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"block-{uuid4().hex[:6]}"
    organization = helpers.org(admin, slug)
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, "owner")
    purchased = helpers.technical_product(admin, organization, "BUY-1")
    purchased.supply_mode = "purchased"
    produced = helpers.technical_product(admin, organization, "MAKE-1")
    produced.supply_mode = "produced"
    admin.commit()
    try:
        with pytest.raises(ValidationError, match="comprado"):
            assert_product_allows_production(
                admin,
                organization_id=organization.id,
                technical_product_id=purchased.id,
            )
        with pytest.raises(ValidationError, match="Sem receita vigente"):
            assert_product_allows_production(
                admin,
                organization_id=organization.id,
                technical_product_id=produced.id,
            )
        recipe = helpers.formulation(admin, produced, "F-MAKE")
        version = helpers.formulation_version(admin, recipe)
        helpers.approve_version(admin, version, actor)
        from app.modules.formula_lab.rules import publish_formulation_version

        publish_formulation_version(admin, version)
        admin.commit()
        assert_product_allows_production(
            admin,
            organization_id=organization.id,
            technical_product_id=produced.id,
        )
    finally:
        admin.close()
