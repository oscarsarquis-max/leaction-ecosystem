from decimal import Decimal

from app.modules.calculation_engine.precision import (
    QUANTITY_QUANTUM,
    quantize_factor,
    quantize_quantity,
)
from app.modules.production_planning.constants import (
    REMAINDER_FIRST_BATCHES,
    SPLIT_METHOD,
    TARGET_MODE_UNITS,
)
from app.modules.production_planning.errors import ValidationError


def split_target(
    total: Decimal, count: int, *, integer_units: bool
) -> list[tuple[Decimal, Decimal, Decimal]]:
    if count < 1:
        raise ValidationError("batelada exige quantidade positiva")
    if total <= 0:
        raise ValidationError("alvo da ordem deve ser positivo")
    quantum = Decimal("1") if integer_units else QUANTITY_QUANTUM
    exact = total / Decimal(count)
    base = (exact if integer_units else quantize_quantity(exact)).quantize(quantum)
    parts = [base] * count
    remainder = total - (base * Decimal(count))
    steps = int(remainder / quantum)
    if remainder < 0:
        raise ValidationError("resíduo de divisão inválido")
    for index in range(steps):
        parts[index] = parts[index] + quantum
    if sum(parts, Decimal("0")) != total:
        leftover = total - sum(parts, Decimal("0"))
        parts[0] = parts[0] + leftover
    if sum(parts, Decimal("0")) != total:
        raise ValidationError("soma das bateladas diverge do alvo")
    rows: list[tuple[Decimal, Decimal, Decimal]] = []
    for part in parts:
        factor = quantize_factor(part / total)
        remainder_applied = part - base
        rows.append((part, factor, remainder_applied))
    return rows


def split_memory(count: int, total: Decimal, mode: str) -> dict:
    return {
        "method": SPLIT_METHOD,
        "remainder_rule": REMAINDER_FIRST_BATCHES,
        "batch_count": count,
        "order_target": format(total, "f"),
        "target_mode": mode,
        "integer_units": mode == TARGET_MODE_UNITS,
    }
