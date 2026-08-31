"""Correspondência item fiscal ↔ cadastro Panne (ingrediente ou produto comprado)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.constants import (
    DECISION_CONFIRMED,
    DECISION_SUGGESTED,
    DESCRIPTION_MIN_SCORE,
    MATCH_MATCHED,
    MATCH_SUGGESTED,
    MATCH_UNMATCHED,
    STRATEGY_GTIN_LINK,
    STRATEGY_MANUAL,
    STRATEGY_SUPPLIER_LINK,
    STRATEGY_SUPPLIER_SKU,
    TARGET_INGREDIENT,
    TARGET_PRODUCT,
    TARGET_TYPES,
)
from app.modules.fiscal_inbound.conversion import compute_conversion
from app.modules.fiscal_inbound.models import FiscalInboundItem, FiscalItemMatch, SupplierItemLink
from app.modules.production_planning.errors import ValidationError


def _now():
    return datetime.now(UTC)


def suggest_matches(
    session: Session,
    *,
    organization_id: UUID,
    supplier_id: UUID | None,
    item: FiscalInboundItem,
) -> list[dict]:
    suggestions: list[dict] = []
    if supplier_id and item.supplier_code:
        link = session.scalar(
            select(SupplierItemLink).where(
                SupplierItemLink.organization_id == organization_id,
                SupplierItemLink.supplier_id == supplier_id,
                SupplierItemLink.supplier_code == item.supplier_code,
            )
        )
        if link:
            suggestions.append(
                {
                    "target_type": link.target_type,
                    "target_id": link.target_id,
                    "unit_code": link.unit_code,
                    "conversion_factor": link.conversion_factor,
                    "score": Decimal("1.0000"),
                    "strategy": STRATEGY_SUPPLIER_LINK,
                    "reason": "Vínculo já confirmado com este fornecedor e código.",
                }
            )
    if supplier_id and item.gtin:
        link = session.scalar(
            select(SupplierItemLink).where(
                SupplierItemLink.organization_id == organization_id,
                SupplierItemLink.supplier_id == supplier_id,
                SupplierItemLink.gtin == item.gtin,
            )
        )
        if link:
            suggestions.append(
                {
                    "target_type": link.target_type,
                    "target_id": link.target_id,
                    "unit_code": link.unit_code,
                    "conversion_factor": link.conversion_factor,
                    "score": Decimal("0.9800"),
                    "strategy": STRATEGY_GTIN_LINK,
                    "reason": "GTIN já vinculado a este fornecedor.",
                }
            )
    return suggestions


def apply_suggestion(session: Session, item: FiscalInboundItem, suggestion: dict, actor_user_id: UUID):
    match = FiscalItemMatch(
        organization_id=item.organization_id,
        fiscal_inbound_item_id=item.id,
        target_type=suggestion["target_type"],
        target_id=suggestion["target_id"],
        unit_code=suggestion.get("unit_code") or item.unit_code,
        conversion_factor=suggestion.get("conversion_factor") or Decimal("1"),
        score=suggestion.get("score"),
        strategy=suggestion["strategy"],
        decision=DECISION_SUGGESTED,
    )
    session.add(match)
    item.match_status = MATCH_SUGGESTED
    item.target_type = suggestion["target_type"]
    item.target_id = suggestion["target_id"]
    return match


def confirm_match(
    session: Session,
    *,
    item: FiscalInboundItem,
    target_type: str,
    target_id: UUID,
    inventory_item_id: UUID | None,
    unit_code: str | None,
    conversion_factor: Decimal | None,
    actor_user_id: UUID,
    supplier_id: UUID | None,
    persist_link: bool = True,
) -> FiscalItemMatch:
    if target_type not in TARGET_TYPES:
        raise ValidationError("contrato_invalido")
    converted, factor, memory = compute_conversion(
        fiscal_quantity=item.quantity,
        fiscal_unit=item.unit_code,
        target_unit=unit_code or item.unit_code,
        conversion_factor=conversion_factor,
    )
    match = FiscalItemMatch(
        organization_id=item.organization_id,
        fiscal_inbound_item_id=item.id,
        target_type=target_type,
        target_id=target_id,
        inventory_item_id=inventory_item_id,
        unit_code=unit_code or item.unit_code,
        conversion_factor=factor,
        score=Decimal("1.0000"),
        strategy=STRATEGY_MANUAL if not item.supplier_code else STRATEGY_SUPPLIER_SKU,
        decision=DECISION_CONFIRMED,
        decided_by=actor_user_id,
        decided_at=_now(),
    )
    session.add(match)
    item.match_status = MATCH_MATCHED
    item.target_type = target_type
    item.target_id = target_id
    item.inventory_item_id = inventory_item_id
    item.conversion_factor = factor
    item.converted_quantity = converted
    item.converted_unit_code = unit_code or item.unit_code
    item.conversion_memory = memory
    item.row_version = int(item.row_version or 1) + 1

    if persist_link and supplier_id and (item.supplier_code or item.gtin):
        existing = None
        if item.supplier_code:
            existing = session.scalar(
                select(SupplierItemLink).where(
                    SupplierItemLink.organization_id == item.organization_id,
                    SupplierItemLink.supplier_id == supplier_id,
                    SupplierItemLink.supplier_code == item.supplier_code,
                )
            )
        if existing is None and item.gtin:
            existing = session.scalar(
                select(SupplierItemLink).where(
                    SupplierItemLink.organization_id == item.organization_id,
                    SupplierItemLink.supplier_id == supplier_id,
                    SupplierItemLink.gtin == item.gtin,
                )
            )
        if existing is None:
            session.add(
                SupplierItemLink(
                    organization_id=item.organization_id,
                    supplier_id=supplier_id,
                    supplier_code=item.supplier_code,
                    gtin=item.gtin,
                    target_type=target_type,
                    target_id=target_id,
                    unit_code=unit_code or item.unit_code,
                    conversion_factor=factor,
                    confirmed_by=actor_user_id,
                    confirmed_at=_now(),
                )
            )
        else:
            existing.target_type = target_type
            existing.target_id = target_id
            existing.unit_code = unit_code or item.unit_code
            existing.conversion_factor = factor
            existing.confirmed_by = actor_user_id
            existing.confirmed_at = _now()
            existing.row_version = int(existing.row_version or 1) + 1
    return match


def all_items_matched(items: list[FiscalInboundItem]) -> bool:
    if not items:
        return False
    return all(item.match_status == MATCH_MATCHED for item in items)


def unmatched_count(items: list[FiscalInboundItem]) -> int:
    return sum(1 for item in items if item.match_status in {MATCH_UNMATCHED, MATCH_SUGGESTED})
