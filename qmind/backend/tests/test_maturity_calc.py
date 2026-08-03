"""Unit tests for maturity Decimal ROUND_HALF_UP aggregation."""

from __future__ import annotations

from decimal import Decimal

from app.modules.maturity import calc


def test_dimension_fully_na_excluded():
    score, n = calc.dimension_score([])
    assert score is None
    assert n == 0


def test_dimension_average_half_up():
    score, n = calc.dimension_score([5, 5, 4])
    assert n == 3
    assert score == Decimal("4.67")  # 14/3 = 4.666... → half-up


def test_global_mean_of_dimensions():
    g = calc.global_score([Decimal("3.00"), Decimal("4.00")])
    assert g == Decimal("3.50")


def test_round_half_up_edge():
    assert calc.round_half_up(Decimal("1.225")) == Decimal("1.23")
    assert calc.round_half_up(Decimal("1.224")) == Decimal("1.22")
