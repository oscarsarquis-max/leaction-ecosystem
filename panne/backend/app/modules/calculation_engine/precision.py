"""Política de precisão Decimal. Sem float, sem LLM."""

from decimal import ROUND_HALF_UP, Decimal

QUANTITY_QUANTUM = Decimal("0.000001")
FACTOR_QUANTUM = Decimal("0.0000000001")
PERCENT_QUANTUM = Decimal("0.000001")
DEFAULT_ROUNDING = ROUND_HALF_UP
DEFAULT_PRESENTATION_PLACES = 3
ROUNDING_MODE_NAME = "ROUND_HALF_UP"


def quantize_quantity(value: Decimal) -> Decimal:
    return Decimal(value).quantize(QUANTITY_QUANTUM, rounding=DEFAULT_ROUNDING)


def quantize_factor(value: Decimal) -> Decimal:
    return Decimal(value).quantize(FACTOR_QUANTUM, rounding=DEFAULT_ROUNDING)


def quantize_percent(value: Decimal) -> Decimal:
    return Decimal(value).quantize(PERCENT_QUANTUM, rounding=DEFAULT_ROUNDING)


def present(value: Decimal, places: int = DEFAULT_PRESENTATION_PLACES) -> Decimal:
    if places < 0:
        raise ValueError("casas decimais de apresentação inválidas")
    quantum = Decimal("1").scaleb(-places)
    return Decimal(value).quantize(quantum, rounding=DEFAULT_ROUNDING)
