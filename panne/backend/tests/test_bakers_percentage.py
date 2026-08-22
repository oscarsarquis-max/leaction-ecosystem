from decimal import Decimal

import pytest
from app.modules.calculation_engine.precision import quantize_percent
from app.modules.formula_lab.rules import bakers_percentage, bakers_percentages, total_flour_mass
from sqlalchemy.orm import Session
from tests import helpers


def test_single_flour_basis(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-bp-1")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-BP1")
    recipe = helpers.formulation(db_session, product, "REC-BP1")
    version = helpers.formulation_version(db_session, recipe)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-BP1")
    water = helpers.published_ingredient(db_session, organization, unit, "AGU-BP1")
    flour_item = helpers.formulation_item(
        db_session, version, flour, unit, 1, Decimal("1000"), is_flour_basis=True
    )
    water_item = helpers.formulation_item(db_session, version, water, unit, 2, Decimal("650"))
    percents = bakers_percentages([flour_item, water_item])
    assert percents is not None
    assert percents[flour_item.id] == Decimal("100")
    assert percents[water_item.id] == Decimal("65")
    assert total_flour_mass([flour_item, water_item]) == Decimal("1000")


def test_multiple_flours_sum_base(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-bp-2")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-BP2")
    recipe = helpers.formulation(db_session, product, "REC-BP2")
    version = helpers.formulation_version(db_session, recipe)
    wheat = helpers.published_ingredient(db_session, organization, unit, "FAR-T")
    rye = helpers.published_ingredient(db_session, organization, unit, "FAR-C")
    water = helpers.published_ingredient(db_session, organization, unit, "AGU-2")
    wheat_item = helpers.formulation_item(
        db_session, version, wheat, unit, 1, Decimal("700"), is_flour_basis=True
    )
    rye_item = helpers.formulation_item(
        db_session, version, rye, unit, 2, Decimal("300"), is_flour_basis=True
    )
    water_item = helpers.formulation_item(db_session, version, water, unit, 3, Decimal("720"))
    percents = bakers_percentages([wheat_item, rye_item, water_item])
    assert percents is not None
    assert total_flour_mass([wheat_item, rye_item, water_item]) == Decimal("1000")
    assert percents[wheat_item.id] == Decimal("70")
    assert percents[rye_item.id] == Decimal("30")
    assert percents[water_item.id] == Decimal("72")


def test_no_flour_basis_has_no_percentage(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-bp-0")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-BP0")
    recipe = helpers.formulation(db_session, product, "REC-BP0")
    version = helpers.formulation_version(db_session, recipe)
    sugar = helpers.published_ingredient(db_session, organization, unit, "ACU-0")
    item = helpers.formulation_item(db_session, version, sugar, unit, 1, Decimal("50"))
    assert total_flour_mass([item]) is None
    assert bakers_percentages([item]) is None


def test_zero_quantity_invalid_for_percentage() -> None:
    with pytest.raises(ValueError):
        bakers_percentage(Decimal("10"), Decimal("0"))


def test_percentage_uses_decimal_not_float() -> None:
    value = bakers_percentage(Decimal("1"), Decimal("3"))
    assert value == Decimal("100") / Decimal("3")
    assert not isinstance(value, float)
    presented = quantize_percent(value)
    assert presented == Decimal("33.333333")
