"""Fórmulas determinísticas. Markup, margem bruta e contribuição são distintas."""

from decimal import Decimal, ROUND_HALF_UP

from app.modules.costing_pricing.constants import HUNDRED, ONE, PERCENT_QUANTUM, ZERO
from app.modules.production_planning.errors import ValidationError


def _dec(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _positive_base(cost_base) -> Decimal:
    base = _dec(cost_base)
    if base <= ZERO:
        raise ValidationError("denominador_invalido")
    return base


def quantize_money(value: Decimal, places: int = 6) -> Decimal:
    quantum = Decimal("1").scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)


def price_from_markup_factor(cost_base, factor) -> Decimal:
    return quantize_money(_positive_base(cost_base) * _dec(factor))


def markup_percent_from_price(price, cost_base) -> Decimal:
    base = _positive_base(cost_base)
    return quantize_percent((_dec(price) / base - ONE) * HUNDRED)


def price_from_markup_percent(cost_base, percent) -> Decimal:
    factor = ONE + (_dec(percent) / HUNDRED)
    if factor <= ZERO:
        raise ValidationError("denominador_invalido")
    return price_from_markup_factor(cost_base, factor)


def price_from_gross_margin(cost_base, target_rate) -> Decimal:
    rate = _dec(target_rate)
    if rate < ZERO or rate >= ONE:
        raise ValidationError("denominador_invalido")
    return quantize_money(_positive_base(cost_base) / (ONE - rate))


def gross_margin_from_price(price, cost_for_gross) -> Decimal:
    sale = _dec(price)
    if sale <= ZERO:
        raise ValidationError("denominador_invalido")
    return quantize_percent((sale - _dec(cost_for_gross)) / sale)


def price_from_contribution(
    recoverable_base,
    variable_expense_rate,
    contribution_target,
) -> Decimal:
    rate = _dec(variable_expense_rate)
    target = _dec(contribution_target)
    denominator = ONE - rate - target
    if denominator <= ZERO:
        raise ValidationError("denominador_invalido")
    if target < ZERO or target >= ONE or rate < ZERO:
        raise ValidationError("denominador_invalido")
    return quantize_money(_positive_base(recoverable_base) / denominator)


def contribution_from_price(price, variable_product, variable_selling) -> Decimal:
    sale = _dec(price)
    if sale <= ZERO:
        raise ValidationError("denominador_invalido")
    return quantize_percent((sale - _dec(variable_product) - _dec(variable_selling)) / sale)


def reverse_metrics(
    price,
    cost_base,
    *,
    cost_for_gross=None,
    variable_product=None,
    variable_selling=None,
    fixed_allocated=None,
) -> dict:
    sale = _dec(price)
    base = _positive_base(cost_base)
    gross_cost = base if cost_for_gross is None else _dec(cost_for_gross)
    var_prod = ZERO if variable_product is None else _dec(variable_product)
    var_sell = ZERO if variable_selling is None else _dec(variable_selling)
    fixed = ZERO if fixed_allocated is None else _dec(fixed_allocated)
    unit_breakeven = None
    if sale - var_prod - var_sell > ZERO and fixed > ZERO:
        unit_breakeven = quantize_money(fixed / (sale - var_prod - var_sell))
    return {
        "markup_percent": markup_percent_from_price(sale, base),
        "gross_margin": gross_margin_from_price(sale, gross_cost),
        "contribution_margin": contribution_from_price(sale, var_prod, var_sell),
        "unit_breakeven": None if unit_breakeven is None else format(unit_breakeven, "f"),
    }
