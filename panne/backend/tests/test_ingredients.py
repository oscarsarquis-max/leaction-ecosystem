from decimal import Decimal

import pytest
from app.modules.ingredient_catalog.models import (
    Ingredient,
    IngredientAllergen,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    UnitConversion,
)
from app.modules.ingredient_catalog.rules import (
    CompositionCycleError,
    PublishedVersionFrozenError,
    assert_acyclic_composition,
    ensure_version_editable,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def test_ingredient_code_unique_per_organization_only(db_session: Session) -> None:
    one = helpers.org(db_session, "org-ing-a")
    two = helpers.org(db_session, "org-ing-b")
    helpers.ingredient(db_session, one, "FAR-001")
    helpers.ingredient(db_session, two, "FAR-001")
    with pytest.raises(IntegrityError):
        helpers.ingredient(db_session, one, "FAR-001")


def test_version_number_unique_and_single_published(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ver")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "ACU-1")
    helpers.version(db_session, item, unit, number=1, status="published")
    with pytest.raises(IntegrityError):
        helpers.version(db_session, item, unit, number=1, status="draft")


def test_only_one_published_version(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-pub")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "FER-1")
    helpers.version(db_session, item, unit, number=1, status="published")
    with pytest.raises(IntegrityError):
        helpers.version(db_session, item, unit, number=2, status="published")


def test_published_version_blocked_by_normal_layer(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-freeze")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "SAL-1")
    published = helpers.version(db_session, item, unit, status="published")
    with pytest.raises(PublishedVersionFrozenError):
        ensure_version_editable(published)
    published.notes = "nao"
    with pytest.raises(Exception, match="published_frozen"):
        db_session.flush()


def test_nutrition_basis_must_be_per_100g_mass(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-basis")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "LEI-1")
    row = IngredientVersion(
        ingredient_id=item.id,
        organization_id=item.organization_id,
        version_number=1,
        status="draft",
        nutrition_basis_type="per_100g",
        nutrition_basis_quantity=Decimal("50"),
        nutrition_basis_unit_id=unit.id,
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_nutrition_unit_rejects_volume(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-vol")
    volume = helpers.milliliter(db_session)
    item = helpers.ingredient(db_session, organization, "AGU-1")
    row = IngredientVersion(
        ingredient_id=item.id,
        organization_id=item.organization_id,
        version_number=1,
        status="draft",
        nutrition_basis_type="per_100g",
        nutrition_basis_quantity=Decimal("100"),
        nutrition_basis_unit_id=volume.id,
    )
    db_session.add(row)
    with pytest.raises(Exception, match="nutrition_basis_unit_must_be_mass"):
        db_session.flush()


def test_nutrient_unique_and_non_negative(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-nut")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "OVO-1")
    ver = helpers.version(db_session, item, unit)
    definition = helpers.nutrient(db_session, unit)
    db_session.add(
        IngredientNutrient(
            organization_id=organization.id,
            ingredient_version_id=ver.id,
            nutrient_id=definition.id,
            value=Decimal("10"),
        )
    )
    db_session.flush()
    db_session.add(
        IngredientNutrient(
            organization_id=organization.id,
            ingredient_version_id=ver.id,
            nutrient_id=definition.id,
            value=Decimal("11"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_nutrient_negative_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-neg")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "NEG-1")
    ver = helpers.version(db_session, item, unit)
    definition = helpers.nutrient(db_session, unit, code="sodium")
    db_session.add(
        IngredientNutrient(
            organization_id=organization.id,
            ingredient_version_id=ver.id,
            nutrient_id=definition.id,
            value=Decimal("-1"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_self_reference_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-self")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "MIX", ingredient_type="composite")
    ver = helpers.version(db_session, item, unit)
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=ver.id,
            component_ingredient_version_id=ver.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cross_organization_component_rejected(db_session: Session) -> None:
    one = helpers.org(db_session, "org-x-a")
    two = helpers.org(db_session, "org-x-b")
    unit = helpers.gram(db_session)
    parent = helpers.ingredient(db_session, one, "PREP", ingredient_type="preparation")
    foreign = helpers.ingredient(db_session, two, "INS")
    parent_v = helpers.version(db_session, parent, unit)
    foreign_v = helpers.version(db_session, foreign, unit)
    db_session.add(
        IngredientComposition(
            organization_id=one.id,
            parent_ingredient_version_id=parent_v.id,
            component_ingredient_version_id=foreign_v.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sequence_unique_and_indirect_cycle(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-cyc")
    unit = helpers.gram(db_session)
    a = helpers.ingredient(db_session, organization, "A", ingredient_type="composite")
    b = helpers.ingredient(db_session, organization, "B", ingredient_type="composite")
    c = helpers.ingredient(db_session, organization, "C", ingredient_type="composite")
    va = helpers.version(db_session, a, unit)
    vb = helpers.version(db_session, b, unit)
    vc = helpers.version(db_session, c, unit)
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=va.id,
            component_ingredient_version_id=vb.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=vb.id,
            component_ingredient_version_id=vc.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    db_session.flush()
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=va.id,
            component_ingredient_version_id=vb.id,
            component_type="constituent",
            quantity=Decimal("2"),
            measurement_unit_id=unit.id,
            sequence=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_indirect_cycle_rejected_by_domain(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-cyc2")
    unit = helpers.gram(db_session)
    a = helpers.ingredient(db_session, organization, "A", ingredient_type="composite")
    b = helpers.ingredient(db_session, organization, "B", ingredient_type="composite")
    c = helpers.ingredient(db_session, organization, "C", ingredient_type="composite")
    va = helpers.version(db_session, a, unit)
    vb = helpers.version(db_session, b, unit)
    vc = helpers.version(db_session, c, unit)
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=va.id,
            component_ingredient_version_id=vb.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    db_session.add(
        IngredientComposition(
            organization_id=organization.id,
            parent_ingredient_version_id=vb.id,
            component_ingredient_version_id=vc.id,
            component_type="constituent",
            quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            sequence=0,
        )
    )
    db_session.flush()
    with pytest.raises(CompositionCycleError):
        assert_acyclic_composition(db_session, vc.id, va.id)


def test_allergen_unique_per_version(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-alg")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "TRI")
    ver = helpers.version(db_session, item, unit)
    gluten = helpers.allergen(db_session)
    db_session.add(
        IngredientAllergen(
            organization_id=organization.id,
            ingredient_version_id=ver.id,
            allergen_id=gluten.id,
            presence="contains",
        )
    )
    db_session.flush()
    db_session.add(
        IngredientAllergen(
            organization_id=organization.id,
            ingredient_version_id=ver.id,
            allergen_id=gluten.id,
            presence="may_contain",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_mass_volume_conversion_rejected(db_session: Session) -> None:
    mass = helpers.gram(db_session)
    volume = helpers.milliliter(db_session)
    db_session.add(
        UnitConversion(
            from_unit_id=mass.id,
            to_unit_id=volume.id,
            factor=Decimal("1"),
            status="active",
        )
    )
    with pytest.raises(Exception, match="incompatible_unit_dimension"):
        db_session.flush()


def test_schema_excludes_legacy_and_future_tables(db_session: Session) -> None:
    from sqlalchemy import inspect

    tables = set(inspect(db_session.get_bind()).get_table_names())
    assert "ingredient" in tables
    assert "organization" in tables
    assert "organization_ingredient" not in tables
    assert "tbl_ingrediente" not in tables
    assert "formula_ingredient" not in tables
    assert Ingredient.__tablename__ == "ingredient"
