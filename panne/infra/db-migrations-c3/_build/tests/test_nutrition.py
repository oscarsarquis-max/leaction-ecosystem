from decimal import Decimal
from inspect import getsource
from pathlib import Path

import pytest
from app.modules.calculation_engine import nutrition as nutrition_engine
from app.modules.calculation_engine.nutrition import (
    ALGORITHM_NAME,
    BASIS_PER_100G,
    BASIS_PORTION,
    NutritionError,
    calculate_nutrition,
    invalidate_nutrition_calculation,
    persist_nutrition_calculation,
    reconstruct_whole_formula,
    require_compatible_conversion,
)
from app.modules.formula_lab.models import FormulationVersion
from app.modules.ingredient_catalog.models import IngredientComposition
from app.modules.nutrition_calculation.access import (
    NutritionAccessError,
    get_nutrition_calculation,
)
from app.modules.nutrition_calculation.models import (
    CalculationEvidence,
    NutritionCalculation,
    NutritionCalculationItem,
)
from sqlalchemy.orm import Session
from tests import helpers


def _formula(session: Session, slug: str):
    organization = helpers.org(session, slug)
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, "PAO-N")
    recipe = helpers.formulation(session, product, "REC-N")
    version = helpers.formulation_version(session, recipe)
    return organization, unit, version


def test_single_ingredient_and_known_zero(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-1")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-N1", {protein: Decimal("0")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("200"))
    result = calculate_nutrition(db_session, version)
    assert result.status == "complete"
    assert result.formula_net_mass_g == Decimal("200.000000")
    assert result.items[0][1] == Decimal("0.000000")
    assert result.items[0][4] == "complete"
    assert result.expected_final_mass_g is None
    assert result.items[0][2] is None


def test_multiple_ingredients_and_nutrients(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-m")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    flour = helpers.published_dossier(
        db_session,
        organization,
        unit,
        "FAR-M",
        {protein: Decimal("10"), sodium: Decimal("2")},
    )
    water = helpers.published_dossier(
        db_session,
        organization,
        unit,
        "AGU-M",
        {protein: Decimal("0"), sodium: Decimal("0")},
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    helpers.formulation_item(db_session, version, water, unit, 2, Decimal("60"))
    result = calculate_nutrition(db_session, version)
    by_code = {item[0].code: item for item in result.items}
    assert by_code["protein"][1] == Decimal("10.000000")
    assert by_code["sodium"][1] == Decimal("2.000000")
    assert result.status == "complete"


def test_unknown_value_is_not_zero(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-u")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-U", {protein: Decimal("12")}
    )
    salt = helpers.published_ingredient(db_session, organization, unit, "SAL-U")
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    helpers.formulation_item(db_session, version, salt, unit, 2, Decimal("2"))
    result = calculate_nutrition(db_session, version)
    assert result.status == "incomplete"
    assert result.items[0][1] == Decimal("12.000000")
    assert result.items[0][4] == "missing_data"
    assert any(row.evidence_type == "missing_value" for row in result.evidence)


def test_per_100g_and_technical_portion_with_loss(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-p")
    version.expected_bake_loss_rate = Decimal("0.20")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-P", {protein: Decimal("10")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    result = calculate_nutrition(
        db_session,
        version,
        requested_basis=BASIS_PORTION,
        portion_mass_g=Decimal("50"),
    )
    assert result.expected_final_mass_g == Decimal("80.000000")
    assert result.items[0][2] == Decimal("12.500000")
    assert result.items[0][3] == Decimal("6.250000")
    assert any("retenção" in text for text in result.assumptions)


def test_zero_loss_and_invalid_loss(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-z")
    version.expected_bake_loss_rate = Decimal("0")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-Z", {protein: Decimal("8")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    result = calculate_nutrition(db_session, version, requested_basis=BASIS_PER_100G)
    assert result.expected_final_mass_g == Decimal("100.000000")
    assert result.items[0][2] == Decimal("8.000000")
    with pytest.raises(NutritionError):
        calculate_nutrition(
            db_session,
            version,
            requested_basis=BASIS_PER_100G,
            bake_loss_rate=Decimal("1"),
        )


def test_missing_final_mass_leaves_per_100g_incomplete(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-f")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-F", {protein: Decimal("5")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("80"))
    result = calculate_nutrition(db_session, version, requested_basis=BASIS_PER_100G)
    assert result.status == "incomplete"
    assert result.items[0][2] is None
    assert result.items[0][1] == Decimal("4.000000")


def test_composite_uses_published_dossier_not_children(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-c")
    protein = helpers.nutrient(db_session, unit, "protein")
    mix_ver = helpers.draft_ingredient(
        db_session, organization, unit, "MIX-C", ingredient_type="composite"
    )
    helpers.ingredient_nutrient(db_session, mix_ver, protein, Decimal("20"))
    child = helpers.published_dossier(
        db_session, organization, unit, "FAR-C", {protein: Decimal("99")}
    )
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=mix_ver.id,
            component_ingredient_version_id=child.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=1,
        )
    )
    helpers.publish_ingredient_version(db_session, mix_ver)
    helpers.formulation_item(db_session, version, mix_ver, unit, 1, Decimal("50"))
    result = calculate_nutrition(db_session, version)
    assert result.items[0][1] == Decimal("10.000000")
    assert result.status == "complete"


def test_preparation_without_data_is_incomplete(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-pr")
    protein = helpers.nutrient(db_session, unit, "protein")
    preferment = helpers.ingredient(
        db_session, organization, "LEV-1", ingredient_type="preparation"
    )
    preferment_ver = helpers.version(db_session, preferment, unit, status="published")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-PR", {protein: Decimal("10")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    helpers.formulation_item(db_session, version, preferment_ver, unit, 2, Decimal("20"))
    result = calculate_nutrition(db_session, version)
    assert result.status == "incomplete"
    assert result.items[0][4] == "missing_data"


def test_kilogram_converted_to_grams(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-kg")
    kg = helpers.kilogram(db_session)
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-KG", {protein: Decimal("10")}
    )
    helpers.formulation_item(db_session, version, flour, kg, 1, Decimal("1"))
    result = calculate_nutrition(db_session, version)
    assert result.formula_net_mass_g == Decimal("1000.000000")
    assert result.items[0][1] == Decimal("100.000000")
    assert any(row.evidence_type == "unit_conversion" for row in result.evidence)


def test_incompatible_unit_rejected(db_session: Session) -> None:
    gram = helpers.gram(db_session)
    volume = helpers.milliliter(db_session)
    with pytest.raises(NutritionError, match="incompatível"):
        require_compatible_conversion(gram, volume)


def test_decimal_precision_and_reconstruction(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-d")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session,
        organization,
        unit,
        "FAR-D",
        {protein: Decimal("1") / Decimal("3") * Decimal("100")},
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("30"))
    result = calculate_nutrition(db_session, version)
    persisted = persist_nutrition_calculation(db_session, version, result)
    item = (
        db_session.query(NutritionCalculationItem)
        .filter_by(nutrition_calculation_id=persisted.id)
        .one()
    )
    rows = db_session.query(CalculationEvidence).all()
    rebuilt = reconstruct_whole_formula(rows, protein.id, item.id)
    assert rebuilt == item.whole_formula_amount
    assert persisted.algorithm_name == ALGORITHM_NAME
    assert not isinstance(result.items[0][1], float)


def test_isolation_rejects_foreign_org(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-iso")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-ISO", {protein: Decimal("4")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    other = helpers.org(db_session, "org-nut-iso-b")
    persisted = persist_nutrition_calculation(
        db_session, version, calculate_nutrition(db_session, version)
    )
    with pytest.raises(NutritionAccessError):
        get_nutrition_calculation(db_session, other.id, persisted.id)
    loaded = get_nutrition_calculation(db_session, organization.id, persisted.id)
    assert loaded.id == persisted.id
    foreign_version = FormulationVersion(
        organization_id=other.id,
        formulation_id=version.formulation_id,
        version_number=9,
        status="draft",
    )
    db_session.add(foreign_version)
    with pytest.raises(Exception):
        db_session.flush()


def test_immutability_and_invalidation(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-imm")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-IMM", {protein: Decimal("6")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("100"))
    first = persist_nutrition_calculation(
        db_session, version, calculate_nutrition(db_session, version)
    )
    first_total = (
        db_session.query(NutritionCalculationItem)
        .filter_by(nutrition_calculation_id=first.id)
        .one()
        .whole_formula_amount
    )
    second = persist_nutrition_calculation(
        db_session,
        version,
        calculate_nutrition(db_session, version, bake_loss_rate=Decimal("0.10")),
    )
    assert first.id != second.id
    assert db_session.get(NutritionCalculation, first.id).formula_net_mass_g == Decimal(
        "100.000000"
    )
    assert first_total == Decimal("6.000000")
    first.formula_net_mass_g = Decimal("1")
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_item_and_evidence_not_updatable(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-upd")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-UPD", {protein: Decimal("3")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("50"))
    persisted = persist_nutrition_calculation(
        db_session, version, calculate_nutrition(db_session, version)
    )
    item = (
        db_session.query(NutritionCalculationItem)
        .filter_by(nutrition_calculation_id=persisted.id)
        .one()
    )
    item.whole_formula_amount = Decimal("99")
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_invalidation_preserves_history(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-inv")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-INV", {protein: Decimal("7")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("70"))
    persisted = persist_nutrition_calculation(
        db_session, version, calculate_nutrition(db_session, version)
    )
    invalidate_nutrition_calculation(persisted)
    db_session.flush()
    assert persisted.status == "invalidated"
    assert (
        db_session.query(NutritionCalculationItem)
        .filter_by(nutrition_calculation_id=persisted.id)
        .count()
        == 1
    )
    persisted.warnings = ["nao"]
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_draft_is_simulation_not_approved(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-nut-sim")
    protein = helpers.nutrient(db_session, unit, "protein")
    flour = helpers.published_dossier(
        db_session, organization, unit, "FAR-SIM", {protein: Decimal("9")}
    )
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("90"))
    result = calculate_nutrition(db_session, version)
    assert result.is_simulation is True
    assert result.formulation_version_status == "draft"
    assert any("rascunho" in text for text in result.warnings)
    assert "rótulo aprovado" not in " ".join(result.warnings).lower()
    assert "conforme anvisa" not in " ".join(result.warnings).lower()


def test_no_regulatory_outputs_in_domain() -> None:
    source = getsource(nutrition_engine)
    models_source = Path("app/modules/nutrition_calculation/models.py").read_text(encoding="utf-8")
    blob = source + models_source
    forbidden = (
        "%VD",
        "perc_vd",
        "daily_value",
        "conforme Anvisa",
        "rótulo aprovado",
        "lupa frontal",
        "alegação nutricional",
        "contém glúten",
        "contém lactose",
    )
    for token in forbidden:
        assert token.lower() not in blob.lower()
    assert not hasattr(NutritionCalculation, "daily_value_percent")
    assert not hasattr(NutritionCalculationItem, "daily_value_percent")
    assert "percentual_valor_diario" not in dir(nutrition_engine)
