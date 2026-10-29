from decimal import Decimal

import pytest
from app.modules.calculation_engine.nutrition import calculate_nutrition
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def _formula(session: Session, slug: str):
    organization = helpers.org(session, slug)
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, f"PAO-{slug}")
    recipe = helpers.formulation(session, product, f"REC-{slug}")
    version = helpers.formulation_version(session, recipe)
    return organization, unit, version


def test_measured_and_known_zero(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-loq-m")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    draft = helpers.draft_ingredient(db_session, organization, unit, "FAR-LOQ-M")
    helpers.ingredient_nutrient(db_session, draft, protein, Decimal("12"), value_status="measured")
    helpers.ingredient_nutrient(
        db_session, draft, sodium, Decimal("0"), value_status="known_zero"
    )
    helpers.publish_ingredient_version(db_session, draft)
    helpers.formulation_item(db_session, version, draft, unit, 1, Decimal("100"))
    result = calculate_nutrition(db_session, version)
    by_code = {item[0].code: item for item in result.items}
    assert by_code["protein"][1] == Decimal("12.000000")
    assert by_code["sodium"][1] == Decimal("0.000000")
    assert by_code["sodium"][4] == "complete"
    assert result.status == "complete"


def test_below_loq_is_not_zero(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-loq-b")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    draft = helpers.draft_ingredient(db_session, organization, unit, "SAL-LOQ")
    helpers.ingredient_nutrient(
        db_session,
        draft,
        sodium,
        None,
        value_status="below_loq",
        limit_of_quantification=Decimal("0.010000"),
        loq_unit_id=unit.id,
        method_or_source="laboratório interno",
    )
    helpers.publish_ingredient_version(db_session, draft)
    helpers.formulation_item(db_session, version, draft, unit, 1, Decimal("2"))
    result = calculate_nutrition(db_session, version)
    assert result.status == "incomplete"
    assert result.items[0][1] == Decimal("0.000000")
    assert result.items[0][4] == "below_quantification_limit"
    assert any(row.evidence_type == "quantification_limit" for row in result.evidence)
    assert any("não foi convertido em zero" in row.message for row in result.evidence)


def test_unknown_and_not_detected_are_missing(db_session: Session) -> None:
    organization, unit, version = _formula(db_session, "org-loq-u")
    protein = helpers.nutrient(db_session, unit, "protein")
    sodium = helpers.nutrient(db_session, unit, "sodium")
    draft = helpers.draft_ingredient(db_session, organization, unit, "FAR-LOQ-U")
    helpers.ingredient_nutrient(db_session, draft, protein, None, value_status="unknown")
    helpers.ingredient_nutrient(db_session, draft, sodium, None, value_status="not_detected")
    helpers.publish_ingredient_version(db_session, draft)
    helpers.formulation_item(db_session, version, draft, unit, 1, Decimal("50"))
    result = calculate_nutrition(db_session, version)
    assert result.status == "incomplete"
    assert all(item[4] == "missing_data" for item in result.items)
    assert all(item[1] == Decimal("0.000000") for item in result.items)


def test_invalid_loq_combinations_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-loq-inv")
    unit = helpers.gram(db_session)
    cases = [
        ("FAR-INV1", "protein-inv1", Decimal("1"), "below_loq", None, None),
        ("FAR-INV2", "protein-inv2", Decimal("3"), "unknown", None, None),
        ("FAR-INV3", "protein-inv3", None, "measured", None, None),
        ("FAR-INV4", "protein-inv4", Decimal("1"), "known_zero", None, None),
        (
            "FAR-INV5",
            "protein-inv5",
            None,
            "below_loq",
            Decimal("0"),
            unit.id,
        ),
    ]
    for code, nutrient_code, value, status, loq, loq_unit in cases:
        protein = helpers.nutrient(db_session, unit, nutrient_code)
        draft = helpers.draft_ingredient(db_session, organization, unit, code)
        nested = db_session.begin_nested()
        with pytest.raises(IntegrityError):
            helpers.ingredient_nutrient(
                db_session,
                draft,
                protein,
                value,
                value_status=status,
                limit_of_quantification=loq,
                loq_unit_id=loq_unit,
            )
            db_session.flush()
        nested.rollback()
