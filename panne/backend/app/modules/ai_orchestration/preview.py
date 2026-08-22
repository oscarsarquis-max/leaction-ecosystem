"""Prévia técnica determinística. A IA não calcula oficialmente."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.modules.formula_lab.rules import FlourBasisEmptyError, bakers_percentages


@dataclass(frozen=True)
class TechnicalPreview:
    warnings: tuple[str, ...]
    bakers_percentages: dict[str, Decimal] | None
    formula_net_mass_g: Decimal | None


def preview_proposal_items(items: list) -> TechnicalPreview:
    warnings: list[str] = []
    resolved = [
        item
        for item in items
        if item.resolution_status == "resolved" and item.net_quantity_g is not None
    ]
    if len(resolved) != len(items):
        warnings.append("Prévia incompleta: há itens sem resolução ou sem quantidade.")
    inconsistent = False
    for item in items:
        if item.correction_factor is not None and item.net_quantity_g is None:
            inconsistent = True
        if item.is_flour_basis and item.net_quantity_g is None:
            inconsistent = True
    if inconsistent:
        warnings.append("Valores sugeridos inconsistentes; nenhuma correção automática foi feita.")
    if not resolved:
        return TechnicalPreview(tuple(warnings), None, None)
    fake_items = []
    net_total = Decimal("0")
    for item in resolved:
        net_total += item.net_quantity_g
        fake_items.append(
            SimpleNamespace(
                id=uuid4(),
                net_quantity=item.net_quantity_g,
                is_flour_basis=item.is_flour_basis,
            )
        )
    percentages = None
    try:
        raw = bakers_percentages(fake_items)
        if raw:
            percentages = {str(key): value for key, value in raw.items()}
    except FlourBasisEmptyError:
        warnings.append("Base de farinha marcada sem massa positiva; prévia de padeiro omitida.")
    return TechnicalPreview(tuple(warnings), percentages, net_total)
