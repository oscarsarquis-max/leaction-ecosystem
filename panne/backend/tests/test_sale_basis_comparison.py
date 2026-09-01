"""Domain tests: sale basis + comparison (no demo SKU dependency)."""

from decimal import Decimal

from app.modules.costing_pricing.comparison import build_comparison, formulas, sale_basis_payload


def test_formulas_markup_vs_margin():
    out = formulas(price=Decimal("8.90"), cost=Decimal("4.52"))
    assert out["markup_factor"] == Decimal("8.90") / Decimal("4.52")
    assert out["margin_amount"] == Decimal("4.38")
    assert out["margin_rate"] is not None
    assert abs(out["margin_rate"] - (Decimal("4.38") / Decimal("8.90"))) < Decimal("0.0000001")


def test_sale_basis_not_informed_blocks_comparison():
    basis = sale_basis_payload(quantity=None, unit_id=None)
    assert basis["informed"] is False
    cmp = build_comparison(
        price_amount="8.90",
        price_currency="BRL",
        sale_basis=basis,
        cost_amount="0.45",
        cost_currency="BRL",
        cost_basis_quantity="1",
        cost_basis_unit_id="11111111-1111-1111-1111-111111111111",
    )
    assert cmp["allowed"] is False
    assert cmp["reason"] == "sale_basis_not_informed"
    assert cmp["markup_factor"] is None


def test_compatible_bases_allow_comparison():
    unit = "22222222-2222-2222-2222-222222222222"
    basis = sale_basis_payload(
        quantity="1",
        unit_id=unit,
        unit_code="un",
        unit_display_name="unidade",
    )
    assert basis["informed"] is True
    cmp = build_comparison(
        price_amount="10.00",
        price_currency="BRL",
        sale_basis=basis,
        cost_amount="4.00",
        cost_currency="BRL",
        cost_basis_quantity="1",
        cost_basis_unit_id=unit,
    )
    assert cmp["allowed"] is True
    assert Decimal(cmp["markup_factor"]) == Decimal("2.5")
    assert Decimal(cmp["margin_rate"]) == Decimal("0.6")


def test_unit_mismatch_blocks():
    basis = sale_basis_payload(
        quantity="1",
        unit_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        unit_code="un",
        unit_display_name="unidade",
    )
    cmp = build_comparison(
        price_amount="10.00",
        price_currency="BRL",
        sale_basis=basis,
        cost_amount="4.00",
        cost_currency="BRL",
        cost_basis_quantity="1",
        cost_basis_unit_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    assert cmp["allowed"] is False
    assert cmp["reason"] == "unit_dimension_mismatch"


def test_cost_basis_absent_blocks_even_with_sale_basis():
    basis = sale_basis_payload(
        quantity="1",
        unit_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        unit_code="un",
        unit_display_name="unidade",
    )
    cmp = build_comparison(
        price_amount="10.00",
        price_currency="BRL",
        sale_basis=basis,
        cost_amount="4.00",
        cost_currency="BRL",
        cost_basis_quantity=None,
        cost_basis_unit_id=None,
    )
    assert cmp["allowed"] is False
    assert cmp["reason"] == "cost_basis_not_informed"


def test_quantity_normalization_same_unit():
    unit = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    basis = sale_basis_payload(
        quantity="2",
        unit_id=unit,
        unit_code="un",
        unit_display_name="unidade",
    )
    cmp = build_comparison(
        price_amount="20.00",
        price_currency="BRL",
        sale_basis=basis,
        cost_amount="4.00",
        cost_currency="BRL",
        cost_basis_quantity="1",
        cost_basis_unit_id=unit,
    )
    assert cmp["allowed"] is True
    # price/2 = 10, cost/1 = 4 → markup 2.5
    assert Decimal(cmp["markup_factor"]) == Decimal("2.5")
