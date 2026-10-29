from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import TechnicalProduct
from app.modules.identity_organization.models import AppUser
from app.modules.ingredient_catalog.models import Ingredient, Supplier
from app.modules.inventory_procurement.eligibility import (
    is_lot_production_eligible,
    project_balance_quantities,
)
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryCountSession,
    InventoryItem,
    InventoryLocation,
    InventoryLot,
    InventoryMovement,
    InventoryPick,
    InventoryPickLine,
    InventoryPolicy,
    InventoryPolicyVersion,
    InventoryReplenishmentSuggestion,
    InventoryReservation,
    InventoryReservationAllocation,
    ProcurementOrder,
    ProcurementQuotation,
    ProcurementReceipt,
    ProcurementRequisition,
    ProcurementReturn,
)
from app.modules.production_planning.models import ProductionOrder


def _dec(value) -> str | None:
    if value is None:
        return None
    return format(Decimal(value), "f")


def _load_balance_context(session: Session, rows: list[InventoryBalance]) -> dict:
    """Lote + item + local + ingrediente em consultas em lote (sem N+1)."""
    if not rows:
        return {"lots": {}, "items": {}, "locations": {}, "ingredients": {}}
    lot_ids = {row.inventory_lot_id for row in rows}
    item_ids = {row.inventory_item_id for row in rows}
    location_ids = {row.inventory_location_id for row in rows}
    lots = {
        row.id: row
        for row in session.scalars(select(InventoryLot).where(InventoryLot.id.in_(lot_ids))).all()
    }
    items = {
        row.id: row
        for row in session.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all()
    }
    locations = {
        row.id: row
        for row in session.scalars(
            select(InventoryLocation).where(InventoryLocation.id.in_(location_ids))
        ).all()
    }
    ingredient_ids = {item.ingredient_id for item in items.values()}
    ingredients = (
        {
            row.id: row
            for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
        }
        if ingredient_ids
        else {}
    )
    return {"lots": lots, "items": items, "locations": locations, "ingredients": ingredients}


def _load_lot_context(session: Session, rows: list[InventoryLot]) -> dict:
    if not rows:
        return {"items": {}, "locations": {}, "ingredients": {}, "balances_by_lot": {}}
    item_ids = {row.inventory_item_id for row in rows}
    location_ids = {row.inventory_location_id for row in rows}
    lot_ids = {row.id for row in rows}
    items = {
        row.id: row
        for row in session.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all()
    }
    locations = {
        row.id: row
        for row in session.scalars(
            select(InventoryLocation).where(InventoryLocation.id.in_(location_ids))
        ).all()
    }
    ingredient_ids = {item.ingredient_id for item in items.values()}
    ingredients = (
        {
            row.id: row
            for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
        }
        if ingredient_ids
        else {}
    )
    balances = list(
        session.scalars(select(InventoryBalance).where(InventoryBalance.inventory_lot_id.in_(lot_ids))).all()
    )
    balances_by_lot: dict[UUID, InventoryBalance] = {}
    for balance in balances:
        # Um saldo por (local, item, lote); no seed há um por lote.
        balances_by_lot[balance.inventory_lot_id] = balance
    return {
        "items": items,
        "locations": locations,
        "ingredients": ingredients,
        "balances_by_lot": balances_by_lot,
    }


def balances_out(rows: list[InventoryBalance], session: Session, *, as_of: date | None = None) -> list[dict]:
    ctx = _load_balance_context(session, rows)
    return [balance_out(row, session, context=ctx, as_of=as_of) for row in rows]


def lots_out(rows: list[InventoryLot], session: Session, *, as_of: date | None = None) -> list[dict]:
    ctx = _load_lot_context(session, rows)
    return [lot_out(row, session, context=ctx, as_of=as_of) for row in rows]

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


def lot_out(row: InventoryLot, session=None, *, context: dict | None = None, as_of: date | None = None) -> dict:
    item_label = None
    location_label = None
    physical = None
    reserved = None
    unreserved = None
    eligible_qty = None
    impeded = None
    unit_code = row.unit_code
    eligible, reason = is_lot_production_eligible(row, as_of=as_of)

    if context is not None:
        item = context["items"].get(row.inventory_item_id)
        location = context["locations"].get(row.inventory_location_id)
        if item is not None:
            ingredient = context["ingredients"].get(item.ingredient_id)
            item_label = ingredient.display_name if ingredient is not None else None
            unit_code = item.unit_code or unit_code
        if location is not None:
            location_label = location.display_name or location.code
        balance = context["balances_by_lot"].get(row.id)
        if balance is not None:
            physical_d = Decimal(balance.physical_quantity)
            reserved_d = Decimal(balance.reserved_quantity)
            projected = project_balance_quantities(physical_d, reserved_d, eligible=eligible)
            physical = _dec(physical_d)
            reserved = _dec(reserved_d)
            unreserved = _dec(projected["unreserved_quantity"])
            eligible_qty = _dec(projected["eligible_quantity"])
            impeded = _dec(projected["impeded_quantity"])
            unit_code = balance.unit_code or unit_code
    elif session is not None:
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
        "unit_code": unit_code,
        "physical_quantity": physical,
        "reserved_quantity": reserved,
        "unreserved_quantity": unreserved,
        "available_quantity": unreserved,
        "eligible_quantity": eligible_qty,
        "impeded_quantity": impeded,
        "production_eligible": eligible,
        "eligibility_reason": reason,
        "row_version": row.row_version,
    }


def balance_out(
    row: InventoryBalance,
    session=None,
    *,
    context: dict | None = None,
    as_of: date | None = None,
) -> dict:
    physical = Decimal(row.physical_quantity)
    reserved = Decimal(row.reserved_quantity)
    item_label = None
    location_label = None
    lot_code = None
    lot_status = None
    lot: InventoryLot | None = None

    if context is not None:
        item = context["items"].get(row.inventory_item_id)
        location = context["locations"].get(row.inventory_location_id)
        lot = context["lots"].get(row.inventory_lot_id)
        if item is not None:
            ingredient = context["ingredients"].get(item.ingredient_id)
            item_label = ingredient.display_name if ingredient is not None else None
        if location is not None:
            location_label = location.display_name or location.code
        if lot is not None:
            lot_code = lot.internal_lot_code
            lot_status = lot.status
    elif session is not None:
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
            lot_status = lot.status

    eligible, reason = is_lot_production_eligible(lot, as_of=as_of)
    projected = project_balance_quantities(physical, reserved, eligible=eligible)
    unreserved = projected["unreserved_quantity"]
    return {
        "id": str(row.id),
        "inventory_item_id": str(row.inventory_item_id),
        "inventory_location_id": str(row.inventory_location_id),
        "inventory_lot_id": str(row.inventory_lot_id),
        "item_label": item_label,
        "location_label": location_label,
        "lot_code": lot_code,
        "lot_status": lot_status,
        "unit_code": row.unit_code,
        "physical_quantity": _dec(physical),
        "reserved_quantity": _dec(reserved),
        # Contrato legado: available = physical - reserved (não reservado).
        "available_quantity": _dec(unreserved),
        "unreserved_quantity": _dec(unreserved),
        "eligible_quantity": _dec(projected["eligible_quantity"]),
        "impeded_quantity": _dec(projected["impeded_quantity"]),
        "production_eligible": eligible,
        "eligibility_reason": reason,
    }


def movement_out(row: InventoryMovement, session=None, *, context: dict | None = None) -> dict:
    item_label = None
    lot_code = None
    from_label = None
    to_label = None
    actor_label = None
    document_label = None
    unit_code = row.unit_code

    items = (context or {}).get("items", {})
    lots = (context or {}).get("lots", {})
    locations = (context or {}).get("locations", {})
    ingredients = (context or {}).get("ingredients", {})
    users = (context or {}).get("users", {})
    documents = (context or {}).get("documents", {})

    item = items.get(row.inventory_item_id)
    if item is None and session is not None:
        item = session.get(InventoryItem, row.inventory_item_id)
    if item is not None:
        ingredient = ingredients.get(item.ingredient_id)
        if ingredient is None and session is not None:
            ingredient = session.get(Ingredient, item.ingredient_id)
        item_label = ingredient.display_name if ingredient is not None else None
        unit_code = item.unit_code or unit_code

    if row.inventory_lot_id:
        lot = lots.get(row.inventory_lot_id)
        if lot is None and session is not None:
            lot = session.get(InventoryLot, row.inventory_lot_id)
        if lot is not None:
            lot_code = lot.internal_lot_code

    if row.from_location_id:
        loc = locations.get(row.from_location_id)
        if loc is None and session is not None:
            loc = session.get(InventoryLocation, row.from_location_id)
        if loc is not None:
            from_label = loc.display_name or loc.code
    if row.to_location_id:
        loc = locations.get(row.to_location_id)
        if loc is None and session is not None:
            loc = session.get(InventoryLocation, row.to_location_id)
        if loc is not None:
            to_label = loc.display_name or loc.code

    actor = users.get(row.actor_user_id)
    if actor is None and session is not None:
        actor = session.get(AppUser, row.actor_user_id)
    if actor is not None:
        actor_label = actor.display_name

    if row.origin_id is not None:
        document_label = documents.get((row.origin_type, row.origin_id))
    if document_label is None and row.procurement_receipt_id is not None:
        document_label = documents.get(("procurement_receipt", row.procurement_receipt_id))
    if document_label is None and row.production_order_id is not None:
        document_label = documents.get(("production_order", row.production_order_id))

    return {
        "id": str(row.id),
        "movement_type": row.movement_type,
        "inventory_item_id": str(row.inventory_item_id),
        "inventory_lot_id": None if row.inventory_lot_id is None else str(row.inventory_lot_id),
        "item_label": item_label,
        "lot_code": lot_code,
        "from_location_id": None if row.from_location_id is None else str(row.from_location_id),
        "to_location_id": None if row.to_location_id is None else str(row.to_location_id),
        "from_location_label": from_label,
        "to_location_label": to_label,
        "quantity": _dec(row.quantity),
        "canonical_quantity": _dec(row.canonical_quantity),
        "unit_code": unit_code,
        "sign": row.sign,
        "nature": row.nature,
        "origin_type": row.origin_type,
        "origin_id": None if row.origin_id is None else str(row.origin_id),
        "document_label": document_label,
        "reason": row.reason,
        "actor_label": actor_label,
        "effective_at": row.effective_at.isoformat(),
        "reverses_id": None if row.reverses_id is None else str(row.reverses_id),
        "content_hash": row.content_hash,
        "created_at": row.created_at.isoformat(),
    }


def _load_movement_context(session: Session, rows: list[InventoryMovement]) -> dict:
    if not rows:
        return {"items": {}, "lots": {}, "locations": {}, "ingredients": {}, "users": {}, "documents": {}}
    item_ids = {row.inventory_item_id for row in rows}
    lot_ids = {row.inventory_lot_id for row in rows if row.inventory_lot_id}
    location_ids = {row.from_location_id for row in rows if row.from_location_id} | {
        row.to_location_id for row in rows if row.to_location_id
    }
    user_ids = {row.actor_user_id for row in rows}
    items = {
        row.id: row
        for row in session.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all()
    }
    lots = (
        {
            row.id: row
            for row in session.scalars(select(InventoryLot).where(InventoryLot.id.in_(lot_ids))).all()
        }
        if lot_ids
        else {}
    )
    locations = (
        {
            row.id: row
            for row in session.scalars(
                select(InventoryLocation).where(InventoryLocation.id.in_(location_ids))
            ).all()
        }
        if location_ids
        else {}
    )
    ingredient_ids = {item.ingredient_id for item in items.values()}
    ingredients = (
        {
            row.id: row
            for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
        }
        if ingredient_ids
        else {}
    )
    users = {
        row.id: row for row in session.scalars(select(AppUser).where(AppUser.id.in_(user_ids))).all()
    }
    documents: dict[tuple[str, UUID], str] = {}
    receipt_ids = {
        row.procurement_receipt_id for row in rows if row.procurement_receipt_id
    } | {
        row.origin_id
        for row in rows
        if row.origin_type == "procurement_receipt" and row.origin_id
    }
    if receipt_ids:
        for receipt in session.scalars(
            select(ProcurementReceipt).where(ProcurementReceipt.id.in_(receipt_ids))
        ).all():
            documents[("procurement_receipt", receipt.id)] = receipt.public_code
    return_ids = {
        row.origin_id
        for row in rows
        if row.origin_type == "procurement_return" and row.origin_id
    }
    if return_ids:
        for ret in session.scalars(
            select(ProcurementReturn).where(ProcurementReturn.id.in_(return_ids))
        ).all():
            documents[("procurement_return", ret.id)] = ret.public_code
    count_ids = {
        row.inventory_count_session_id for row in rows if row.inventory_count_session_id
    } | {
        row.origin_id
        for row in rows
        if row.origin_type == "inventory_count_session" and row.origin_id
    }
    if count_ids:
        for count in session.scalars(
            select(InventoryCountSession).where(InventoryCountSession.id.in_(count_ids))
        ).all():
            documents[("inventory_count_session", count.id)] = count.public_code
    order_ids = {row.production_order_id for row in rows if row.production_order_id}
    if order_ids:
        for order in session.scalars(select(ProductionOrder).where(ProductionOrder.id.in_(order_ids))).all():
            documents[("production_order", order.id)] = order.public_code
    return {
        "items": items,
        "lots": lots,
        "locations": locations,
        "ingredients": ingredients,
        "users": users,
        "documents": documents,
    }


def movements_out(rows: list[InventoryMovement], session: Session) -> list[dict]:
    ctx = _load_movement_context(session, rows)
    return [movement_out(row, session, context=ctx) for row in rows]


def reservation_out(
    row: InventoryReservation,
    allocations=None,
    session=None,
    *,
    context: dict | None = None,
) -> dict:
    item_label = None
    order_code = None
    unit_code = row.unit_code
    items = (context or {}).get("items", {})
    ingredients = (context or {}).get("ingredients", {})
    orders = (context or {}).get("orders", {})
    lots = (context or {}).get("lots", {})
    locations = (context or {}).get("locations", {})

    item = items.get(row.inventory_item_id)
    if item is None and session is not None:
        item = session.get(InventoryItem, row.inventory_item_id)
    if item is not None:
        ingredient = ingredients.get(item.ingredient_id)
        if ingredient is None and session is not None:
            ingredient = session.get(Ingredient, item.ingredient_id)
        item_label = ingredient.display_name if ingredient is not None else None
        unit_code = item.unit_code or unit_code

    order = orders.get(row.production_order_id)
    if order is None and session is not None:
        order = session.get(ProductionOrder, row.production_order_id)
    if order is not None:
        order_code = order.public_code

    alloc_payload = []
    for item_alloc in allocations or []:
        lot = lots.get(item_alloc.inventory_lot_id)
        loc = locations.get(item_alloc.inventory_location_id)
        if lot is None and session is not None:
            lot = session.get(InventoryLot, item_alloc.inventory_lot_id)
        if loc is None and session is not None:
            loc = session.get(InventoryLocation, item_alloc.inventory_location_id)
        alloc_payload.append(
            {
                "lot_id": str(item_alloc.inventory_lot_id),
                "lot_code": lot.internal_lot_code if lot is not None else None,
                "location_id": str(item_alloc.inventory_location_id),
                "location_label": (loc.display_name or loc.code) if loc is not None else None,
                "quantity": _dec(item_alloc.quantity),
            }
        )

    return {
        "id": str(row.id),
        "production_order_id": str(row.production_order_id),
        "order_public_code": order_code,
        "inventory_item_id": str(row.inventory_item_id),
        "item_label": item_label,
        "required_quantity": _dec(row.required_quantity),
        "reserved_quantity": _dec(row.reserved_quantity),
        "shortage_quantity": _dec(row.shortage_quantity),
        "unit_code": unit_code,
        "status": row.status,
        "adopted": row.adopted,
        "reason": row.reason,
        "created_at": row.created_at.isoformat(),
        "row_version": row.row_version,
        "allocations": alloc_payload,
    }


def reservations_out(
    rows: list[InventoryReservation],
    session: Session,
    allocations_by_reservation: dict[UUID, list] | None = None,
) -> list[dict]:
    if not rows:
        return []
    reservation_ids = {row.id for row in rows}
    if allocations_by_reservation is None:
        allocations = list(
            session.scalars(
                select(InventoryReservationAllocation).where(
                    InventoryReservationAllocation.inventory_reservation_id.in_(reservation_ids)
                )
            ).all()
        )
        allocations_by_reservation = {}
        for alloc in allocations:
            allocations_by_reservation.setdefault(alloc.inventory_reservation_id, []).append(alloc)
    item_ids = {row.inventory_item_id for row in rows}
    order_ids = {row.production_order_id for row in rows}
    lot_ids = {
        alloc.inventory_lot_id
        for allocs in allocations_by_reservation.values()
        for alloc in allocs
    }
    location_ids = {
        alloc.inventory_location_id
        for allocs in allocations_by_reservation.values()
        for alloc in allocs
    }
    items = {
        row.id: row
        for row in session.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all()
    }
    orders = {
        row.id: row
        for row in session.scalars(select(ProductionOrder).where(ProductionOrder.id.in_(order_ids))).all()
    }
    lots = (
        {
            row.id: row
            for row in session.scalars(select(InventoryLot).where(InventoryLot.id.in_(lot_ids))).all()
        }
        if lot_ids
        else {}
    )
    locations = (
        {
            row.id: row
            for row in session.scalars(
                select(InventoryLocation).where(InventoryLocation.id.in_(location_ids))
            ).all()
        }
        if location_ids
        else {}
    )
    ingredient_ids = {item.ingredient_id for item in items.values()}
    ingredients = (
        {
            row.id: row
            for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
        }
        if ingredient_ids
        else {}
    )
    ctx = {
        "items": items,
        "orders": orders,
        "lots": lots,
        "locations": locations,
        "ingredients": ingredients,
    }
    return [
        reservation_out(
            row,
            allocations_by_reservation.get(row.id, []),
            session,
            context=ctx,
        )
        for row in rows
    ]


def pick_out(row: InventoryPick, lines=None, session=None, *, context: dict | None = None) -> dict:
    order_code = None
    product_label = None
    created_by_label = None
    orders = (context or {}).get("orders", {})
    products = (context or {}).get("products", {})
    users = (context or {}).get("users", {})
    items = (context or {}).get("items", {})
    ingredients = (context or {}).get("ingredients", {})
    lots = (context or {}).get("lots", {})
    locations = (context or {}).get("locations", {})

    order = orders.get(row.production_order_id)
    if order is None and session is not None:
        order = session.get(ProductionOrder, row.production_order_id)
    if order is not None:
        order_code = order.public_code
        product = products.get(order.technical_product_id)
        if product is None and session is not None:
            product = session.get(TechnicalProduct, order.technical_product_id)
        if product is not None:
            product_label = product.display_name

    creator = users.get(row.created_by_user_id)
    if creator is None and session is not None:
        creator = session.get(AppUser, row.created_by_user_id)
    if creator is not None:
        created_by_label = creator.display_name

    line_payload = []
    for line in lines or []:
        item = items.get(line.inventory_item_id)
        lot = lots.get(line.inventory_lot_id)
        loc = locations.get(line.inventory_location_id)
        if item is None and session is not None:
            item = session.get(InventoryItem, line.inventory_item_id)
        if lot is None and session is not None:
            lot = session.get(InventoryLot, line.inventory_lot_id)
        if loc is None and session is not None:
            loc = session.get(InventoryLocation, line.inventory_location_id)
        item_label = None
        unit_code = None
        if item is not None:
            ingredient = ingredients.get(item.ingredient_id)
            if ingredient is None and session is not None:
                ingredient = session.get(Ingredient, item.ingredient_id)
            item_label = ingredient.display_name if ingredient is not None else None
            unit_code = item.unit_code
        line_payload.append(
            {
                "id": str(line.id),
                "inventory_item_id": str(line.inventory_item_id),
                "item_label": item_label,
                "lot_id": str(line.inventory_lot_id),
                "lot_code": lot.internal_lot_code if lot is not None else None,
                "location_id": str(line.inventory_location_id),
                "location_label": (loc.display_name or loc.code) if loc is not None else None,
                "quantity": _dec(line.quantity),
                "unit_code": unit_code,
                "suggested": line.suggested,
                "substituted": line.substituted,
                "reason": line.reason,
            }
        )

    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "production_order_id": str(row.production_order_id),
        "order_public_code": order_code,
        "product_label": product_label,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "created_by_label": created_by_label,
        "line_count": len(line_payload),
        "row_version": row.row_version,
        "lines": line_payload,
    }


def picks_out(
    rows: list[InventoryPick],
    session: Session,
    lines_by_pick: dict[UUID, list] | None = None,
) -> list[dict]:
    if not rows:
        return []
    pick_ids = {row.id for row in rows}
    if lines_by_pick is None:
        lines = list(
            session.scalars(
                select(InventoryPickLine).where(InventoryPickLine.inventory_pick_id.in_(pick_ids))
            ).all()
        )
        lines_by_pick = {}
        for line in lines:
            lines_by_pick.setdefault(line.inventory_pick_id, []).append(line)
    order_ids = {row.production_order_id for row in rows}
    user_ids = {row.created_by_user_id for row in rows}
    item_ids = {
        line.inventory_item_id for pick_lines in lines_by_pick.values() for line in pick_lines
    }
    lot_ids = {line.inventory_lot_id for pick_lines in lines_by_pick.values() for line in pick_lines}
    location_ids = {
        line.inventory_location_id for pick_lines in lines_by_pick.values() for line in pick_lines
    }
    orders = {
        row.id: row
        for row in session.scalars(select(ProductionOrder).where(ProductionOrder.id.in_(order_ids))).all()
    }
    product_ids = {order.technical_product_id for order in orders.values()}
    products = (
        {
            row.id: row
            for row in session.scalars(
                select(TechnicalProduct).where(TechnicalProduct.id.in_(product_ids))
            ).all()
        }
        if product_ids
        else {}
    )
    users = {
        row.id: row for row in session.scalars(select(AppUser).where(AppUser.id.in_(user_ids))).all()
    }
    items = (
        {
            row.id: row
            for row in session.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all()
        }
        if item_ids
        else {}
    )
    lots = (
        {
            row.id: row
            for row in session.scalars(select(InventoryLot).where(InventoryLot.id.in_(lot_ids))).all()
        }
        if lot_ids
        else {}
    )
    locations = (
        {
            row.id: row
            for row in session.scalars(
                select(InventoryLocation).where(InventoryLocation.id.in_(location_ids))
            ).all()
        }
        if location_ids
        else {}
    )
    ingredient_ids = {item.ingredient_id for item in items.values()}
    ingredients = (
        {
            row.id: row
            for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
        }
        if ingredient_ids
        else {}
    )
    ctx = {
        "orders": orders,
        "products": products,
        "users": users,
        "items": items,
        "lots": lots,
        "locations": locations,
        "ingredients": ingredients,
    }
    return [
        pick_out(row, lines_by_pick.get(row.id, []), session, context=ctx) for row in rows
    ]


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
