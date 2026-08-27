"""Elegibilidade operacional de lote (R026-009).

`available_quantity` do saldo permanece `physical - reserved` (não reservado).
Disponível para produção e impedido são projeções derivadas de status + validade.
`as_of` vem de `inventory_operational_date` — nunca do cliente HTTP comum.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.inventory_procurement.constants import BLOCKED_LOT_STATUSES, ZERO
from app.modules.inventory_procurement.models import InventoryLot
from app.modules.inventory_procurement.operational_date import inventory_operational_date

# Motivos estáveis para API / auditoria
REASON_STATUS = "lot_status"
REASON_EXPIRED = "expired_calendar"


def is_lot_production_eligible(lot: InventoryLot | None, *, as_of: date | None = None) -> tuple[bool, str | None]:
    """Alinha com FEFO e `_assert_lot_usable`: status available e expires_on >= as_of (ou null)."""
    if lot is None:
        return False, "lot_missing"
    today = as_of if as_of is not None else inventory_operational_date()
    if lot.status in BLOCKED_LOT_STATUSES:
        return False, REASON_STATUS
    if lot.expires_on is not None and lot.expires_on < today:
        return False, REASON_EXPIRED
    return True, None


def project_balance_quantities(
    physical: Decimal,
    reserved: Decimal,
    *,
    eligible: bool,
) -> dict[str, Decimal]:
    """Projeções. Impedido ⊆ não reservado quando o lote é inelegível."""
    unreserved = physical - reserved
    if eligible:
        return {
            "unreserved_quantity": unreserved,
            "eligible_quantity": unreserved,
            "impeded_quantity": ZERO,
        }
    impeded = unreserved if unreserved > ZERO else ZERO
    return {
        "unreserved_quantity": unreserved,
        "eligible_quantity": ZERO,
        "impeded_quantity": impeded,
    }
