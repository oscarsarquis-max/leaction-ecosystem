from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.ingredient_catalog.models import IngredientAllergen, IngredientComposition
from app.modules.labeling_compliance.applicability import classify_profile, front_labeling_scope
from app.modules.labeling_compliance.constants import (
    SOLID_ADDED_SUGARS_G,
    SOLID_SATURATED_FAT_G,
    SOLID_SODIUM_MG,
)
from app.modules.labeling_compliance.models import (
    LabelingAssessment,
    LabelingDossier,
    LabelingDossierVersion,
    LabelingFinding,
)
from app.modules.labeling_compliance.rounding import round_declared, round_energy_kcal, round_sodium_mg
from app.modules.nutrition_calculation.models import NutritionCalculation, NutritionCalculationItem
from sqlalchemy.orm import Session, sessionmaker
from tests import helpers
from tests.jwt_support import ISSUER
from tests.test_production_api import _cleanup, _client, _headers
from tests.test_recipe_http import _base, _create_recipe, _h, _publish_ingredient, _setup


def _ensure_head(engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _labeling_schema(engine) -> None:
    _ensure_head(engine)


COMPLETE_PROFILE = {
    "jurisdiction": "BR",
    "evaluation_date": "2026-08-23",
    "packed_food": True,
    "packed_away_from_consumer": True,
    "packed_at_point_of_sale": False,
    "packed_on_request": False,
    "same_establishment": False,
    "sales_channel": "own_store",
    "food_service": False,
    "physical_state": "solid",
    "ready_to_eat": True,
    "regulatory_category_code": "pao",
    "category_confirmed": True,
    "package_area_cm2": "200",
    "net_content_g": "500",
    "servings_per_package": 10,
    "purpose": "commercial_sale",
    "destination_market": "BR",
}


def test_rounding_and_insignificant_values() -> None:
    assert round_energy_kcal(Decimal("4")) == Decimal("0")
    assert round_energy_kcal(Decimal("12")) == Decimal("10")
    assert round_energy_kcal(Decimal("86")) == Decimal("90")
    assert round_declared("protein", Decimal("0.4")) == Decimal("0")
    assert round_declared("protein", Decimal("3.26")) == Decimal("3.3")
    assert round_declared("saturated_fat", Decimal("5.24")) == Decimal("5.0")
    assert round_sodium_mg(Decimal("4")) == Decimal("0")
    assert round_sodium_mg(Decimal("137")) == Decimal("135")
    assert round_sodium_mg(Decimal("612")) == Decimal("610")


def test_profile_incomplete_is_not_exemption() -> None:
    assert classify_profile({"jurisdiction": "BR"}) == "incomplete"
    assert classify_profile(COMPLETE_PROFILE | {"category_confirmed": False}) == "incomplete"
    assert classify_profile(COMPLETE_PROFILE | {"regulatory_category_code": "ambigua"}) == "incomplete"
    assert classify_profile(COMPLETE_PROFILE) == "complete"


def test_not_applicable_requires_proof() -> None:
    class _P:
        completeness = "complete"
        physical_state = "solid"
        packed_food = False
        packed_away_from_consumer = False
        same_establishment = True
        packed_on_request = True

    assert front_labeling_scope(_P()) == "not_applicable"
    assert front_labeling_scope(None) == "insufficient_context"


def test_front_thresholds() -> None:
    assert SOLID_ADDED_SUGARS_G == Decimal("15")
    assert SOLID_SATURATED_FAT_G == Decimal("6")
    assert SOLID_SODIUM_MG == Decimal("600")


def _calc(session: Session, organization, version, nutrients: dict[str, Decimal], unit):
    row = NutritionCalculation(
        organization_id=organization.id,
        formulation_version_id=version.id,
        status="complete",
        calculation_basis="per_100g",
        formulation_version_status=version.status,
        is_simulation=False,
        formula_net_mass_g=Decimal("100"),
        algorithm_name="technical_nutrition_raw",
        algorithm_version="1",
        rounding_policy="none",
    )
    session.add(row)
    session.flush()
    for code, value in nutrients.items():
        definition = helpers.nutrient(session, unit, code)
        session.add(
            NutritionCalculationItem(
                organization_id=organization.id,
                nutrition_calculation_id=row.id,
                nutrient_definition_id=definition.id,
                measurement_unit_id=unit.id,
                whole_formula_amount=value,
                per_100g_amount=value,
                completeness_status="complete",
            )
        )
    session.flush()
    return row


def test_missing_nutrient_is_not_zero(db_session: Session) -> None:
    from app.modules.labeling_compliance.nutrition_declaration import project_declaration

    organization = helpers.org(db_session, "lab-miss")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-M")
    recipe = helpers.formulation(db_session, product, "REC-M")
    version = helpers.formulation_version(db_session, recipe)
    calc = _calc(db_session, organization, version, {"protein": Decimal("10")}, unit)
    lines = {row["nutrient_code"]: row for row in project_declaration(db_session, calc, category_code="pao", servings=10)}
    assert lines["added_sugars"]["declared_per_100g"] is None
    assert lines["added_sugars"]["completeness"] == "insufficient_evidence"
    assert lines["protein"]["declared_per_100g"] == Decimal("10.0")


def test_compound_ingredients_and_warnings(db_session: Session) -> None:
    from app.modules.labeling_compliance.ingredients import candidate_ingredients
    from app.modules.labeling_compliance.warnings import candidate_warnings

    organization = helpers.org(db_session, "lab-ing")
    unit = helpers.gram(db_session)
    actor = helpers.user(db_session, "lab-ing@example.com")
    product = helpers.technical_product(db_session, organization, "PAO-C")
    recipe = helpers.formulation(db_session, product, "REC-C")
    version = helpers.formulation_version(db_session, recipe, created_by_user_id=actor.id)
    mix = helpers.draft_ingredient(db_session, organization, unit, "MIX-C", ingredient_type="composite")
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-C")
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=mix.id,
            component_ingredient_version_id=flour.id,
            component_type="constituent",
            quantity=Decimal("80"),
            measurement_unit_id=unit.id,
            sequence=1,
        )
    )
    gluten = helpers.allergen(db_session, "gluten")
    db_session.add(
        IngredientAllergen(
            organization_id=organization.id,
            ingredient_version_id=mix.id,
            allergen_id=gluten.id,
            presence="contains",
            evidence_note="rótulo",
        )
    )
    helpers.publish_ingredient_version(db_session, mix)
    helpers.formulation_item(db_session, version, mix, unit, 1, Decimal("200"))
    db_session.flush()
    items = candidate_ingredients(db_session, version.id)
    assert items[0]["compound"] is True
    assert items[0]["components"]
    warnings = {row["code"]: row for row in candidate_warnings(db_session, version.id)}
    assert warnings["gluten_contains"]["result"] == "manual_review_required"
    assert warnings["may_contain"]["result"] == "insufficient_evidence"
    assert warnings["lactose"]["result"] == "insufficient_evidence"


def _recipe_version(ctx):
    flour_id, flour_version = _publish_ingredient(ctx)
    created = _create_recipe(ctx, "PAO-L", "Pão de rotulagem")
    recipe_id = created["data"]["id"]
    detail = ctx["client"].get(_base(ctx, f"/recipes/{recipe_id}"), headers=_h(ctx)).json()
    version_id = detail["data"]["versions"][0]["id"]
    row_version = detail["data"]["versions"][0]["row_version"]
    item = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/items"),
        headers=_h(ctx, match=row_version),
        json={
            "ingredient_version_id": flour_version,
            "sequence": 1,
            "net_quantity": "1000",
            "measurement_unit_id": str(ctx["unit"].id),
            "correction_factor": "1",
            "is_flour_basis": True,
            "role": "ingredient",
        },
    )
    assert item.status_code == 200, item.text
    return version_id


def test_http_permissions_rls_and_no_auto_approval(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "lab-own", "owner", fake=fake)
    baker = _setup(engine, "lab-bak", "baker_operator", fake=fake, client=owner["client"])
    version_id = _recipe_version(owner)
    create_key = uuid4()
    created = owner["client"].post(
        _base(owner, "/labeling/dossiers"),
        headers=_h(owner, key=create_key),
        json={"formulation_version_id": version_id},
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["disclaimer"].startswith("Proposta técnica")
    assert "conforme anvisa" not in created.text.lower()
    dossier_id = created.json()["data"]["id"]
    replay = owner["client"].post(
        _base(owner, "/labeling/dossiers"),
        headers=_h(owner, key=create_key),
        json={"formulation_version_id": version_id},
    )
    assert replay.status_code == 200
    assert replay.json()["data"]["id"] == dossier_id

    denied = baker["client"].post(
        _base(baker, "/labeling/dossiers"),
        headers=_h(baker, key=uuid4()),
        json={"formulation_version_id": version_id},
    )
    assert denied.status_code == 403
    hidden = baker["client"].get(
        _base(owner, "/labeling/dossiers"),
        headers=_headers(baker["token"], baker["organization"].id),
    )
    assert hidden.status_code == 403
    other = owner["client"].get(
        _base(baker, f"/labeling/dossiers/{dossier_id}"),
        headers=_headers(owner["token"], owner["organization"].id),
    )
    assert other.status_code == 403

    conflict = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/profile"),
        headers=_h(owner, match=99),
        json=COMPLETE_PROFILE,
    )
    assert conflict.status_code == 409

    profile = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/profile"),
        headers=_h(owner, match=created.json()["row_version"]),
        json={k: v for k, v in COMPLETE_PROFILE.items() if k != "category_confirmed"},
    )
    assert profile.status_code == 200
    assert profile.json()["data"]["completeness"] == "incomplete"
    evaluated = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/evaluate"),
        headers=_h(owner, key=uuid4(), match=profile.json()["row_version"]),
    )
    assert evaluated.status_code == 200, evaluated.text
    detail = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}"), headers=_h(owner)).json()
    results = {item["rule_code"]: item["result"] for item in detail["data"]["current"]["findings"]}
    assert results["applicability_complete"] == "insufficient_context"
    assert results["fop_scope"] == "insufficient_context"
    assert detail["data"]["certified"] is False
    assert detail["data"]["conforme_anvisa"] is False
    assert any(item["status"] == "pending" for item in detail["data"]["current"]["mandatory"])

    complete = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/profile"),
        headers=_h(owner, match=detail["row_version"]),
        json=COMPLETE_PROFILE,
    )
    assert complete.json()["data"]["completeness"] == "complete"
    again = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/evaluate"),
        headers=_h(owner, key=uuid4(), match=complete.json()["row_version"]),
    )
    assert again.status_code == 200
    latest = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}"), headers=_h(owner)).json()
    assert latest["data"]["current"]["version"]["version_number"] == 2
    assert latest["data"]["current"]["front_of_pack"]["magnifier_required"] is None
    versions = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}/versions"), headers=_h(owner)).json()
    compared = owner["client"].get(
        _base(owner, f"/labeling/dossiers/{dossier_id}/compare"),
        headers=_h(owner),
        params={"left": versions["items"][1]["id"], "right": versions["items"][0]["id"]},
    )
    assert compared.status_code == 200
    review = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/review"),
        headers=_h(owner, key=uuid4(), match=latest["row_version"]),
        json={"decision": "accepted", "notes": "revisão humana, sem certificado"},
    )
    assert review.status_code == 200
    reviewed = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}"), headers=_h(owner)).json()
    assert reviewed["data"]["status"] == "reviewed"
    assert reviewed["data"]["certified"] is False
    blocked = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/mandatory"),
        headers=_h(owner, match=reviewed["row_version"]),
        json={"items": [{"code": "lote", "value": "L1"}]},
    )
    assert blocked.status_code == 409
    rendered = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}/render"), headers=_h(owner))
    assert rendered.status_code == 200
    assert "Não é rótulo final" in rendered.json()["data"]["html"]
    after = owner["client"].get(_base(owner, f"/labeling/dossiers/{dossier_id}"), headers=_h(owner)).json()
    assert after["row_version"] == reviewed["row_version"]
    invalid = owner["client"].post(
        _base(owner, f"/labeling/dossiers/{dossier_id}/invalidate"),
        headers=_h(owner, match=after["row_version"]),
        json={"reason": "norma nova"},
    )
    assert invalid.status_code == 200
    sources = owner["client"].get(_base(owner, "/labeling/sources"), headers=_h(owner))
    assert sources.status_code == 200
    assert all(item["jurisdiction"] == "BR" for item in sources.json()["items"])
    baker_read = baker["client"].get(_base(baker, "/labeling/dossiers"), headers=_h(baker))
    assert baker_read.status_code == 200
    assert baker_read.json()["total"] == 0
    _cleanup(owner["client"])
    owner["admin"].close()
    baker["admin"].close()


def test_fop_limits_and_physical_delete(db_session: Session) -> None:
    from app.modules.labeling_compliance.evaluate import evaluate_dossier
    from app.modules.labeling_compliance.models import LabelingApplicabilityProfile

    organization = helpers.org(db_session, "lab-fop")
    unit = helpers.gram(db_session)
    actor = helpers.user(db_session, "lab-fop@example.com")
    product = helpers.technical_product(db_session, organization, "PAO-F")
    recipe = helpers.formulation(db_session, product, "REC-F")
    version = helpers.formulation_version(db_session, recipe, created_by_user_id=actor.id)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-F")
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    calc = _calc(
        db_session,
        organization,
        version,
        {
            "added_sugars": Decimal("15"),
            "saturated_fat": Decimal("4.9"),
            "sodium": Decimal("610"),
            "energy_kcal": Decimal("300"),
            "carbohydrate": Decimal("50"),
            "total_sugars": Decimal("16"),
            "protein": Decimal("8"),
            "total_fat": Decimal("10"),
            "trans_fat": Decimal("0"),
            "fiber": Decimal("2"),
        },
        unit,
    )
    dossier = LabelingDossier(
        organization_id=organization.id,
        formulation_id=recipe.id,
        formulation_version_id=version.id,
        nutrition_calculation_id=calc.id,
        created_by_user_id=actor.id,
    )
    db_session.add(dossier)
    db_session.flush()
    profile = LabelingApplicabilityProfile(
        organization_id=organization.id,
        labeling_dossier_id=dossier.id,
        jurisdiction="BR",
        evaluation_date=__import__("datetime").date(2026, 8, 23),
        packed_food=True,
        packed_away_from_consumer=True,
        packed_at_point_of_sale=False,
        packed_on_request=False,
        same_establishment=False,
        sales_channel="own_store",
        food_service=False,
        physical_state="solid",
        ready_to_eat=True,
        regulatory_category_code="pao",
        category_confirmed=True,
        net_content_g=Decimal("500"),
        servings_per_package=10,
        purpose="commercial_sale",
        destination_market="BR",
        completeness="complete",
    )
    db_session.add(profile)
    db_session.flush()
    evaluated = evaluate_dossier(db_session, dossier, actor_user_id=actor.id, profile=profile)
    from app.modules.labeling_compliance.models import LabelingFrontOfPack

    front = db_session.query(LabelingFrontOfPack).filter_by(labeling_dossier_version_id=evaluated.id).one()
    assert front.added_sugars_result == "high"
    assert front.saturated_fat_result == "below"
    assert front.sodium_result == "high"
    assert front.magnifier_required is True
    assert "15" in front.compared["thresholds"]["added_sugars"]
    findings = list(db_session.query(LabelingFinding).all())
    assert all("conforme anvisa" not in row.explanation.lower() for row in findings)
    import pytest

    blocked_delete = db_session.begin_nested()
    with pytest.raises(Exception, match="physical_delete_forbidden"):
        db_session.delete(evaluated)
        db_session.flush()
    blocked_delete.rollback()
    blocked_update = db_session.begin_nested()
    with pytest.raises(Exception, match="append_only"):
        row = db_session.query(LabelingAssessment).filter_by(labeling_dossier_version_id=evaluated.id).one()
        row.proposal_summary = "alterado"
        db_session.flush()
    blocked_update.rollback()
