from decimal import Decimal

from app.modules.ingredient_catalog.models import Ingredient, Supplier
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryCountSession,
    InventoryItem,
    InventoryLocation,
    InventoryLot,
    InventoryMovement,
    InventoryPick,
    InventoryPolicy,
    InventoryPolicyVersion,
    InventoryReplenishmentSuggestion,
    InventoryReservation,
    ProcurementOrder,
    ProcurementQuotation,
    ProcurementReceipt,
    ProcurementRequisition,
    ProcurementReturn,
)


def _dec(value) -> str | None:
    if value is None:
        return None
    return format(Decimal(value), "f")


def policy_out(policy: InventoryPolicy, version: InventoryPolicyVersion | None) -> dict:
    return {
        "id": str(policy.id),
        "code": policy.code,
        "display_name": policy.display_name,
        "status": policy.status,
        "establishment_id": None if policy.establishment_id is None else str(policy.establishment_id),
        "row_version": policy.row_version,
        "version": None
        if version is None
        else {
            "id": str(version.id),
            "version_number": version.version_number,
            "status": version.status,
            "allow_negative_balance": version.allow_negative_balance,
            "lot_mode": version.lot_mode,
            "expiry_required": version.expiry_required,
            "lot_consumption": version.lot_consumption,
            "receipt_tolerance_percent": _dec(version.receipt_tolerance_percent),
            "count_tolerance_percent": _dec(version.count_tolerance_percent),
            "reserve_on_release": version.reserve_on_release,
            "adjust_requires_approval": version.adjust_requires_approval,
            "expiry_alert_days": version.expiry_alert_days,
            "algorithm_name": version.algorithm_name,
            "algorithm_version": version.algorithm_version,
        },
    }


def location_out(row: InventoryLocation) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "kind": row.kind,
        "status": row.status,
        "establishment_id": str(row.establishment_id),
        "row_version": row.row_version,
    }


def item_out(row: InventoryItem) -> dict:
    return {
        "id": str(row.id),
        "ingredient_id": str(row.ingredient_id),
        "unit_code": row.unit_code,
        "lot_control": row.lot_control,
        "expiry_control": row.expiry_control,
        "reorder_point": _dec(row.reorder_point),
        "safety_stock": _dec(row.safety_stock),
        "target_quantity": _dec(row.target_quantity),
        "status": row.status,
        "row_version": row.row_version,
    }


def lot_out(row: InventoryLot, session=None) -> dict:
    item_label = None
    location_label = None
    if session is not None:
        item = session.get(InventoryItem, row.inventory_item_id)
        location = session.get(InventoryLocation, row.inventory_location_id)
        if item is not None:
            ingredient = session.get(Ingredient, item.ingredient_id)
            item_label = ingredient.display_name if ingredient is not None else None
        if location is not None:
            location_label = location.display_name or location.code
    return {
        "id": str(row.id),
        "internal_lot_code": row.internal_lot_code,
        "supplier_lot_code": row.supplier_lot_code,
        "inventory_item_id": str(row.inventory_item_id),
        "inventory_location_id": str(row.inventory_location_id),
        "item_label": item_label,
        "location_label": location_label,
        "expires_on": None if row.expires_on is None else row.expires_on.isoformat(),
        "status": row.status,
        "received_quantity": _dec(row.received_quantity),
        "unit_code": row.unit_code,
        "row_version": row.row_version,
    }


def balance_out(row: InventoryBalance, session=None) -> dict:
    physical = Decimal(row.physical_quantity)
    reserved = Decimal(row.reserved_quantity)
    item_label = None
    location_label = None
    lot_code = None
    if session is not None:
        item = session.get(InventoryItem, row.inventory_item_id)
        location = session.get(InventoryLocation, row.inventory_location_id)
        lot = session.get(InventoryLot, row.inventory_lot_id)
        if item is not None:
            ingredient = session.get(Ingredient, item.ingredient_id)
            item_label = ingredient.display_name if ingredient is not None else None
        if location is not None:
            location_label = location.display_name or location.code
        if lot is not None:
            lot_code = lot.internal_lot_code
    return {
        "id": str(row.id),
        "inventory_item_id": str(row.inventory_item_id),
        "inventory_location_id": str(row.inventory_location_id),
        "inventory_lot_id": str(row.inventory_lot_id),
        "item_label": item_label,
        "location_label": location_label,
        "lot_code": lot_code,
        "unit_code": row.unit_code,
        "physical_quantity": _dec(physical),
        "reserved_quantity": _dec(reserved),
        "available_quantity": _dec(physical - reserved),
    }


def movement_out(row: InventoryMovement) -> dict:
    return {
        "id": str(row.id),
        "movement_type": row.movement_type,
        "inventory_item_id": str(row.inventory_item_id),
        "inventory_lot_id": None if row.inventory_lot_id is None else str(row.inventory_lot_id),
        "quantity": _dec(row.quantity),
        "canonical_quantity": _dec(row.canonical_quantity),
        "sign": row.sign,
        "origin_type": row.origin_type,
        "reason": row.reason,
        "content_hash": row.content_hash,
        "created_at": row.created_at.isoformat(),
    }


def reservation_out(row: InventoryReservation, allocations=None) -> dict:
    return {
        "id": str(row.id),
        "production_order_id": str(row.production_order_id),
        "inventory_item_id": str(row.inventory_item_id),
        "required_quantity": _dec(row.required_quantity),
        "reserved_quantity": _dec(row.reserved_quantity),
        "shortage_quantity": _dec(row.shortage_quantity),
        "status": row.status,
        "adopted": row.adopted,
        "row_version": row.row_version,
        "allocations": [
            {
                "lot_id": str(item.inventory_lot_id),
                "location_id": str(item.inventory_location_id),
                "quantity": _dec(item.quantity),
            }
            for item in allocations or []
        ],
    }


def pick_out(row: InventoryPick, lines=None) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "production_order_id": str(row.production_order_id),
        "status": row.status,
        "row_version": row.row_version,
        "lines": [
            {
                "lot_id": str(item.inventory_lot_id),
                "quantity": _dec(item.quantity),
                "suggested": item.suggested,
                "substituted": item.substituted,
            }
            for item in lines or []
        ],
    }


def count_out(row: InventoryCountSession, variances=None) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "inventory_location_id": str(row.inventory_location_id),
        "cutoff_at": row.cutoff_at.isoformat(),
        "status": row.status,
        "require_second_count": row.require_second_count,
        "row_version": row.row_version,
        "variances": variances or [],
    }


def suggestion_out(row: InventoryReplenishmentSuggestion, items=None, session=None) -> dict:
    labeled = []
    for item in items or []:
        item_label = None
        if session is not None:
            stock = session.get(InventoryItem, item.inventory_item_id)
            if stock is not None:
                ingredient = session.get(Ingredient, stock.ingredient_id)
                item_label = ingredient.display_name if ingredient is not None else None
        labeled.append(
            {
                "inventory_item_id": str(item.inventory_item_id),
                "item_label": item_label,
                "physical_quantity": _dec(item.physical_quantity),
                "reserved_quantity": _dec(item.reserved_quantity),
                "available_quantity": _dec(item.available_quantity),
                "in_transit_quantity": _dec(item.in_transit_quantity),
                "planned_demand": _dec(item.planned_demand),
                "suggested_quantity": _dec(item.suggested_quantity),
                "formula": item.formula,
                "gaps": item.gaps,
            }
        )
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "horizon_days": row.horizon_days,
        "generated_at": row.generated_at.isoformat(),
        "items": labeled,
    }


def requisition_out(row: ProcurementRequisition, items=None) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "status": row.status,
        "justification": row.justification,
        "needed_by": None if row.needed_by is None else row.needed_by.isoformat(),
        "row_version": row.row_version,
        "items": [
            {
                "id": str(item.id),
                "inventory_item_id": str(item.inventory_item_id),
                "quantity": _dec(item.quantity),
                "unit_code": item.unit_code,
            }
            for item in items or []
        ],
    }


def quotation_out(row: ProcurementQuotation, items=None, session=None) -> dict:
    supplier_name = None
    if session is not None:
        supplier = session.get(Supplier, row.supplier_id)
        supplier_name = supplier.display_name if supplier is not None else None
    return {
        "id": str(row.id),
        "supplier_id": str(row.supplier_id),
        "supplier_name": supplier_name,
        "valid_until": None if row.valid_until is None else row.valid_until.isoformat(),
        "lead_time_days": row.lead_time_days,
        "row_version": row.row_version,
        "items": [
            {
                "id": str(item.id),
                "inventory_item_id": str(item.inventory_item_id),
                "quantity": _dec(item.quantity),
                "unit_price": _dec(item.unit_price),
                "unit_code": item.unit_code,
            }
            for item in items or []
        ],
    }


def order_out(row: ProcurementOrder, items=None, session=None) -> dict:
    supplier_name = None
    if session is not None:
        supplier = session.get(Supplier, row.supplier_id)
        supplier_name = supplier.display_name if supplier is not None else None
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "supplier_id": str(row.supplier_id),
        "supplier_name": supplier_name,
        "status": row.status,
        "current_revision": row.current_revision,
        "currency": row.currency,
        "row_version": row.row_version,
        "items": [
            {
                "id": str(item.id),
                "inventory_item_id": str(item.inventory_item_id),
                "quantity": _dec(item.quantity),
                "unit_price": _dec(item.unit_price),
                "unit_code": item.unit_code,
            }
            for item in items or []
        ],
    }


def receipt_out(row: ProcurementReceipt, items=None) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "procurement_order_id": str(row.procurement_order_id),
        "status": row.status,
        "row_version": row.row_version,
        "items": [
            {
                "id": str(item.id),
                "inventory_lot_id": None if item.inventory_lot_id is None else str(item.inventory_lot_id),
                "quantity": _dec(item.quantity),
                "observed_unit_price": _dec(item.observed_unit_price),
                "divergence": item.divergence,
            }
            for item in items or []
        ],
    }


def return_out(row: ProcurementReturn) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "procurement_receipt_id": str(row.procurement_receipt_id),
        "inventory_lot_id": str(row.inventory_lot_id),
        "quantity": _dec(row.quantity),
        "reason": row.reason,
        "status": row.status,
    }
