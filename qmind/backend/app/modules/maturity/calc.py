"""Maturity aggregation — Decimal + ROUND_HALF_UP (003_Maturity_Model.md §6).

Formula changes (weights, rounding, subset rules) require a **new**
`maturity_models.model_version` — never mutate an active catalog in place.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable


TWOPLACES = Decimal("0.01")


def round_half_up(value: Decimal, places: int = 2) -> Decimal:
    quant = Decimal(10) ** -places
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def dimension_score(levels: Iterable[int]) -> tuple[Decimal | None, int]:
    """Average of applicable criterion levels. None if dimension fully N/A (n=0)."""
    vals = list(levels)
    n = len(vals)
    if n == 0:
        return None, 0
    total = sum(Decimal(v) for v in vals)
    return round_half_up(total / Decimal(n)), n


def global_score(dimension_scores: Iterable[Decimal]) -> Decimal | None:
    """Mean of dimension scores that have ≥1 applicable criterion."""
    vals = list(dimension_scores)
    if not vals:
        return None
    total = sum(vals)
    return round_half_up(total / Decimal(len(vals)))
