"""Conversão de unidade fiscal → unidade interna, com memória de cálculo."""

from __future__ import annotations

from decimal import Decimal

from app.modules.fiscal_inbound.constants import FACTOR_EXPONENT, QUANTITY_EXPONENT
from app.modules.production_planning.errors import ValidationError


def compute_conversion(
    *,
    fiscal_quantity: Decimal,
    fiscal_unit: str | None,
    target_unit: str | None,
    conversion_factor: Decimal | None,
) -> tuple[Decimal, Decimal, dict]:
    factor = conversion_factor if conversion_factor is not None else Decimal("1")
    if factor <= 0:
        raise ValidationError("fator_conversao_invalido")
    if fiscal_unit and target_unit and fiscal_unit != target_unit and factor == 1:
        # Unidades distintas sem fator explícito — bloqueia.
        raise ValidationError("unidade_incompativel")
    converted = (fiscal_quantity * factor).quantize(QUANTITY_EXPONENT)
    memory = {
        "fiscal_quantity": format(fiscal_quantity, "f"),
        "fiscal_unit": fiscal_unit,
        "target_unit": target_unit or fiscal_unit,
        "conversion_factor": format(factor.quantize(FACTOR_EXPONENT), "f"),
        "converted_quantity": format(converted, "f"),
    }
    return converted, factor.quantize(FACTOR_EXPONENT), memory
