"""Rateio de frete/desconto → custo unitário interno (sem contabilidade fiscal completa)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.fiscal_inbound.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    BASIS_GROSS_AMOUNT,
    MONEY_EXPONENT,
    ZERO,
)
from app.modules.production_planning.errors import ValidationError


def allocate_costs(
    *,
    lines: list[dict],
    freight: Decimal | None,
    discount: Decimal | None,
    basis: str = BASIS_GROSS_AMOUNT,
) -> list[dict]:
    """lines: [{item_id, gross_amount, quantity, unit_cost_hint?}]"""
    if not lines:
        return []
    freight = freight or ZERO
    discount = discount or ZERO
    if basis == BASIS_GROSS_AMOUNT:
        weights = [Decimal(str(line.get("gross_amount") or 0)) for line in lines]
    else:
        weights = [Decimal(str(line.get("quantity") or 0)) for line in lines]
    total_weight = sum(weights, ZERO)
    if total_weight <= ZERO:
        raise ValidationError("rateio_sem_base")
    allocated: list[dict] = []
    for line, weight in zip(lines, weights, strict=True):
        share = weight / total_weight
        freight_share = (freight * share).quantize(MONEY_EXPONENT)
        discount_share = (discount * share).quantize(MONEY_EXPONENT)
        gross = Decimal(str(line.get("gross_amount") or 0))
        qty = Decimal(str(line.get("quantity") or 0))
        if qty <= ZERO:
            raise ValidationError("contrato_invalido")
        net = (gross + freight_share - discount_share).quantize(MONEY_EXPONENT)
        unit_cost = (net / qty).quantize(MONEY_EXPONENT)
        allocated.append(
            {
                "item_id": line["item_id"],
                "basis": basis,
                "freight_share": freight_share,
                "discount_share": discount_share,
                "other_share": ZERO,
                "net_amount": net,
                "unit_cost": unit_cost,
                "memory": {
                    "gross_amount": format(gross, "f"),
                    "quantity": format(qty, "f"),
                    "share": format(share, "f"),
                    "freight_total": format(freight, "f"),
                    "discount_total": format(discount, "f"),
                },
                "algorithm_name": ALGORITHM_NAME,
                "algorithm_version": ALGORITHM_VERSION,
            }
        )
    return allocated
