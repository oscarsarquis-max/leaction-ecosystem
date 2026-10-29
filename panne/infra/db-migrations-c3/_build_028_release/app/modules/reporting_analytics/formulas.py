"""Agregações analíticas. Percentual nunca é somado. Ausência ≠ zero."""

from decimal import ROUND_HALF_UP, Decimal

from app.modules.costing_pricing.formulas import (
    contribution_from_price,
    gross_margin_from_price,
    markup_percent_from_price,
)
from app.modules.production_planning.errors import ValidationError
from app.modules.reporting_analytics.constants import HUNDRED, PERCENT_QUANTUM, ZERO


def quantize(value: Decimal, places: int = 6) -> Decimal:
    return value.quantize(Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP)


def ratio(numerator, denominator) -> Decimal | None:
    num = Decimal(str(numerator))
    den = Decimal(str(denominator))
    if den <= ZERO:
        return None
    return quantize(num / den, 6)


def ratio_percent(numerator, denominator) -> Decimal | None:
    value = ratio(numerator, denominator)
    if value is None:
        return None
    return value.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP) * HUNDRED


def weighted_average(pairs: list[tuple[Decimal, Decimal]]) -> Decimal | None:
    weight = sum((weight for _value, weight in pairs), ZERO)
    if weight <= ZERO:
        return None
    total = sum((value * weight for value, weight in pairs), ZERO)
    return quantize(total / weight, 6)


def unavailable(reason: str) -> dict:
    return {"status": "unavailable", "reason": reason, "value": None}


def known_zero() -> dict:
    return {"status": "known_zero", "reason": "zero_conhecido", "value": "0"}


def present(value: Decimal | int | str, *, unit: str) -> dict:
    if isinstance(value, Decimal):
        rendered = format(value, "f")
    else:
        rendered = str(value)
    return {"status": "available", "reason": None, "value": rendered, "unit": unit}


def reuse_markup(price, cost_base):
    try:
        return present(markup_percent_from_price(price, cost_base), unit="percent")
    except ValidationError:
        return unavailable("denominador_invalido")


def reuse_gross(price, cost):
    try:
        return present(gross_margin_from_price(price, cost), unit="percent")
    except ValidationError:
        return unavailable("denominador_invalido")


def reuse_contribution(price, variable_product, variable_selling):
    try:
        return present(contribution_from_price(price, variable_product, variable_selling), unit="percent")
    except ValidationError:
        return unavailable("denominador_invalido")


def coverage(valid: int, universe: int) -> dict:
    if universe <= 0:
        return {
            **unavailable("conjunto_vazio"),
            "universe": 0,
            "valid_count": 0,
            "missing_count": 0,
            "percent": None,
        }
    missing = universe - valid
    percent = ratio_percent(valid, universe)
    return {
        "status": "available",
        "universe": universe,
        "valid_count": valid,
        "missing_count": missing,
        "percent": None if percent is None else format(percent / HUNDRED * HUNDRED, "f"),
        "value": None if percent is None else format(percent, "f"),
        "unit": "percent",
        "reason": None,
    }
