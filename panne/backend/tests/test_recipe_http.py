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
        "token": token,
        "fake": fake,
    }


def _h(ctx, **extra):
    return _headers(ctx["token"], ctx["organization"].id, **extra)


def _base(ctx, path: str) -> str:
    return f"/api/v1/organizations/{ctx['organization'].id}{path}"


def _publish_ingredient(ctx, code="FAR-R", name="Farinha de trigo"):
    created = ctx["client"].post(
        _base(ctx, "/ingredients"),
        headers=_h(ctx, key=uuid4()),
        json={
            "code": code,
            "display_name": name,
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": str(ctx["unit"].id),
        },
    )
    assert created.status_code == 200, created.text
    ingredient_id = created.json()["data"]["id"]
    detail = ctx["client"].get(_base(ctx, f"/ingredients/{ingredient_id}"), headers=_h(ctx)).json()
    version_id = detail["data"]["versions"][0]["id"]
    row_version = detail["data"]["versions"][0]["row_version"]
    nutrient = ctx["client"].post(
        _base(ctx, f"/ingredients/{ingredient_id}/versions/{version_id}/nutrients"),
        headers=_h(ctx, match=row_version),
        json={
            "nutrient_id": str(ctx["protein"].id),
            "value": "10",
            "value_status": "measured",
        },
    )
    assert nutrient.status_code == 200, nutrient.text
    published = ctx["client"].post(
        _base(ctx, f"/ingredients/{ingredient_id}/versions/{version_id}/publish"),
        headers=_h(ctx, key=uuid4(), match=row_version + 1),
    )
    assert published.status_code == 200, published.text
    return ingredient_id, version_id


def _create_recipe(ctx, code="PAO-1", name="Pão francês"):
    response = ctx["client"].post(
        _base(ctx, "/recipes"),
        headers=_h(ctx, key=uuid4()),
        json={"code": code, "display_name": name},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_permissions_and_rls(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "rec-own", "owner", fake=fake)
    baker = _setup(engine, "rec-bak", "baker_operator", fake=fake, client=owner["client"])
    created = _create_recipe(owner)
    listed = baker["client"].get(
        _base(owner, "/recipes"),
        headers=_headers(baker["token"], baker["organization"].id),
    )
    assert listed.status_code == 403
    denied = baker["client"].post(
        _base(baker, "/recipes"),
        headers=_h(baker, key=uuid4()),
        json={"code": "X", "display_name": "X"},
    )
    assert denied.status_code == 403
    visible = owner["client"].get(_base(owner, "/recipes"), headers=_h(owner))
    assert visible.status_code == 200
    assert any(item["id"] == created["data"]["id"] for item in visible.json()["items"])
    hidden = owner["client"].get(
        _base(baker, "/recipes"),
        headers=_headers(owner["token"], owner["organization"].id),
    )
    assert hidden.status_code == 403
    _cleanup(owner["client"])
    owner["admin"].close()
    baker["admin"].close()


def test_atomic_create_versioning_and_lifecycle(engine):
    ctx = _setup(engine, "rec-life")
    flour_id, flour_version = _publish_ingredient(ctx, "FAR-L", "Farinha")
    water_id, water_version = _publish_ingredient(ctx, "AGU-L", "Água")
    created = _create_recipe(ctx, "BAG-1", "Baguete")
    recipe_id = created["data"]["id"]
    assert created["data"]["current_version"]["status"] == "draft"
    detail = ctx["client"].get(_base(ctx, f"/recipes/{recipe_id}"), headers=_h(ctx)).json()
    version_id = detail["data"]["versions"][0]["id"]
    row_version = detail["data"]["versions"][0]["row_version"]
    unit_id = str(ctx["unit"].id)

    item = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/items"),
        headers=_h(ctx, match=row_version),
        json={
            "ingredient_version_id": flour_version,
            "sequence": 1,
            "net_quantity": "1000",
            "measurement_unit_id": unit_id,
            "correction_factor": "1",
            "is_flour_basis": True,
            "role": "ingredient",
        },
    )
    assert item.status_code == 200, item.text
    row_version += 1
    water = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/items"),
        headers=_h(ctx, match=row_version),
        json={
            "ingredient_version_id": water_version,
            "sequence": 2,
            "net_quantity": "650",
            "measurement_unit_id": unit_id,
            "is_flour_basis": False,
            "role": "ingredient",
        },
    )
    assert water.status_code == 200, water.text
    row_version += 1
    bakers = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/bakers"),
        headers=_h(ctx),
    ).json()["data"]
    assert bakers["flour_mass"] == "1000.000000"
    assert bakers["explained_absence"] is False
    percents = {row["id"]: row["bakers_percentage"] for row in bakers["items"]}
    assert percents[item.json()["data"]["id"]].startswith("100")
    assert percents[water.json()["data"]["id"]].startswith("65")

    step = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/steps"),
        headers=_h(ctx, match=row_version),
        json={
            "sequence": 1,
            "title": "Mistura",
            "instructions": "Juntar farinha e água.",
            "duration_seconds": 600,
            "temperature_celsius": "24",
        },
    )
    assert step.status_code == 200, step.text
    row_version += 1
    draft = ctx["client"].patch(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}"),
        headers=_h(ctx, match=row_version),
        json={
            "yield_units": 10,
            "target_unit_weight_g": "50",
            "expected_bake_loss_rate": "0.12",
        },
    )
    assert draft.status_code == 200, draft.text
    row_version = draft.json()["row_version"]
    yield_view = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/yield"),
        headers=_h(ctx),
    ).json()["data"]
    assert yield_view["yield_units"] == 10
    assert yield_view["base_net_mass"] is not None

    simulated = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/scale/simulate"),
        headers=_h(ctx),
        json={"mode": "total_dough_mass", "target_total_dough_mass": "3300"},
    )
    assert simulated.status_code == 200, simulated.text
    assert simulated.json()["data"]["persisted"] is False
    saved = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/scale"),
        headers=_h(ctx, key=uuid4()),
        json={"mode": "total_dough_mass", "target_total_dough_mass": "3300"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["algorithm_code"] == "deterministic_scale"

    trial = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/trials"),
        headers=_h(ctx, key=uuid4()),
        json={"code": f"TR-{uuid4().hex[:6]}", "notes": "ensaio de laboratório"},
    )
    assert trial.status_code == 200, trial.text
    trial_id = trial.json()["data"]["id"]
    assert trial_id and len(str(trial_id)) == 36, trial.json()
    started = ctx["client"].patch(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/trials/{trial_id}"),
        headers=_h(ctx),
        json={"status": "in_progress"},
    )
    assert started.status_code == 200
    measured = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/trials/{trial_id}/measurements"),
        headers=_h(ctx),
        json={"measurement_type": "temperature", "value": "24", "measurement_unit_id": unit_id},
    )
    assert measured.status_code == 200, measured.text
    done = ctx["client"].patch(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/trials/{trial_id}"),
        headers=_h(ctx),
        json={"status": "completed"},
    )
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "completed"

    nutrition = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/nutrition"),
        headers=_h(ctx, key=uuid4()),
    )
    assert nutrition.status_code == 200, nutrition.text
    assert "Prévia técnica incompleta" in nutrition.json()["data"]["disclaimer"]

    ref = ctx["client"].post(
        _base(ctx, "/recipe-references"),
        headers=_h(ctx, key=uuid4()),
        json={"title": "Manual interno", "source_type": "internal", "notes": "v1"},
    )
    assert ref.status_code == 200, ref.text
    identity_version = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}"), headers=_h(ctx)
    ).json()
    linked = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/references"),
        headers=_h(ctx, match=identity_version["row_version"]),
        json={"recipe_reference_id": ref.json()["data"]["id"], "role": "source"},
    )
    assert linked.status_code == 200, linked.text

    submitted = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/approvals"),
        headers=_h(ctx, key=uuid4()),
        json={"decision": "submitted", "notes": "pronta para revisão"},
    )
    assert submitted.status_code == 200
    approved = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/approvals"),
        headers=_h(ctx, key=uuid4()),
        json={"decision": "approved", "notes": "ok técnico"},
    )
    assert approved.status_code == 200
    blocked = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/publish"),
        headers=_h(ctx, key=uuid4(), match=999),
    )
    assert blocked.status_code == 409
    published = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/publish"),
        headers=_h(ctx, key=uuid4(), match=row_version),
    )
    assert published.status_code == 200, published.text
    assert published.json()["data"]["status"] == "published"
    frozen = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/items"),
        headers=_h(ctx, match=published.json()["row_version"]),
        json={
            "ingredient_version_id": flour_version,
            "sequence": 3,
            "net_quantity": "10",
            "measurement_unit_id": unit_id,
        },
    )
    assert frozen.status_code == 409
    sheet = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/sheet"),
        headers=_h(ctx),
    )
    assert sheet.status_code == 200
    assert sheet.json()["data"]["payload_sha256"]
    assert sheet.json()["data"]["kind"] == "ficha_tecnica_derivada"

    key = uuid4()
    first = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions"),
        headers=_h(ctx, key=key),
        json={"source_version_id": version_id},
    )
    second = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions"),
        headers=_h(ctx, key=key),
        json={"source_version_id": version_id},
    )
    assert first.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]
    assert first.json()["data"]["status"] == "draft"
    retired = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/retire"),
        headers=_h(ctx, key=uuid4(), match=published.json()["row_version"]),
    )
    assert retired.status_code == 200
    assert retired.json()["data"]["status"] == "retired"
    completeness = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}/versions/{first.json()['data']['id']}/completeness"),
        headers=_h(ctx),
    )
    assert completeness.status_code == 200
    assert "items" in completeness.json()["data"]
    _cleanup(ctx["client"])
    ctx["admin"].close()


def test_publish_requires_approval_and_baker_reads_released(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "rec-appr", "owner", fake=fake)
    baker = _setup(engine, "rec-appr-b", "baker_operator", fake=fake, client=owner["client"])
    _publish_ingredient(owner, "FAR-P", "Farinha")
    created = _create_recipe(owner, "PAO-P", "Pão")
    recipe_id = created["data"]["id"]
    detail = owner["client"].get(_base(owner, f"/recipes/{recipe_id}"), headers=_h(owner)).json()
    version_id = detail["data"]["versions"][0]["id"]
    unpublished = baker["client"].get(
        _base(baker, "/recipes"),
        headers=_h(baker),
    )
    assert unpublished.status_code == 200
    assert unpublished.json()["items"] == []
    missing = owner["client"].post(
        _base(owner, f"/recipes/{recipe_id}/versions/{version_id}/publish"),
        headers=_h(owner, key=uuid4(), match=detail["data"]["versions"][0]["row_version"]),
    )
    assert missing.status_code == 409
    assert missing.json()["code"] == "aprovacao_obrigatoria"
    owner["client"].post(
        _base(owner, f"/recipes/{recipe_id}/versions/{version_id}/approvals"),
        headers=_h(owner, key=uuid4()),
        json={"decision": "rejected", "notes": "falta etapa"},
    )
    still = owner["client"].post(
        _base(owner, f"/recipes/{recipe_id}/versions/{version_id}/publish"),
        headers=_h(owner, key=uuid4(), match=detail["data"]["versions"][0]["row_version"]),
    )
    assert still.status_code == 409
    _cleanup(owner["client"])
    owner["admin"].close()
    baker["admin"].close()
