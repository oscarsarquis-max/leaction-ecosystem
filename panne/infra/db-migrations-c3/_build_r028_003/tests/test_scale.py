from decimal import Decimal

import pytest
from app.modules.calculation_engine.precision import present, quantize_factor
from app.modules.calculation_engine.scale import (
    ALGORITHM_CODE,
    ALGORITHM_VERSION,
    MODE_FINAL_UNITS,
    MODE_TOTAL_DOUGH_MASS,
    ScaleError,
    calculate_final_units,
    calculate_total_dough_mass,
    persist_scale_calculation,
)
from app.modules.formula_lab.models import ScaleCalculation, ScaleCalculationItem
from sqlalchemy.orm import Session
from tests import helpers


def _items(session: Session, slug: str):
    organization = helpers.org(session, slug)
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, "PAO-SC")
    recipe = helpers.formulation(session, product, "REC-SC")
    version = helpers.formulation_version(session, recipe)
    flour = helpers.published_ingredient(session, organization, unit, f"FAR-{slug}")
    water = helpers.published_ingredient(session, organization, unit, f"AGU-{slug}")
    flour_item = helpers.formulation_item(
        session, version, flour, unit, 1, Decimal("1000"), is_flour_basis=True
    )
    water_item = helpers.formulation_item(
        session, version, water, unit, 2, Decimal("650"), correction_factor=Decimal("1")
    )
    return version, [flour_item, water_item]


def test_scale_by_total_dough_mass(db_session: Session) -> None:
    version, items = _items(db_session, "org-sc-a")
    result = calculate_total_dough_mass(items, Decimal("3300"))
    assert result.calculation_mode == MODE_TOTAL_DOUGH_MASS
    assert result.base_total_net_mass == Decimal("1650.000000")
    assert result.scale_factor == Decimal("2.0000000000")
    assert result.items[0].scaled_net_quantity == Decimal("2000.000000")
    assert result.items[1].scaled_net_quantity == Decimal("1300.000000")
    assert result.items[0].scaled_gross_quantity == Decimal("2000.000000")
    assert result.items[0].bakers_percentage == Decimal("100.000000")
    assert result.items[1].bakers_percentage == Decimal("65.000000")


def test_scale_by_final_units_with_valid_loss(db_session: Session) -> None:
    version, items = _items(db_session, "org-sc-b")
    result = calculate_final_units(items, 10, Decimal("100"), Decimal("0.20"))
    assert result.calculation_mode == MODE_FINAL_UNITS
    assert result.required_pre_bake_mass == Decimal("1250.000000")
    expected_factor = quantize_factor(Decimal("1250") / Decimal("1650"))
    assert result.scale_factor == expected_factor
    assert result.items[0].scaled_gross_quantity == result.items[0].scaled_net_quantity


def test_scale_zero_loss(db_session: Session) -> None:
    _, items = _items(db_session, "org-sc-z")
    result = calculate_final_units(items, 2, Decimal("825"), Decimal("0"))
    assert result.required_pre_bake_mass == Decimal("1650.000000")
    assert result.scale_factor == Decimal("1.0000000000")


def test_scale_loss_one_or_more_rejected(db_session: Session) -> None:
    _, items = _items(db_session, "org-sc-bad")
    with pytest.raises(ScaleError):
        calculate_final_units(items, 2, Decimal("100"), Decimal("1"))
    with pytest.raises(ScaleError):
        calculate_final_units(items, 2, Decimal("100"), Decimal("1.2"))


def test_scale_rejects_float_and_non_positive(db_session: Session) -> None:
    _, items = _items(db_session, "org-sc-flt")
    with pytest.raises(ScaleError, match="float"):
        calculate_total_dough_mass(items, 1.5)  # type: ignore[arg-type]
    with pytest.raises(ScaleError):
        calculate_total_dough_mass(items, Decimal("0"))
    with pytest.raises(ScaleError):
        calculate_final_units(items, 0, Decimal("100"), Decimal("0.1"))


def test_scale_reproducible_and_memory(db_session: Session) -> None:
    version, items = _items(db_session, "org-sc-mem")
    first = calculate_total_dough_mass(items, Decimal("2475"))
    second = calculate_total_dough_mass(items, Decimal("2475"))
    assert first.scale_factor == second.scale_factor
    assert [item.scaled_net_quantity for item in first.items] == [
        item.scaled_net_quantity for item in second.items
    ]
    persisted = persist_scale_calculation(db_session, version, first)
    assert persisted.algorithm_code == ALGORITHM_CODE
    assert persisted.algorithm_version == ALGORITHM_VERSION
    stored = db_session.get(ScaleCalculation, persisted.id)
    assert stored is not None
    assert stored.scale_factor == first.scale_factor
    lines = (
        db_session.query(ScaleCalculationItem)
        .filter_by(scale_calculation_id=persisted.id)
        .order_by(ScaleCalculationItem.sequence)
        .all()
    )
    assert len(lines) == 2
    assert lines[0].base_net_quantity == Decimal("1000")
    assert lines[0].ingredient_version_id == items[0].ingredient_version_id
    reconstructed = lines[0].base_net_quantity * stored.scale_factor
    assert reconstructed.quantize(Decimal("0.000001")) == lines[0].scaled_net_quantity
    stored.notes = "nope"  # type: ignore[attr-defined]
    stored.scale_factor = Decimal("9")
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_half_up_rounding_and_no_float() -> None:
    assert present(Decimal("1.235"), 2) == Decimal("1.24")
    assert present(Decimal("1.225"), 2) == Decimal("1.23")
    added = Decimal("0.1") + Decimal("0.2")
    assert added == Decimal("0.3")
    assert not isinstance(added, float)
