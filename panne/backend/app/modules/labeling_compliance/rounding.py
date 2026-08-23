"""Arredondamento regulatório. IN 75/2020, acesso 2026-08-23. Sem float."""

from decimal import ROUND_HALF_UP, Decimal

from app.modules.labeling_compliance.constants import DAILY_VALUES


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _nearest(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_HALF_UP) * step


def round_energy_kcal(value: Decimal) -> Decimal:
    amount = _to_decimal(value)
    if amount < Decimal("5"):
        return Decimal("0")
    if amount <= Decimal("50"):
        return _nearest(amount, Decimal("5"))
    return _nearest(amount, Decimal("10"))


def round_macro_g(value: Decimal) -> Decimal:
    amount = _to_decimal(value)
    if amount < Decimal("0.5"):
        return Decimal("0")
    if amount <= Decimal("10"):
        return amount.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return _nearest(amount, Decimal("1"))


def round_fat_g(value: Decimal) -> Decimal:
    amount = _to_decimal(value)
    if amount < Decimal("0.5"):
        return Decimal("0")
    if amount <= Decimal("5"):
        return amount.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return _nearest(amount, Decimal("0.5"))


def round_sodium_mg(value: Decimal) -> Decimal:
    amount = _to_decimal(value)
    if amount < Decimal("5"):
        return Decimal("0")
    if amount <= Decimal("140"):
        return _nearest(amount, Decimal("5"))
    return _nearest(amount, Decimal("10"))


def round_declared(code: str, value: Decimal) -> Decimal:
    if code == "energy_kcal":
        return round_energy_kcal(value)
    if code == "sodium":
        return round_sodium_mg(value)
    if code in {"total_fat", "saturated_fat", "trans_fat"}:
        return round_fat_g(value)
    return round_macro_g(value)


def daily_value_percent(code: str, declared: Decimal) -> Decimal | None:
    reference = DAILY_VALUES.get(code)
    if reference is None or reference <= 0:
        return None
    return (declared / reference * Decimal("100")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
