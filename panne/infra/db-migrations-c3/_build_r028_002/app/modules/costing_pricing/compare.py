"""Comparações versionadas. Sem ranking de pessoas."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.constants import ZERO
from app.modules.costing_pricing.formulas import quantize_money, quantize_percent
from app.modules.costing_pricing.models import CostingCalculation, CostingComponent, PracticedPrice


def _amount(value) -> Decimal:
    return ZERO if value is None else value


def composition(session: Session, calculation: CostingCalculation) -> list[dict]:
    rows = list(
        session.scalars(
            select(CostingComponent).where(
                CostingComponent.costing_calculation_id == calculation.id
            )
        )
    )
    total = calculation.total_amount
    items = []
    for row in rows:
        share = None
        if total and total > ZERO and row.amount is not None:
            share = quantize_percent(row.amount / total * Decimal("100"))
        items.append(
            {
                "category": row.category,
                "amount": None if row.amount is None else format(row.amount, "f"),
                "quality": row.quality,
                "share_percent": None if share is None else format(share, "f"),
            }
        )
    return items


def compare_calculations(left: CostingCalculation, right: CostingCalculation) -> dict:
    total_delta = None
    if left.total_amount is not None and right.total_amount is not None:
        total_delta = quantize_money(right.total_amount - left.total_amount)
    sellable_delta = None
    if left.sellable_unit_amount is not None and right.sellable_unit_amount is not None:
        sellable_delta = quantize_money(right.sellable_unit_amount - left.sellable_unit_amount)
    produced_delta = None
    if left.produced_quantity is not None and right.produced_quantity is not None:
        produced_delta = quantize_money(right.produced_quantity - left.produced_quantity)
    base = left.total_amount or right.total_amount
    return {
        "left_id": str(left.id),
        "right_id": str(right.id),
        "left_kind": left.kind,
        "right_kind": right.kind,
        "left_completeness": left.completeness,
        "right_completeness": right.completeness,
        "total_delta": None if total_delta is None else format(total_delta, "f"),
        "sellable_delta": None if sellable_delta is None else format(sellable_delta, "f"),
        "yield_quantity_delta": None if produced_delta is None else format(produced_delta, "f"),
        "sensitivity": None
        if base is None
        else {
            "cost_plus_10": format(quantize_money(base * Decimal("1.10")), "f"),
            "cost_minus_10": format(quantize_money(base * Decimal("0.90")), "f"),
            "note": "Projeção determinística. Não cria cadastro paralelo nem ranking.",
        },
    }


def suggested_versus_practiced(suggested, practiced: PracticedPrice) -> dict:
    if suggested is None:
        return {"delta": None}
    return {
        "suggested": format(suggested, "f"),
        "practiced": format(practiced.amount, "f"),
        "delta": format(quantize_money(practiced.amount - suggested), "f"),
        "channel": practiced.channel,
    }
