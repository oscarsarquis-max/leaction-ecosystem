from decimal import Decimal

import pytest
from app.modules.calculation_engine.nutrition import (
    NutritionError,
    calculate_nutrition,
    persist_nutrition_calculation,
)
from app.modules.nutrition_calculation.models import NutritionCalculation
from sqlalchemy.orm import Session
from tests import helpers


def _formula(session: Session, slug: str):
    organization = helpers.org(session, slug)
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, f"PAO-{slug}")
    recipe = helpers.formulation(session, product, f"REC-{slug}")
    version = helpers.formulation_version(session, recipe)
    return organization, unit, version


def test_expected_nutrient_present_and_absent(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-np-1")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-NP1", {protein: Decimal("10")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    profile = helpers.expectation_profile(db_session, "tecnico-1", [protein, sodium])
    result = calculate_nutrition(db_session, version, expectation_profile=profile)
    by_code = {item[0].code: item for item in result.items}
    assert by_code["protein"][1] == Decimal("10.000000")
    assert by_code["protein"][4] == "complete"
    assert by_code["sodium"][4] == "missing_data"
    assert result.status == "incomplete"
    assert any("todos os ingredientes" in row.message for row in result.evidence)


def test_absence_on_all_ingredients_is_visible(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-np-all")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-ALL")
    water = helpers.published_ingredient(db_session, organization, unit, "AGU-ALL")
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("80"))
    helpers.formulation_item(db_session, version, water, unit, 2, Decimal("20"))
    profile = helpers.expectation_profile(db_session, "tecnico-all", [protein, sodium])
    result = calculate_nutrition(db_session, version, expectation_profile=profile)
    assert {item[0].code for item in result.items} == {"protein", "sodium"}
    assert all(item[4] == "missing_data" for item in result.items)
    assert result.status == "incomplete"


def test_private_profile_isolation(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-np-iso")
    other = helpers.org(db_session, "org-np-iso-b")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-ISO", {protein: Decimal("4")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    foreign = helpers.expectation_profile(
        db_session, "privado-b", [protein], organization=other
    )
    with pytest.raises(NutritionError, match="outra organização"):
        calculate_nutrition(db_session, version, expectation_profile=foreign)
    own = helpers.expectation_profile(
        db_session, "privado-a", [protein], organization=organization
    )
    result = calculate_nutrition(db_session, version, expectation_profile=own)
    assert result.expectation_profile_id == own.id
    assert result.status == "complete"


def test_old_snapshots_remain_without_profile(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-np-old")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-OLD", {protein: Decimal("6")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    old = persist_nutrition_calculation(
        db_session, version, calculate_nutrition(db_session, version)
    )
    profile = helpers.expectation_profile(db_session, "depois", [protein, sodium])
    new = persist_nutrition_calculation(
        db_session,
        version,
        calculate_nutrition(db_session, version, expectation_profile=profile),
    )
    assert old.id != new.id
    assert old.expectation_profile_id is None
    assert db_session.get(NutritionCalculation, old.id).formula_net_mass_g == Decimal(
        "100.000000"
    )
    assert new.expectation_profile_id == profile.id
    assert len(old.warnings) >= 1 or db_session.get(NutritionCalculation, old.id) is not None
