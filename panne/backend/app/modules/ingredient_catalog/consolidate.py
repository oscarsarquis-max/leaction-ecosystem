"""Vínculo manual de lotes e linhas fiscais a um ingrediente.

Não funde cadastros, não altera saldo, custo, movimento nem documento fiscal.
A repetição com o mesmo conjunto é idempotente.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.models import FiscalInboundDocument, FiscalInboundItem, FiscalItemMatch
from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_MATCH,
    PERMISSION_INGREDIENT_UPDATE_DRAFT,
    PERMISSION_INVENTORY_ITEM_MANAGE,
    PERMISSION_INVENTORY_READ,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import Ingredient, IngredientCommand, IngredientLinkReassignment
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryItem,
    InventoryLot,
    InventoryMovement,
    InventoryReservation,
    InventoryReservationAllocation,
    ProcurementReceiptItem,
)
from app.modules.inventory_procurement.services import _digest, _get, _org, _qty, _replay
from app.modules.production_planning.errors import ConcurrencyError, ValidationError

INBOUND_ONLY_MOVEMENTS = frozenset({"receipt", "opening"})


def _replay_ingredient(session: Session, org: UUID, key, command: str, payload: dict):
    if key is None:
        return None
    row = session.scalar(
        select(IngredientCommand).where(
            IngredientCommand.organization_id == org,
            IngredientCommand.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != _digest(payload):
        raise ValidationError("idempotencia_conflito")
    return row


def _now():
    return datetime.now(UTC)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _lot_snapshot(lot: InventoryLot) -> dict:
    return {
        "lot_id": str(lot.id),
        "inventory_item_id": str(lot.inventory_item_id),
        "received_quantity": _text(lot.received_quantity),
        "unit_code": lot.unit_code,
        "internal_lot_code": lot.internal_lot_code,
        "status": lot.status,
        "package_content_quantity": _text(lot.package_content_quantity) if lot.package_content_quantity is not None else None,
        "package_content_unit": lot.package_content_unit,
        "cost_status": lot.cost_status,
        "declared_unit_cost": _text(lot.declared_unit_cost) if lot.declared_unit_cost is not None else None,
    }


def list_linkable_entries(session: Session, principal: Principal, *, destination_id: UUID | None = None) -> list[dict]:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    org = _org(principal)
    lots = list(session.scalars(select(InventoryLot).where(InventoryLot.organization_id == org)))
    items = {
        row.id: row
        for row in session.scalars(select(InventoryItem).where(InventoryItem.organization_id == org))
    }
    ingredients = {
        row.id: row
        for row in session.scalars(select(Ingredient).where(Ingredient.organization_id == org))
    }
    fiscal_by_lot: dict[UUID, FiscalInboundItem] = {}
    receipt_items = list(
        session.scalars(
            select(ProcurementReceiptItem).where(ProcurementReceiptItem.organization_id == org)
        )
    )
    fiscal_ids = [row.fiscal_inbound_item_id for row in receipt_items if row.fiscal_inbound_item_id]
    fiscals = {}
    documents = {}
    if fiscal_ids:
        fiscals = {
            row.id: row
            for row in session.scalars(
                select(FiscalInboundItem).where(FiscalInboundItem.id.in_(fiscal_ids))
            )
        }
        document_ids = [row.fiscal_inbound_document_id for row in fiscals.values()]
        if document_ids:
            documents = {
                row.id: row
                for row in session.scalars(
                    select(FiscalInboundDocument).where(FiscalInboundDocument.id.in_(document_ids))
                )
            }
    for receipt in receipt_items:
        if receipt.inventory_lot_id and receipt.fiscal_inbound_item_id:
            fiscal_by_lot[receipt.inventory_lot_id] = fiscals.get(receipt.fiscal_inbound_item_id)

    rows = []
    for lot in lots:
        stock = items.get(lot.inventory_item_id)
        ingredient = ingredients.get(stock.ingredient_id) if stock else None
        fiscal = fiscal_by_lot.get(lot.id)
        if destination_id and ingredient and ingredient.id == destination_id:
            linked = True
        else:
            linked = False
        rows.append(
            {
                "inventory_lot_id": str(lot.id),
                "internal_lot_code": lot.internal_lot_code,
                "quantity": _text(lot.received_quantity),
                "unit_code": lot.unit_code,
                "establishment_id": str(lot.establishment_id),
                "current_ingredient_id": None if ingredient is None else str(ingredient.id),
                "current_ingredient_name": None if ingredient is None else ingredient.display_name,
                "current_ingredient_code": None if ingredient is None else ingredient.code,
                "already_linked": linked,
                "fiscal_inbound_item_id": None if fiscal is None else str(fiscal.id),
                "description": None if fiscal is None else fiscal.description,
                "document_id": None if fiscal is None else str(fiscal.fiscal_inbound_document_id),
                "document_number": None
                if fiscal is None
                else (documents.get(fiscal.fiscal_inbound_document_id).number if documents.get(fiscal.fiscal_inbound_document_id) else None),
                "gtin": None if fiscal is None else fiscal.gtin,
                "supplier_code": None if fiscal is None else fiscal.supplier_code,
                "unit_cost": None if fiscal is None else _text(fiscal.unit_cost),
                "package_content_quantity": _text(lot.package_content_quantity)
                if lot.package_content_quantity is not None
                else None,
                "package_content_unit": lot.package_content_unit,
                "cost_status": lot.cost_status,
            }
        )
    used_lots = {str(lot_id) for lot_id in _used_lot_ids(session, org)}
    for row in rows:
        row["has_downstream_use"] = row["inventory_lot_id"] in used_lots
    return rows


def _used_lot_ids(session: Session, org: UUID) -> set[UUID]:
    used: set[UUID] = set()
    for balance in session.scalars(
        select(InventoryBalance).where(InventoryBalance.organization_id == org)
    ):
        if balance.inventory_lot_id and Decimal(balance.reserved_quantity) > 0:
            used.add(balance.inventory_lot_id)
    for movement in session.scalars(
        select(InventoryMovement).where(InventoryMovement.organization_id == org)
    ):
        if movement.inventory_lot_id and movement.movement_type not in INBOUND_ONLY_MOVEMENTS:
            used.add(movement.inventory_lot_id)
    return used


def lot_downstream_use(session: Session, org: UUID, lot: InventoryLot) -> dict | None:
    for balance in session.scalars(
        select(InventoryBalance).where(
            InventoryBalance.organization_id == org,
            InventoryBalance.inventory_lot_id == lot.id,
        )
    ):
        reserved = Decimal(balance.reserved_quantity)
        if reserved > 0:
            return {"kind": "reservation", "reserved_quantity": format(reserved, "f")}
    for movement in session.scalars(
        select(InventoryMovement)
        .where(
            InventoryMovement.organization_id == org,
            InventoryMovement.inventory_lot_id == lot.id,
        )
        .order_by(InventoryMovement.created_at.asc())
    ):
        if movement.movement_type not in INBOUND_ONLY_MOVEMENTS:
            return {"kind": movement.movement_type, "movement_id": str(movement.id)}
    return None


def package_content_matches(lot: InventoryLot, quantity: Decimal, unit: str) -> bool:
    if lot.package_content_quantity is None or not lot.package_content_unit:
        return False
    return Decimal(lot.package_content_quantity) == quantity and lot.package_content_unit.casefold() == unit.casefold()


def apply_package_content(
    session: Session,
    principal: Principal,
    lot: InventoryLot,
    quantity: Decimal,
    unit: str,
    *,
    expected_row_version: int | None = None,
) -> bool:
    """Corrige conteúdo só antes de uso. Depois, só repetição idêntica. Devolve True se gravou."""
    org = _org(principal)
    if expected_row_version is not None and int(lot.row_version or 1) != int(expected_row_version):
        raise ConcurrencyError("versao_conflito")
    if package_content_matches(lot, quantity, unit):
        return False
    used = lot_downstream_use(session, org, lot)
    if used is not None:
        raise ValidationError("conteudo_embalagem_ja_usado")
    before = _lot_snapshot(lot)
    lot.package_content_quantity = quantity
    lot.package_content_unit = unit
    lot.package_content_declared_at = _now()
    lot.package_content_declared_by = principal.user_id
    lot.row_version = int(lot.row_version or 1) + 1
    session.add(
        IngredientLinkReassignment(
            organization_id=org,
            destination_ingredient_id=_item_ingredient(session, org, lot.inventory_item_id),
            source_ingredient_id=None,
            fiscal_inbound_item_id=None,
            inventory_lot_id=lot.id,
            inventory_item_from_id=lot.inventory_item_id,
            inventory_item_to_id=lot.inventory_item_id,
            before_snapshot=before,
            after_snapshot={**_lot_snapshot(lot), "kind": "package_content"},
            digest=_digest({"lot": str(lot.id), "qty": format(quantity, "f"), "unit": unit}),
            actor_user_id=principal.user_id,
        )
    )
    return True


def declare_package_content(
    session: Session,
    principal: Principal,
    lot_id: UUID,
    body: dict,
    *,
    idempotency_key,
) -> InventoryLot:
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.lot.package_content", body)
    if replay is not None:
        return _get(session, InventoryLot, org, replay.resource_id)
    lot = _get(session, InventoryLot, org, lot_id)
    quantity = _qty(body["package_content_quantity"])
    unit = str(body["package_content_unit"] or "").strip()
    if not unit:
        raise ValidationError("conteudo_embalagem_obrigatorio")
    expected = body.get("expected_row_version")
    apply_package_content(
        session,
        principal,
        lot,
        quantity,
        unit,
        expected_row_version=None if expected is None else int(expected),
    )
    from app.modules.inventory_procurement.services import _store_command

    _store_command(
        session,
        org,
        idempotency_key,
        "inventory.lot.package_content",
        body,
        "inventory_lot",
        lot.id,
        principal.user_id,
    )
    return lot


def _item_ingredient(session: Session, org: UUID, inventory_item_id: UUID) -> UUID:
    item = _get(session, InventoryItem, org, inventory_item_id)
    return item.ingredient_id


def consolidate_links(
    session: Session,
    principal: Principal,
    destination_id: UUID,
    body: dict,
    *,
    idempotency_key,
) -> dict:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_MATCH)
    org = _org(principal)
    payload = {"destination_id": str(destination_id), **body}
    replay = _replay_ingredient(session, org, idempotency_key, "ingredient.links.consolidate", payload)
    if replay is not None:
        return {"replayed": True, "destination_id": str(destination_id), "linked": []}

    destination = _get(session, Ingredient, org, destination_id)
    expected = body.get("expected_row_version")
    if expected is None:
        raise ValidationError("contrato_invalido")
    if int(expected) != int(destination.row_version or 1):
        raise ConcurrencyError("versao_conflito")

    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("selecao_obrigatoria")

    dest_stock = session.scalar(
        select(InventoryItem).where(
            InventoryItem.organization_id == org,
            InventoryItem.ingredient_id == destination.id,
        )
    )
    establishments: set[UUID] = set()
    if dest_stock is not None:
        for existing in session.scalars(
            select(InventoryLot).where(InventoryLot.inventory_item_id == dest_stock.id)
        ):
            establishments.add(existing.establishment_id)

    linked = []
    for raw in entries:
        lot_id = UUID(str(raw["inventory_lot_id"]))
        lot = _get(session, InventoryLot, org, lot_id)
        if dest_stock is None:
            dest_stock = InventoryItem(
                organization_id=org,
                ingredient_id=destination.id,
                unit_code=lot.unit_code,
                lot_control="optional",
                created_by_user_id=principal.user_id,
            )
            session.add(dest_stock)
            session.flush()
        elif dest_stock.unit_code.casefold() != lot.unit_code.casefold():
            raise ValidationError("unidade_incompativel")
        if establishments and lot.establishment_id not in establishments:
            raise ValidationError("estabelecimento_incompativel")
        establishments.add(lot.establishment_id)

        source_item = session.get(InventoryItem, lot.inventory_item_id)
        source_ingredient_id = None if source_item is None else source_item.ingredient_id
        if source_item is not None and source_item.organization_id != org:
            raise ValidationError("organizacao_incompativel")

        fiscal_id = raw.get("fiscal_inbound_item_id")
        fiscal = None
        if fiscal_id:
            fiscal = session.get(FiscalInboundItem, UUID(str(fiscal_id)))
            if fiscal is None or fiscal.organization_id != org:
                raise ValidationError("organizacao_incompativel")

        already = lot.inventory_item_id == dest_stock.id
        before = {
            "lot": _lot_snapshot(lot),
            "fiscal_target": None if fiscal is None else str(fiscal.target_id),
            "fiscal_inventory_item": None if fiscal is None else str(fiscal.inventory_item_id),
            "received_quantity": _text(lot.received_quantity),
            "unit_cost": None if fiscal is None else _text(fiscal.unit_cost),
        }
        digest = _digest(
            {
                "lot": str(lot.id),
                "dest": str(destination.id),
                "stock": str(dest_stock.id),
            }
        )
        existing = session.scalar(
            select(IngredientLinkReassignment).where(
                IngredientLinkReassignment.organization_id == org,
                IngredientLinkReassignment.inventory_lot_id == lot.id,
                IngredientLinkReassignment.destination_ingredient_id == destination.id,
                IngredientLinkReassignment.digest == digest,
            )
        )
        if existing is not None or already:
            linked.append({"inventory_lot_id": str(lot.id), "status": "already_linked"})
            continue

        lot.inventory_item_id = dest_stock.id
        for balance in session.scalars(
            select(InventoryBalance).where(InventoryBalance.inventory_lot_id == lot.id)
        ):
            if balance.organization_id != org:
                raise ValidationError("organizacao_incompativel")
            balance.inventory_item_id = dest_stock.id
        for receipt in session.scalars(
            select(ProcurementReceiptItem).where(ProcurementReceiptItem.inventory_lot_id == lot.id)
        ):
            if receipt.organization_id != org:
                raise ValidationError("organizacao_incompativel")
            receipt.inventory_item_id = dest_stock.id
            if fiscal is None and receipt.fiscal_inbound_item_id:
                fiscal = session.get(FiscalInboundItem, receipt.fiscal_inbound_item_id)
        for allocation in session.scalars(
            select(InventoryReservationAllocation).where(
                InventoryReservationAllocation.inventory_lot_id == lot.id
            )
        ):
            if allocation.organization_id != org:
                raise ValidationError("organizacao_incompativel")
            reservation = session.get(InventoryReservation, allocation.inventory_reservation_id)
            if reservation is None or reservation.organization_id != org:
                raise ValidationError("organizacao_incompativel")
            reservation.inventory_item_id = dest_stock.id
        if fiscal is not None:
            fiscal.target_type = "ingredient"
            fiscal.target_id = destination.id
            fiscal.inventory_item_id = dest_stock.id
            for match in session.scalars(
                select(FiscalItemMatch).where(FiscalItemMatch.fiscal_inbound_item_id == fiscal.id)
            ):
                match.target_id = destination.id
                match.inventory_item_id = dest_stock.id

        if raw.get("package_content_quantity") and raw.get("package_content_unit"):
            apply_package_content(
                session,
                principal,
                lot,
                _qty(raw["package_content_quantity"]),
                str(raw["package_content_unit"]).strip(),
                expected_row_version=None
                if raw.get("expected_row_version") is None
                else int(raw["expected_row_version"]),
            )

        session.add(
            IngredientLinkReassignment(
                organization_id=org,
                destination_ingredient_id=destination.id,
                source_ingredient_id=source_ingredient_id,
                fiscal_inbound_item_id=None if fiscal is None else fiscal.id,
                inventory_lot_id=lot.id,
                inventory_item_from_id=None if source_item is None else source_item.id,
                inventory_item_to_id=dest_stock.id,
                before_snapshot=before,
                after_snapshot={
                    "lot": _lot_snapshot(lot),
                    "fiscal_target": None if fiscal is None else str(fiscal.target_id),
                    "received_quantity": _text(lot.received_quantity),
                    "unit_cost": None if fiscal is None else _text(fiscal.unit_cost),
                },
                digest=digest,
                actor_user_id=principal.user_id,
            )
        )
        linked.append({"inventory_lot_id": str(lot.id), "status": "linked"})

    destination.row_version = int(destination.row_version or 1) + 1
    session.add(
        IngredientCommand(
            organization_id=org,
            idempotency_key=idempotency_key,
            command="ingredient.links.consolidate",
            payload_digest=_digest(payload),
            resource_type="ingredient",
            resource_id=destination.id,
            actor_user_id=principal.user_id,
        )
    )
    session.flush()
    return {
        "replayed": False,
        "destination_id": str(destination.id),
        "destination_name": destination.display_name,
        "row_version": destination.row_version,
        "linked": linked,
    }


def recipe_quantity_from_lot(
    lot: InventoryLot,
    *,
    wanted_quantity: Decimal,
    wanted_unit: str,
) -> tuple[Decimal, dict]:
    """Converte quantidade da receita para a unidade do lote, se o conteúdo foi declarado."""
    wanted_unit = wanted_unit.casefold()
    lot_unit = (lot.unit_code or "").casefold()
    if lot_unit == wanted_unit:
        return wanted_quantity, {"source": "same_unit"}
    if lot.package_content_quantity is None or not lot.package_content_unit:
        raise ValidationError("conteudo_embalagem_ausente")
    pack_unit = lot.package_content_unit.casefold()
    pack_qty = Decimal(lot.package_content_quantity)
    if pack_qty <= 0:
        raise ValidationError("conteudo_embalagem_ausente")
    if pack_unit == wanted_unit:
        return (wanted_quantity / pack_qty), {"source": "declared_package_content", "factor": format(pack_qty, "f")}
    if pack_unit == "kg" and wanted_unit == "g":
        return (wanted_quantity / (pack_qty * Decimal("1000"))), {
            "source": "declared_package_content",
            "factor": format(pack_qty * Decimal("1000"), "f"),
        }
    if pack_unit == "g" and wanted_unit == "kg":
        return (wanted_quantity / (pack_qty / Decimal("1000"))), {
            "source": "declared_package_content",
            "factor": format(pack_qty / Decimal("1000"), "f"),
        }
    raise ValidationError("conteudo_embalagem_ausente")


def reconcile_lot(session: Session, principal: Principal, lot_id: UUID) -> dict:
    """Soma movimentos do lote contra o saldo. Não edita o histórico nem cria saldo."""
    require_permission(principal, PERMISSION_INVENTORY_READ)
    org = _org(principal)
    lot = _get(session, InventoryLot, org, lot_id)
    current_item = session.get(InventoryItem, lot.inventory_item_id)
    current_ingredient = None
    if current_item is not None:
        current_ingredient = session.get(Ingredient, current_item.ingredient_id)
    movements = list(
        session.scalars(
            select(InventoryMovement)
            .where(
                InventoryMovement.organization_id == org,
                InventoryMovement.inventory_lot_id == lot.id,
            )
            .order_by(InventoryMovement.created_at.asc())
        )
    )
    signed = sum((Decimal(row.canonical_quantity) * Decimal(row.sign) for row in movements), Decimal("0"))
    balance = session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.organization_id == org,
            InventoryBalance.inventory_lot_id == lot.id,
        )
    )
    physical = Decimal("0") if balance is None else Decimal(balance.physical_quantity)
    reserved = Decimal("0") if balance is None else Decimal(balance.reserved_quantity)
    reassignments = list(
        session.scalars(
            select(IngredientLinkReassignment)
            .where(
                IngredientLinkReassignment.organization_id == org,
                IngredientLinkReassignment.inventory_lot_id == lot.id,
            )
            .order_by(IngredientLinkReassignment.created_at.asc())
        )
    )
    recorded_items = []
    seen: set[str] = set()
    for movement in movements:
        key = str(movement.inventory_item_id)
        if key in seen:
            continue
        seen.add(key)
        item = session.get(InventoryItem, movement.inventory_item_id)
        ingredient = None if item is None else session.get(Ingredient, item.ingredient_id)
        recorded_items.append(
            {
                "inventory_item_id": key,
                "ingredient_id": None if ingredient is None else str(ingredient.id),
                "ingredient_name": None if ingredient is None else ingredient.display_name,
            }
        )
    return {
        "inventory_lot_id": str(lot.id),
        "internal_lot_code": lot.internal_lot_code,
        "current_inventory_item_id": str(lot.inventory_item_id),
        "current_ingredient_id": None if current_ingredient is None else str(current_ingredient.id),
        "current_ingredient_name": None if current_ingredient is None else current_ingredient.display_name,
        "movement_count": len(movements),
        "signed_movement_quantity": format(signed, "f"),
        "physical_quantity": format(physical, "f"),
        "reserved_quantity": format(reserved, "f"),
        "matched": signed == physical,
        "hidden_chain": False,
        "recorded_inventory_items": recorded_items,
        "reclassified": any(str(row.inventory_item_id) != str(lot.inventory_item_id) for row in movements),
        "reassignments": [
            {
                "id": str(row.id),
                "source_ingredient_id": None if row.source_ingredient_id is None else str(row.source_ingredient_id),
                "destination_ingredient_id": str(row.destination_ingredient_id),
                "inventory_item_from_id": None if row.inventory_item_from_id is None else str(row.inventory_item_from_id),
                "inventory_item_to_id": str(row.inventory_item_to_id),
                "created_at": row.created_at.isoformat(),
            }
            for row in reassignments
        ],
        "movements": [
            {
                "id": str(row.id),
                "movement_type": row.movement_type,
                "recorded_inventory_item_id": str(row.inventory_item_id),
                "current_inventory_item_id": str(lot.inventory_item_id),
                "quantity": format(Decimal(row.quantity), "f"),
                "canonical_quantity": format(Decimal(row.canonical_quantity), "f"),
                "sign": row.sign,
                "reclassified": str(row.inventory_item_id) != str(lot.inventory_item_id),
            }
            for row in movements
        ],
    }
