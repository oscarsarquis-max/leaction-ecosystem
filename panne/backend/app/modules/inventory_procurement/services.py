"""Casos de uso de estoque e compras. Ledger quantitativo; decisão humana nas compras."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import ROUND_CEILING, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_INVENTORY_ADJUST,
    PERMISSION_INVENTORY_COUNT,
    PERMISSION_INVENTORY_COUNT_APPROVE,
    PERMISSION_INVENTORY_EXPIRED_OVERRIDE,
    PERMISSION_INVENTORY_ITEM_MANAGE,
    PERMISSION_INVENTORY_LOT_MANAGE,
    PERMISSION_INVENTORY_MOVE,
    PERMISSION_INVENTORY_POLICY_MANAGE,
    PERMISSION_INVENTORY_READ,
    PERMISSION_INVENTORY_RESERVE,
    PERMISSION_INVENTORY_SEPARATE,
    PERMISSION_PROCUREMENT_ORDER_APPROVE,
    PERMISSION_PROCUREMENT_ORDER_MANAGE,
    PERMISSION_PROCUREMENT_QUOTATION_MANAGE,
    PERMISSION_PROCUREMENT_READ,
    PERMISSION_PROCUREMENT_RECEIVE,
    PERMISSION_PROCUREMENT_REQUISITION_APPROVE,
    PERMISSION_PROCUREMENT_REQUISITION_CREATE,
    PERMISSION_PROCUREMENT_RETURN,
    PERMISSION_SUPPLIER_PRICE_RECORD,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.ingredient_catalog.models import (
    Ingredient,
    MeasurementUnit,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.inventory_procurement.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    BLOCKED_LOT_STATUSES,
    CODE_KINDS,
    CURRENCY,
    ITEM_STATUSES,
    LOCATION_KINDS,
    LOCATION_STATUSES,
    LOT_CONSUMPTION,
    LOT_MODES,
    PHYSICAL_IN,
    PHYSICAL_OUT,
    ZERO,
)
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryCodeCounter,
    InventoryCommand,
    InventoryConsumptionPosting,
    InventoryCountEntry,
    InventoryCountReview,
    InventoryCountScope,
    InventoryCountSession,
    InventoryItem,
    InventoryLocation,
    InventoryLot,
    InventoryMovement,
    InventoryPick,
    InventoryPickLine,
    InventoryPolicy,
    InventoryPolicyVersion,
    InventoryReplenishmentItem,
    InventoryReplenishmentSuggestion,
    InventoryReservation,
    InventoryReservationAllocation,
    ProcurementOrder,
    ProcurementOrderItem,
    ProcurementOrderRevision,
    ProcurementQuotation,
    ProcurementQuotationItem,
    ProcurementReceipt,
    ProcurementReceiptItem,
    ProcurementRequisition,
    ProcurementRequisitionItem,
    ProcurementReturn,
)
from app.modules.production_execution.models import ProductionMaterialConsumption
from app.modules.production_execution.units import convert_to_canonical_mass
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.production_planning.models import ProductionOrder, ProductionOrderMaterial
from app.modules.production_planning.support import as_decimal


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(UTC)


def _qty(value) -> Decimal:
    return as_decimal(value, "quantidade")


def _replay(session: Session, organization_id, key, command: str, payload: dict):
    if key is None:
        return None
    row = session.scalar(
        select(InventoryCommand).where(
            InventoryCommand.organization_id == organization_id,
            InventoryCommand.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != _digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def _store_command(session, organization_id, key, command, payload, resource_type, resource_id, actor_user_id):
    if key is None:
        return
    session.add(
        InventoryCommand(
            organization_id=organization_id,
            idempotency_key=key,
            command=command,
            payload_digest=_digest(payload),
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
        )
    )


def _match(row, expected_version):
    if expected_version is not None and int(row.row_version or 1) != int(expected_version):
        raise ConcurrencyError("versao_conflito")


def _next_code(session: Session, organization_id, kind: str) -> str:
    if kind not in CODE_KINDS:
        raise ValidationError("contrato_invalido")
    counter = session.scalar(
        select(InventoryCodeCounter)
        .where(
            InventoryCodeCounter.organization_id == organization_id,
            InventoryCodeCounter.kind == kind,
        )
        .with_for_update()
    )
    if counter is None:
        counter = InventoryCodeCounter(organization_id=organization_id, kind=kind, last_value=0)
        session.add(counter)
        session.flush()
        counter = session.scalar(
            select(InventoryCodeCounter)
            .where(
                InventoryCodeCounter.organization_id == organization_id,
                InventoryCodeCounter.kind == kind,
            )
            .with_for_update()
        )
    counter.last_value = int(counter.last_value) + 1
    return f"{kind}-{counter.last_value:06d}"


def published_policy(session: Session, organization_id, establishment_id=None) -> InventoryPolicyVersion:
    rows = list(
        session.scalars(
            select(InventoryPolicyVersion)
            .join(InventoryPolicy)
            .where(
                InventoryPolicyVersion.organization_id == organization_id,
                InventoryPolicyVersion.status == "published",
                InventoryPolicy.status == "published",
            )
            .order_by(InventoryPolicyVersion.version_number.desc())
        )
    )
    if not rows:
        raise ValidationError("politica_nao_publicada")
    if establishment_id is not None:
        specific = [
            row
            for row in rows
            if session.get(InventoryPolicy, row.inventory_policy_id).establishment_id == establishment_id
        ]
        if specific:
            return specific[0]
    general = [
        row
        for row in rows
        if session.get(InventoryPolicy, row.inventory_policy_id).establishment_id is None
    ]
    return general[0] if general else rows[0]


def latest_policy_version(session: Session, policy_id) -> InventoryPolicyVersion | None:
    return session.scalar(
        select(InventoryPolicyVersion)
        .where(InventoryPolicyVersion.inventory_policy_id == policy_id)
        .order_by(InventoryPolicyVersion.version_number.desc())
    )


def _get(session, model, organization_id, row_id, code="recurso_nao_encontrado"):
    row = session.get(model, row_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError(code)
    return row


def _convert(session, quantity, unit_code: str) -> tuple[Decimal, Decimal, str]:
    unit = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == unit_code))
    if unit is None:
        raise ValidationError("unidade incompatível")
    converted = convert_to_canonical_mass(session, quantity, unit.id)
    return converted.canonical_quantity, converted.factor, converted.canonical_unit_code


def _hash_lot(payload: dict) -> str:
    return _digest(payload)


def create_policy(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_POLICY_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.policy.create", body)
    if replay is not None:
        return _get(session, InventoryPolicy, org, replay.resource_id)
    lot_mode = body.get("lot_mode") or "optional"
    if lot_mode not in LOT_MODES:
        raise ValidationError("contrato_invalido")
    consumption = body.get("lot_consumption") or "fefo_suggest"
    if consumption not in LOT_CONSUMPTION:
        raise ValidationError("contrato_invalido")
    existing = session.scalar(
        select(InventoryPolicy).where(
            InventoryPolicy.organization_id == org,
            InventoryPolicy.code == body["code"],
        )
    )
    if existing is not None:
        raise ValidationError("codigo_duplicado")
    policy = InventoryPolicy(
        organization_id=org,
        establishment_id=body.get("establishment_id"),
        code=body["code"],
        display_name=body.get("display_name") or body["code"],
        created_by_user_id=principal.user_id,
    )
    session.add(policy)
    session.flush()
    session.add(
        InventoryPolicyVersion(
            organization_id=org,
            inventory_policy_id=policy.id,
            version_number=1,
            status="draft",
            allow_negative_balance=bool(body.get("allow_negative_balance", False)),
            lot_mode=lot_mode,
            expiry_required=bool(body.get("expiry_required", False)),
            lot_consumption=consumption,
            receipt_tolerance_percent=_qty(body.get("receipt_tolerance_percent") or "0"),
            count_tolerance_percent=_qty(body.get("count_tolerance_percent") or "0"),
            reserve_on_release=bool(body.get("reserve_on_release", False)),
            cancelled_order_treatment=body.get("cancelled_order_treatment") or "release_reservation",
            return_restores_available=bool(body.get("return_restores_available", True)),
            waste_reduces_physical=bool(body.get("waste_reduces_physical", True)),
            adjust_requires_approval=bool(body.get("adjust_requires_approval", True)),
            lock_location_on_count=bool(body.get("lock_location_on_count", True)),
            expiry_alert_days=int(body.get("expiry_alert_days") or 7),
            justification=body.get("justification"),
            algorithm_name=ALGORITHM_NAME,
            algorithm_version=ALGORITHM_VERSION,
            effective_from=_parse_time(body["effective_from"]),
            created_by_user_id=principal.user_id,
        )
    )
    session.flush()
    _store_command(
        session, org, idempotency_key, "inventory.policy.create", body, "inventory_policy", policy.id, principal.user_id
    )
    return policy


def publish_policy(session: Session, principal: Principal, policy_id, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_POLICY_MANAGE)
    org = _org(principal)
    payload = {"policy_id": str(policy_id)}
    replay = _replay(session, org, idempotency_key, "inventory.policy.publish", payload)
    if replay is not None:
        return _get(session, InventoryPolicy, org, replay.resource_id)
    policy = _get(session, InventoryPolicy, org, policy_id)
    _match(policy, expected_version)
    version = latest_policy_version(session, policy.id)
    if version is None or version.status != "draft":
        raise InvalidStateError("transicao_invalida")
    version.status = "published"
    policy.status = "published"
    policy.row_version = int(policy.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.policy.publish", payload, "inventory_policy", policy.id, principal.user_id
    )
    return policy


def revise_policy(session: Session, principal: Principal, policy_id, body: dict, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_POLICY_MANAGE)
    org = _org(principal)
    payload = {"policy_id": str(policy_id), **body}
    replay = _replay(session, org, idempotency_key, "inventory.policy.revise", payload)
    if replay is not None:
        return _get(session, InventoryPolicy, org, replay.resource_id)
    policy = _get(session, InventoryPolicy, org, policy_id)
    _match(policy, expected_version)
    current = latest_policy_version(session, policy.id)
    next_number = (current.version_number if current else 0) + 1
    session.add(
        InventoryPolicyVersion(
            organization_id=org,
            inventory_policy_id=policy.id,
            version_number=next_number,
            status="draft",
            allow_negative_balance=bool(body.get("allow_negative_balance", False)),
            lot_mode=body.get("lot_mode") or "optional",
            expiry_required=bool(body.get("expiry_required", False)),
            lot_consumption=body.get("lot_consumption") or "fefo_suggest",
            receipt_tolerance_percent=_qty(body.get("receipt_tolerance_percent") or "0"),
            count_tolerance_percent=_qty(body.get("count_tolerance_percent") or "0"),
            reserve_on_release=bool(body.get("reserve_on_release", False)),
            cancelled_order_treatment=body.get("cancelled_order_treatment") or "release_reservation",
            return_restores_available=bool(body.get("return_restores_available", True)),
            waste_reduces_physical=bool(body.get("waste_reduces_physical", True)),
            adjust_requires_approval=bool(body.get("adjust_requires_approval", True)),
            lock_location_on_count=bool(body.get("lock_location_on_count", True)),
            expiry_alert_days=int(body.get("expiry_alert_days") or 7),
            justification=body.get("justification"),
            algorithm_name=ALGORITHM_NAME,
            algorithm_version=ALGORITHM_VERSION,
            effective_from=_parse_time(body["effective_from"]),
            created_by_user_id=principal.user_id,
        )
    )
    policy.status = "draft"
    policy.row_version = int(policy.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.policy.revise", payload, "inventory_policy", policy.id, principal.user_id
    )
    return policy


def list_policies(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(
        session.scalars(select(InventoryPolicy).where(InventoryPolicy.organization_id == _org(principal)))
    )


def create_location(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.location.create", body)
    if replay is not None:
        return _get(session, InventoryLocation, org, replay.resource_id)
    if body.get("kind") not in LOCATION_KINDS:
        raise ValidationError("contrato_invalido")
    row = InventoryLocation(
        organization_id=org,
        establishment_id=body["establishment_id"],
        code=body["code"],
        display_name=body.get("display_name") or body["code"],
        kind=body["kind"],
        responsible_user_id=body.get("responsible_user_id"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "inventory.location.create", body, "inventory_location", row.id, principal.user_id
    )
    return row


def set_location_status(session, principal, location_id, status, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    org = _org(principal)
    payload = {"location_id": str(location_id), "status": status}
    replay = _replay(session, org, idempotency_key, "inventory.location.status", payload)
    if replay is not None:
        return _get(session, InventoryLocation, org, replay.resource_id)
    if status not in LOCATION_STATUSES:
        raise ValidationError("contrato_invalido")
    row = _get(session, InventoryLocation, org, location_id)
    _match(row, expected_version)
    row.status = status
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.location.status", payload, "inventory_location", row.id, principal.user_id
    )
    return row


def create_item(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.item.create", body)
    if replay is not None:
        return _get(session, InventoryItem, org, replay.resource_id)
    ingredient = session.get(Ingredient, body["ingredient_id"])
    if ingredient is None or ingredient.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    unit = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == body["unit_code"]))
    if unit is None:
        raise ValidationError("unidade incompatível")
    lot_control = body.get("lot_control") or "optional"
    if lot_control not in LOT_MODES:
        raise ValidationError("contrato_invalido")
    row = InventoryItem(
        organization_id=org,
        ingredient_id=ingredient.id,
        unit_code=body["unit_code"],
        lot_control=lot_control,
        expiry_control=bool(body.get("expiry_control", False)),
        reorder_point=_qty(body["reorder_point"]) if body.get("reorder_point") else None,
        safety_stock=_qty(body["safety_stock"]) if body.get("safety_stock") else None,
        target_quantity=_qty(body["target_quantity"]) if body.get("target_quantity") else None,
        preferred_supplier_id=body.get("preferred_supplier_id"),
        preferred_supplier_item_id=body.get("preferred_supplier_item_id"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "inventory.item.create", body, "inventory_item", row.id, principal.user_id
    )
    return row


def set_item_status(session, principal, item_id, status, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
    org = _org(principal)
    payload = {"item_id": str(item_id), "status": status}
    replay = _replay(session, org, idempotency_key, "inventory.item.status", payload)
    if replay is not None:
        return _get(session, InventoryItem, org, replay.resource_id)
    if status not in ITEM_STATUSES:
        raise ValidationError("contrato_invalido")
    row = _get(session, InventoryItem, org, item_id)
    _match(row, expected_version)
    row.status = status
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.item.status", payload, "inventory_item", row.id, principal.user_id
    )
    return row


def list_locations(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(session.scalars(select(InventoryLocation).where(InventoryLocation.organization_id == _org(principal))))


def list_items(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(session.scalars(select(InventoryItem).where(InventoryItem.organization_id == _org(principal))))


def _lock_balance(session, organization_id, location_id, item_id, lot_id) -> InventoryBalance | None:
    return session.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.organization_id == organization_id,
            InventoryBalance.inventory_location_id == location_id,
            InventoryBalance.inventory_item_id == item_id,
            InventoryBalance.inventory_lot_id == lot_id,
        )
        .with_for_update()
    )


def _ensure_balance(session, lot: InventoryLot) -> InventoryBalance:
    row = _lock_balance(
        session, lot.organization_id, lot.inventory_location_id, lot.inventory_item_id, lot.id
    )
    if row is not None:
        return row
    row = InventoryBalance(
        organization_id=lot.organization_id,
        establishment_id=lot.establishment_id,
        inventory_location_id=lot.inventory_location_id,
        inventory_item_id=lot.inventory_item_id,
        inventory_lot_id=lot.id,
        unit_code=lot.unit_code,
        physical_quantity=ZERO,
        reserved_quantity=ZERO,
    )
    session.add(row)
    session.flush()
    return _lock_balance(
        session, lot.organization_id, lot.inventory_location_id, lot.inventory_item_id, lot.id
    )


def available_of(balance: InventoryBalance) -> Decimal:
    return Decimal(balance.physical_quantity) - Decimal(balance.reserved_quantity)


def _location_locked(session, organization_id, location_id) -> bool:
    open_count = session.scalar(
        select(func.count())
        .select_from(InventoryCountSession)
        .where(
            InventoryCountSession.organization_id == organization_id,
            InventoryCountSession.inventory_location_id == location_id,
            InventoryCountSession.lock_location.is_(True),
            InventoryCountSession.status.in_(("scoped", "counting", "review", "approved")),
        )
    )
    return bool(open_count)


def _assert_lot_usable(session, principal, lot: InventoryLot, *, override: bool):
    today = date.today()
    expired = lot.expires_on is not None and lot.expires_on < today
    blocked = lot.status in BLOCKED_LOT_STATUSES or expired
    if blocked and not override:
        raise ValidationError("lote_indisponivel")
    if blocked and override:
        require_permission(principal, PERMISSION_INVENTORY_EXPIRED_OVERRIDE)


def open_balance(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_ADJUST)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.opening", body)
    if replay is not None:
        return _get(session, InventoryLot, org, replay.resource_id)
    item = _get(session, InventoryItem, org, body["inventory_item_id"])
    location = _get(session, InventoryLocation, org, body["inventory_location_id"])
    qty = _qty(body["quantity"])
    lot = InventoryLot(
        organization_id=org,
        establishment_id=location.establishment_id,
        inventory_item_id=item.id,
        inventory_location_id=location.id,
        internal_lot_code=_next_code(session, org, "LOT"),
        supplier_lot_code=body.get("supplier_lot_code"),
        manufactured_on=date.fromisoformat(body["manufactured_on"]) if body.get("manufactured_on") else None,
        expires_on=date.fromisoformat(body["expires_on"]) if body.get("expires_on") else None,
        unit_code=item.unit_code,
        received_quantity=qty,
        content_hash="",
        created_by_user_id=principal.user_id,
    )
    lot.content_hash = _hash_lot({"opening": True, "item": str(item.id), "qty": str(qty)})
    session.add(lot)
    session.flush()
    _post_movement(
        session,
        principal,
        {
            "movement_type": "opening",
            "inventory_item_id": str(item.id),
            "inventory_lot_id": str(lot.id),
            "to_location_id": str(location.id),
            "quantity": format(qty, "f"),
            "unit_code": item.unit_code,
            "origin_type": "opening",
            "origin_id": str(lot.id),
            "reason": body.get("reason") or "saldo_inicial",
            "approved": True,
        },
        idempotency_key=None,
        command="inventory.opening.inner",
        extra_permission=PERMISSION_INVENTORY_ADJUST,
    )
    _store_command(
        session, org, idempotency_key, "inventory.opening", body, "inventory_lot", lot.id, principal.user_id
    )
    return lot


def post_movement(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_MOVE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.movement.post", body)
    if replay is not None:
        return _get(session, InventoryMovement, org, replay.resource_id)
    return _post_movement(session, principal, body, idempotency_key=idempotency_key, command="inventory.movement.post")


def _post_movement(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
    command: str,
    extra_permission: str | None = None,
):
    if extra_permission:
        require_permission(principal, extra_permission)
    org = _org(principal)
    movement_type = body["movement_type"]
    if movement_type not in PHYSICAL_IN | PHYSICAL_OUT | {"reverse"}:
        raise ValidationError("contrato_invalido")
    item = _get(session, InventoryItem, org, body["inventory_item_id"])
    policy = published_policy(session, org)
    lot = None
    if body.get("inventory_lot_id"):
        lot = _get(session, InventoryLot, org, body["inventory_lot_id"])
    elif item.lot_control == "required" or policy.lot_mode == "required":
        raise ValidationError("lote_obrigatorio")
    if lot is None:
        raise ValidationError("lote_obrigatorio")
    location_id = body.get("to_location_id") if movement_type in PHYSICAL_IN else body.get("from_location_id")
    if (
        location_id
        and _location_locked(session, org, location_id)
        and body.get("origin_type") != "inventory_count_session"
    ):
        raise InvalidStateError("inventario_fechado")
    quantity = _qty(body["quantity"])
    if quantity <= ZERO:
        raise ValidationError("contrato_invalido")
    canonical, factor, _unit = _convert(session, quantity, body.get("unit_code") or item.unit_code)
    if movement_type in PHYSICAL_OUT:
        _assert_lot_usable(session, principal, lot, override=bool(body.get("expired_override")))
    if movement_type == "adjust_plus" or movement_type == "adjust_minus":
        require_permission(principal, PERMISSION_INVENTORY_ADJUST)
        if policy.adjust_requires_approval and not body.get("approved"):
            raise PermissionDeniedError("nao_autorizado")
        if not body.get("reason"):
            raise ValidationError("contrato_invalido")
    balance = _ensure_balance(session, lot)
    sign = 1 if movement_type in PHYSICAL_IN else -1
    next_physical = Decimal(balance.physical_quantity) + (canonical * Decimal(sign))
    if next_physical < ZERO and not policy.allow_negative_balance:
        raise ValidationError("saldo_insuficiente")
    if sign < 0 and available_of(balance) < canonical and not policy.allow_negative_balance:
        raise ValidationError("saldo_insuficiente")
    balance.physical_quantity = next_physical
    if next_physical <= ZERO and lot.status == "available":
        lot.status = "exhausted"
    elif next_physical > ZERO and lot.status == "exhausted":
        lot.status = "available"
    balance.row_version = int(balance.row_version or 1) + 1
    movement = InventoryMovement(
        organization_id=org,
        inventory_item_id=item.id,
        inventory_lot_id=lot.id,
        from_location_id=body.get("from_location_id"),
        to_location_id=body.get("to_location_id"),
        movement_type=movement_type,
        quantity=quantity,
        unit_code=body.get("unit_code") or item.unit_code,
        canonical_quantity=canonical,
        conversion_factor=factor,
        sign=sign,
        nature="physical_in" if sign > 0 else "physical_out",
        origin_type=body.get("origin_type") or "manual",
        origin_id=body.get("origin_id"),
        production_order_id=body.get("production_order_id"),
        production_batch_id=body.get("production_batch_id"),
        production_material_consumption_id=body.get("production_material_consumption_id"),
        procurement_receipt_id=body.get("procurement_receipt_id"),
        inventory_count_session_id=body.get("inventory_count_session_id"),
        inventory_policy_version_id=policy.id,
        actor_user_id=principal.user_id,
        effective_at=_parse_time(body["effective_at"]) if body.get("effective_at") else _now(),
        reason=body.get("reason"),
        correlation_id=body.get("correlation_id"),
        causation_id=body.get("causation_id"),
        reverses_id=body.get("reverses_id"),
        content_hash="",
    )
    movement.content_hash = _digest(
        {
            "item": str(item.id),
            "lot": str(lot.id),
            "qty": str(canonical),
            "type": movement_type,
            "origin": str(body.get("origin_id") or ""),
        }
    )
    session.add(movement)
    session.flush()
    _store_command(session, org, idempotency_key, command, body, "inventory_movement", movement.id, principal.user_id)
    return movement


def set_lot_status(session, principal, lot_id, status, reason, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_LOT_MANAGE)
    org = _org(principal)
    payload = {"lot_id": str(lot_id), "status": status, "reason": reason}
    replay = _replay(session, org, idempotency_key, "inventory.lot.status", payload)
    if replay is not None:
        return _get(session, InventoryLot, org, replay.resource_id)
    lot = _get(session, InventoryLot, org, lot_id)
    _match(lot, expected_version)
    if status not in ("available", "quarantined", "blocked", "expired", "exhausted", "closed"):
        raise ValidationError("contrato_invalido")
    lot.status = status
    lot.block_reason = reason
    lot.blocked_by_user_id = principal.user_id
    lot.blocked_at = _now()
    lot.row_version = int(lot.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.lot.status", payload, "inventory_lot", lot.id, principal.user_id
    )
    return lot


def list_lots(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(session.scalars(select(InventoryLot).where(InventoryLot.organization_id == _org(principal))))


def list_balances(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(session.scalars(select(InventoryBalance).where(InventoryBalance.organization_id == _org(principal))))


def list_movements(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(
        session.scalars(
            select(InventoryMovement)
            .where(InventoryMovement.organization_id == _org(principal))
            .order_by(InventoryMovement.created_at.desc())
        )
    )


def suggest_fefo(session: Session, principal: Principal, item_id, quantity) -> list[dict]:
    require_permission(principal, PERMISSION_INVENTORY_READ)
    org = _org(principal)
    needed = _qty(quantity)
    lots = list(
        session.scalars(
            select(InventoryLot)
            .where(
                InventoryLot.organization_id == org,
                InventoryLot.inventory_item_id == item_id,
                InventoryLot.status == "available",
            )
            .order_by(InventoryLot.expires_on.nulls_last(), InventoryLot.created_at)
        )
    )
    suggestions = []
    remaining = needed
    today = date.today()
    for lot in lots:
        if lot.expires_on is not None and lot.expires_on < today:
            continue
        balance = _lock_balance(session, org, lot.inventory_location_id, item_id, lot.id)
        if balance is None:
            continue
        free = available_of(balance)
        if free <= ZERO:
            continue
        take = free if free <= remaining else remaining
        suggestions.append(
            {
                "inventory_lot_id": str(lot.id),
                "inventory_location_id": str(lot.inventory_location_id),
                "quantity": format(take, "f"),
                "expires_on": lot.expires_on.isoformat() if lot.expires_on else None,
                "algorithm": "fefo_suggest",
            }
        )
        remaining -= take
        if remaining <= ZERO:
            break
    return suggestions


def reserve_order(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_RESERVE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.reserve", body)
    if replay is not None:
        return _get(session, InventoryReservation, org, replay.resource_id)
    order = _get(session, ProductionOrder, org, body["production_order_id"])
    policy = published_policy(session, org)
    first_policy = session.scalar(
        select(InventoryPolicy)
        .where(InventoryPolicy.organization_id == org)
        .order_by(InventoryPolicy.created_at.asc())
    )
    historical = first_policy is not None and order.created_at <= first_policy.created_at
    if historical and not body.get("adopt_historical"):
        raise ValidationError("adocao_historica")
    if historical and not body.get("reason"):
        raise ValidationError("contrato_invalido")
    item = _get(session, InventoryItem, org, body["inventory_item_id"])
    required = _qty(body["required_quantity"])
    allocations = body.get("allocations") or suggest_fefo(session, principal, item.id, required)
    reserved = ZERO
    reservation = InventoryReservation(
        organization_id=org,
        production_order_id=order.id,
        production_batch_id=body.get("production_batch_id"),
        inventory_item_id=item.id,
        required_quantity=required,
        reserved_quantity=ZERO,
        unit_code=item.unit_code,
        status="pending",
        adopted=bool(historical and body.get("adopt_historical")),
        reason=body.get("reason"),
        inventory_policy_version_id=policy.id,
        created_by_user_id=principal.user_id,
    )
    session.add(reservation)
    session.flush()
    for alloc in allocations:
        lot = _get(session, InventoryLot, org, alloc["inventory_lot_id"])
        qty = _qty(alloc["quantity"])
        _assert_lot_usable(session, principal, lot, override=False)
        balance = _ensure_balance(session, lot)
        if available_of(balance) < qty and not policy.allow_negative_balance:
            continue
        take = qty if available_of(balance) >= qty else available_of(balance)
        if take <= ZERO:
            continue
        balance.reserved_quantity = Decimal(balance.reserved_quantity) + take
        balance.row_version = int(balance.row_version or 1) + 1
        session.add(
            InventoryReservationAllocation(
                organization_id=org,
                inventory_reservation_id=reservation.id,
                inventory_lot_id=lot.id,
                inventory_location_id=lot.inventory_location_id,
                quantity=take,
            )
        )
        reserved += take
    reservation.reserved_quantity = reserved
    reservation.shortage_quantity = required - reserved if reserved < required else ZERO
    if reserved <= ZERO:
        reservation.status = "pending"
    elif reserved < required:
        reservation.status = "partial"
    else:
        reservation.status = "reserved"
    _store_command(
        session, org, idempotency_key, "inventory.reserve", body, "inventory_reservation", reservation.id, principal.user_id
    )
    return reservation


def release_reservation(session, principal, reservation_id, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_RESERVE)
    org = _org(principal)
    payload = {"reservation_id": str(reservation_id)}
    replay = _replay(session, org, idempotency_key, "inventory.reserve.release", payload)
    if replay is not None:
        return _get(session, InventoryReservation, org, replay.resource_id)
    row = _get(session, InventoryReservation, org, reservation_id)
    _match(row, expected_version)
    if row.status in {"released", "cancelled", "consumed"}:
        raise InvalidStateError("transicao_invalida")
    allocs = list(
        session.scalars(
            select(InventoryReservationAllocation).where(
                InventoryReservationAllocation.inventory_reservation_id == row.id
            )
        )
    )
    for alloc in allocs:
        lot = _get(session, InventoryLot, org, alloc.inventory_lot_id)
        balance = _ensure_balance(session, lot)
        balance.reserved_quantity = Decimal(balance.reserved_quantity) - Decimal(alloc.quantity)
        if balance.reserved_quantity < ZERO:
            balance.reserved_quantity = ZERO
        balance.row_version = int(balance.row_version or 1) + 1
    row.status = "released"
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.reserve.release", payload, "inventory_reservation", row.id, principal.user_id
    )
    return row


def cancel_order_reservations(session, principal, order_id, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_RESERVE)
    org = _org(principal)
    payload = {"production_order_id": str(order_id)}
    replay = _replay(session, org, idempotency_key, "inventory.reserve.cancel_order", payload)
    if replay is not None:
        return _get(session, InventoryReservation, org, replay.resource_id)
    policy = published_policy(session, org)
    if policy.cancelled_order_treatment != "release_reservation":
        raise InvalidStateError("transicao_invalida")
    rows = list(
        session.scalars(
            select(InventoryReservation).where(
                InventoryReservation.organization_id == org,
                InventoryReservation.production_order_id == order_id,
                InventoryReservation.status.in_(("pending", "partial", "reserved")),
            )
        )
    )
    last = None
    for row in rows:
        last = release_reservation(
            session, principal, row.id, expected_version=row.row_version, idempotency_key=None
        )
        last.status = "cancelled"
    if last is None:
        raise ValidationError("recurso_nao_encontrado")
    _store_command(
        session, org, idempotency_key, "inventory.reserve.cancel_order", payload, "inventory_reservation", last.id, principal.user_id
    )
    return last


def confirm_pick(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_SEPARATE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.pick.confirm", body)
    if replay is not None:
        return _get(session, InventoryPick, org, replay.resource_id)
    order = _get(session, ProductionOrder, org, body["production_order_id"])
    policy = published_policy(session, org)
    pick = InventoryPick(
        organization_id=org,
        public_code=_next_code(session, org, "PICK"),
        production_order_id=order.id,
        production_batch_id=body.get("production_batch_id"),
        status="confirmed",
        inventory_policy_version_id=policy.id,
        created_by_user_id=principal.user_id,
    )
    session.add(pick)
    session.flush()
    for line in body.get("lines") or []:
        lot = _get(session, InventoryLot, org, line["inventory_lot_id"])
        _assert_lot_usable(session, principal, lot, override=bool(line.get("expired_override")))
        session.add(
            InventoryPickLine(
                organization_id=org,
                inventory_pick_id=pick.id,
                inventory_item_id=line["inventory_item_id"],
                inventory_lot_id=lot.id,
                inventory_location_id=lot.inventory_location_id,
                quantity=_qty(line["quantity"]),
                suggested=bool(line.get("suggested")),
                substituted=bool(line.get("substituted")),
                reason=line.get("reason"),
            )
        )
    session.flush()
    _store_command(
        session, org, idempotency_key, "inventory.pick.confirm", body, "inventory_pick", pick.id, principal.user_id
    )
    return pick


def post_consumption(session: Session, principal: Principal, consumption_id, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_MOVE)
    org = _org(principal)
    payload = {"consumption_id": str(consumption_id), **body}
    replay = _replay(session, org, idempotency_key, "inventory.consumption.post", payload)
    if replay is not None:
        return _get(session, InventoryConsumptionPosting, org, replay.resource_id)
    existing = session.scalar(
        select(InventoryConsumptionPosting).where(
            InventoryConsumptionPosting.organization_id == org,
            InventoryConsumptionPosting.production_material_consumption_id == consumption_id,
        )
    )
    if existing is not None and existing.status == "posted":
        return existing
    consumption = session.get(ProductionMaterialConsumption, consumption_id)
    if consumption is None or consumption.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    item = session.scalar(
        select(InventoryItem).where(
            InventoryItem.organization_id == org,
            InventoryItem.ingredient_id == body["ingredient_id"],
        )
    )
    if item is None:
        posting = InventoryConsumptionPosting(
            organization_id=org,
            production_material_consumption_id=consumption.id,
            status="pending",
            last_error="item_estocavel_ausente",
            created_by_user_id=principal.user_id,
        )
        session.add(posting)
        session.flush()
        _store_command(
            session,
            org,
            idempotency_key,
            "inventory.consumption.post",
            payload,
            "inventory_consumption_posting",
            posting.id,
            principal.user_id,
        )
        return posting
    kind_map = {
        "consume": "production_consume",
        "return": "production_return",
        "waste": "waste",
        "correction": "adjust_minus" if Decimal(consumption.canonical_quantity) > ZERO else "adjust_plus",
    }
    movement_type = kind_map.get(consumption.consumption_type)
    if movement_type is None:
        raise ValidationError("contrato_invalido")
    try:
        movement = _post_movement(
            session,
            principal,
            {
                "movement_type": movement_type,
                "inventory_item_id": str(item.id),
                "inventory_lot_id": body.get("inventory_lot_id"),
                "from_location_id": body.get("from_location_id"),
                "to_location_id": body.get("to_location_id"),
                "quantity": format(consumption.canonical_quantity, "f"),
                "unit_code": consumption.canonical_unit_code,
                "origin_type": "production_material_consumption",
                "origin_id": str(consumption.id),
                "production_order_id": str(consumption.production_order_id),
                "production_batch_id": str(consumption.production_batch_id),
                "production_material_consumption_id": str(consumption.id),
                "expired_override": body.get("expired_override"),
                "reason": consumption.reason or consumption.consumption_type,
            },
            idempotency_key=None,
            command="inventory.consumption.inner",
        )
        posting = existing or InventoryConsumptionPosting(
            organization_id=org,
            production_material_consumption_id=consumption.id,
            created_by_user_id=principal.user_id,
            status="posted",
        )
        posting.status = "posted"
        posting.inventory_movement_id = movement.id
        posting.last_error = None
        session.add(posting)
        if consumption.consumption_type == "consume":
            _consume_reservation(session, org, consumption.production_order_id, item.id, consumption.canonical_quantity)
    except ValidationError as exc:
        posting = existing or InventoryConsumptionPosting(
            organization_id=org,
            production_material_consumption_id=consumption.id,
            created_by_user_id=principal.user_id,
            status="failed",
        )
        posting.status = "failed"
        posting.last_error = exc.reason
        session.add(posting)
        session.flush()
    session.flush()
    _store_command(
        session,
        org,
        idempotency_key,
        "inventory.consumption.post",
        payload,
        "inventory_consumption_posting",
        posting.id,
        principal.user_id,
    )
    return posting


def _consume_reservation(session, organization_id, order_id, item_id, quantity: Decimal) -> None:
    rows = list(
        session.scalars(
            select(InventoryReservation).where(
                InventoryReservation.organization_id == organization_id,
                InventoryReservation.production_order_id == order_id,
                InventoryReservation.inventory_item_id == item_id,
                InventoryReservation.status.in_(("partial", "reserved")),
            )
        )
    )
    remaining = quantity
    for row in rows:
        allocs = list(
            session.scalars(
                select(InventoryReservationAllocation).where(
                    InventoryReservationAllocation.inventory_reservation_id == row.id
                )
            )
        )
        for alloc in allocs:
            if remaining <= ZERO:
                break
            take = Decimal(alloc.quantity) if Decimal(alloc.quantity) <= remaining else remaining
            lot = _get(session, InventoryLot, organization_id, alloc.inventory_lot_id)
            balance = _ensure_balance(session, lot)
            balance.reserved_quantity = Decimal(balance.reserved_quantity) - take
            if balance.reserved_quantity < ZERO:
                balance.reserved_quantity = ZERO
            remaining -= take
        row.reserved_quantity = max(ZERO, Decimal(row.reserved_quantity) - (quantity - remaining))
        if row.reserved_quantity <= ZERO:
            row.status = "consumed"


def create_count(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_COUNT)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.count.create", body)
    if replay is not None:
        return _get(session, InventoryCountSession, org, replay.resource_id)
    location = _get(session, InventoryLocation, org, body["inventory_location_id"])
    policy = published_policy(session, org)
    row = InventoryCountSession(
        organization_id=org,
        public_code=_next_code(session, org, "CNT"),
        inventory_location_id=location.id,
        cutoff_at=_parse_time(body["cutoff_at"]),
        require_second_count=bool(body.get("require_second_count")),
        lock_location=policy.lock_location_on_count,
        inventory_policy_version_id=policy.id,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "inventory.count.create", body, "inventory_count_session", row.id, principal.user_id
    )
    return row


def freeze_count_scope(session, principal, session_id, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_COUNT)
    org = _org(principal)
    payload = {"session_id": str(session_id)}
    replay = _replay(session, org, idempotency_key, "inventory.count.scope", payload)
    if replay is not None:
        return _get(session, InventoryCountSession, org, replay.resource_id)
    row = _get(session, InventoryCountSession, org, session_id)
    _match(row, expected_version)
    if row.status != "draft":
        raise InvalidStateError("transicao_invalida")
    balances = list(
        session.scalars(
            select(InventoryBalance).where(
                InventoryBalance.organization_id == org,
                InventoryBalance.inventory_location_id == row.inventory_location_id,
            )
        )
    )
    for balance in balances:
        session.add(
            InventoryCountScope(
                organization_id=org,
                inventory_count_session_id=row.id,
                inventory_item_id=balance.inventory_item_id,
                inventory_lot_id=balance.inventory_lot_id,
                expected_quantity=balance.physical_quantity,
            )
        )
    row.status = "scoped"
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.count.scope", payload, "inventory_count_session", row.id, principal.user_id
    )
    return row


def record_count(session, principal, session_id, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_COUNT)
    org = _org(principal)
    payload = {"session_id": str(session_id), **body}
    replay = _replay(session, org, idempotency_key, "inventory.count.entry", payload)
    if replay is not None:
        return _get(session, InventoryCountSession, org, replay.resource_id)
    row = _get(session, InventoryCountSession, org, session_id)
    if row.status not in {"scoped", "counting"}:
        raise InvalidStateError("transicao_invalida")
    scope = _get(session, InventoryCountScope, org, body["inventory_count_scope_id"])
    pass_number = int(body["pass_number"])
    if pass_number not in (1, 2):
        raise ValidationError("contrato_invalido")
    session.add(
        InventoryCountEntry(
            organization_id=org,
            inventory_count_session_id=row.id,
            inventory_count_scope_id=scope.id,
            pass_number=pass_number,
            quantity=_qty(body["quantity"]),
            actor_user_id=principal.user_id,
        )
    )
    row.status = "counting"
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.count.entry", payload, "inventory_count_session", row.id, principal.user_id
    )
    return row


def review_count(session, principal, session_id, body: dict, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_COUNT)
    org = _org(principal)
    payload = {"session_id": str(session_id), **body}
    replay = _replay(session, org, idempotency_key, "inventory.count.review", payload)
    if replay is not None:
        return _get(session, InventoryCountSession, org, replay.resource_id)
    row = _get(session, InventoryCountSession, org, session_id)
    _match(row, expected_version)
    session.add(
        InventoryCountReview(
            organization_id=org,
            inventory_count_session_id=row.id,
            decision=body["decision"],
            reason=body.get("reason"),
            actor_user_id=principal.user_id,
        )
    )
    row.status = "review"
    row.row_version = int(row.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "inventory.count.review", payload, "inventory_count_session", row.id, principal.user_id
    )
    return row


def approve_count(session, principal, session_id, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_INVENTORY_COUNT_APPROVE)
    org = _org(principal)
    payload = {"session_id": str(session_id)}
    replay = _replay(session, org, idempotency_key, "inventory.count.approve", payload)
    if replay is not None:
        return _get(session, InventoryCountSession, org, replay.resource_id)
    row = _get(session, InventoryCountSession, org, session_id)
    _match(row, expected_version)
    if row.status not in {"review", "counting"}:
        raise InvalidStateError("transicao_invalida")
    scopes = list(
        session.scalars(
            select(InventoryCountScope).where(InventoryCountScope.inventory_count_session_id == row.id)
        )
    )
    for scope in scopes:
        counted = _latest_count(session, scope.id, 2 if row.require_second_count else 1)
        if counted is None:
            continue
        delta = Decimal(counted) - Decimal(scope.expected_quantity)
        if delta == ZERO:
            continue
        movement_type = "adjust_plus" if delta > ZERO else "adjust_minus"
        _post_movement(
            session,
            principal,
            {
                "movement_type": movement_type,
                "inventory_item_id": str(scope.inventory_item_id),
                "inventory_lot_id": str(scope.inventory_lot_id),
                "from_location_id": None if delta > ZERO else str(row.inventory_location_id),
                "to_location_id": str(row.inventory_location_id) if delta > ZERO else None,
                "quantity": format(abs(delta), "f"),
                "origin_type": "inventory_count_session",
                "origin_id": str(row.id),
                "inventory_count_session_id": str(row.id),
                "reason": "ajuste_inventario",
                "approved": True,
            },
            idempotency_key=None,
            command="inventory.count.adjust",
            extra_permission=PERMISSION_INVENTORY_ADJUST,
        )
    row.status = "closed"
    row.row_version = int(row.row_version or 1) + 1
    session.add(
        InventoryCountReview(
            organization_id=org,
            inventory_count_session_id=row.id,
            decision="approved",
            actor_user_id=principal.user_id,
        )
    )
    _store_command(
        session, org, idempotency_key, "inventory.count.approve", payload, "inventory_count_session", row.id, principal.user_id
    )
    return row


def _latest_count(session, scope_id, pass_number) -> Decimal | None:
    row = session.scalar(
        select(InventoryCountEntry)
        .where(
            InventoryCountEntry.inventory_count_scope_id == scope_id,
            InventoryCountEntry.pass_number == pass_number,
        )
        .order_by(InventoryCountEntry.created_at.desc())
    )
    if row is None and pass_number == 2:
        return _latest_count(session, scope_id, 1)
    return None if row is None else Decimal(row.quantity)


def reopen_count(session, principal, session_id):
    raise ImmutableError("inventario_fechado")


def suggest_replenishment(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "inventory.replenish.suggest", body)
    if replay is not None:
        return _get(session, InventoryReplenishmentSuggestion, org, replay.resource_id)
    policy = published_policy(session, org)
    horizon = int(body.get("horizon_days") or 7)
    suggestion = InventoryReplenishmentSuggestion(
        organization_id=org,
        public_code=_next_code(session, org, "RPL"),
        horizon_days=horizon,
        generated_at=_now(),
        inventory_policy_version_id=policy.id,
        created_by_user_id=principal.user_id,
    )
    session.add(suggestion)
    session.flush()
    items = list(session.scalars(select(InventoryItem).where(InventoryItem.organization_id == org)))
    for item in items:
        physical = session.scalar(
            select(func.coalesce(func.sum(InventoryBalance.physical_quantity), 0)).where(
                InventoryBalance.organization_id == org,
                InventoryBalance.inventory_item_id == item.id,
            )
        )
        reserved = session.scalar(
            select(func.coalesce(func.sum(InventoryBalance.reserved_quantity), 0)).where(
                InventoryBalance.organization_id == org,
                InventoryBalance.inventory_item_id == item.id,
            )
        )
        physical = Decimal(physical)
        reserved = Decimal(reserved)
        available = physical - reserved
        in_transit = _in_transit(session, org, item.id)
        demand = _planned_demand(session, org, item.id)
        gaps = []
        if item.reorder_point is None:
            gaps.append("ponto_reposicao_ausente")
        if demand is None:
            gaps.append("demanda_planejada_ausente")
        package = None
        if item.preferred_supplier_item_id:
            offer = session.get(SupplierItem, item.preferred_supplier_item_id)
            package = None if offer is None else Decimal(offer.package_quantity)
        else:
            gaps.append("embalagem_ausente")
        safety = item.safety_stock or ZERO
        target = item.target_quantity
        reorder = item.reorder_point
        suggested = ZERO
        if reorder is not None and available + in_transit <= Decimal(reorder):
            baseline = Decimal(target) if target is not None else Decimal(reorder) + safety
            raw = baseline - available - in_transit
            if raw < ZERO:
                raw = ZERO
            if package and package > ZERO:
                multiples = (raw / package).to_integral_value(rounding=ROUND_CEILING)
                suggested = multiples * package
            else:
                suggested = raw
        session.add(
            InventoryReplenishmentItem(
                organization_id=org,
                inventory_replenishment_suggestion_id=suggestion.id,
                inventory_item_id=item.id,
                physical_quantity=physical,
                reserved_quantity=reserved,
                available_quantity=available,
                in_transit_quantity=in_transit,
                planned_demand=demand,
                suggested_quantity=suggested,
                formula={
                    "algorithm": ALGORITHM_NAME,
                    "version": ALGORITHM_VERSION,
                    "horizon_days": horizon,
                    "available_plus_transit": format(available + in_transit, "f"),
                    "reorder_point": None if reorder is None else format(Decimal(reorder), "f"),
                    "target": None if target is None else format(Decimal(target), "f"),
                    "package": None if package is None else format(package, "f"),
                    "automatic_purchase": False,
                },
                gaps=gaps,
            )
        )
    _store_command(
        session,
        org,
        idempotency_key,
        "inventory.replenish.suggest",
        body,
        "inventory_replenishment_suggestion",
        suggestion.id,
        principal.user_id,
    )
    return suggestion


def _in_transit(session, organization_id, item_id) -> Decimal:
    orders = list(
        session.scalars(
            select(ProcurementOrder).where(
                ProcurementOrder.organization_id == organization_id,
                ProcurementOrder.status.in_(("issued", "partially_received")),
            )
        )
    )
    total = ZERO
    for order in orders:
        items = list(
            session.scalars(
                select(ProcurementOrderItem).where(
                    ProcurementOrderItem.procurement_order_id == order.id,
                    ProcurementOrderItem.procurement_order_revision_id.in_(
                        select(ProcurementOrderRevision.id).where(
                            ProcurementOrderRevision.procurement_order_id == order.id,
                            ProcurementOrderRevision.revision_number == order.current_revision,
                        )
                    ),
                    ProcurementOrderItem.inventory_item_id == item_id,
                )
            )
        )
        ordered = sum((Decimal(item.quantity) for item in items), ZERO)
        received = session.scalar(
            select(func.coalesce(func.sum(ProcurementReceiptItem.quantity), 0)).where(
                ProcurementReceiptItem.organization_id == organization_id,
                ProcurementReceiptItem.inventory_item_id == item_id,
                ProcurementReceiptItem.procurement_receipt_id.in_(
                    select(ProcurementReceipt.id).where(
                        ProcurementReceipt.procurement_order_id == order.id,
                        ProcurementReceipt.status == "posted",
                    )
                ),
            )
        )
        pending = ordered - Decimal(received)
        if pending > ZERO:
            total += pending
    return total


def _planned_demand(session, organization_id, item_id) -> Decimal | None:
    from app.modules.ingredient_catalog.models import IngredientVersion

    item = session.get(InventoryItem, item_id)
    versions = list(
        session.scalars(select(IngredientVersion.id).where(IngredientVersion.ingredient_id == item.ingredient_id))
    )
    if not versions:
        return None
    rows = list(
        session.scalars(
            select(ProductionOrderMaterial)
            .join(ProductionOrder)
            .where(
                ProductionOrder.organization_id == organization_id,
                ProductionOrder.status.in_(("released", "in_weighing", "ready", "in_progress")),
                ProductionOrderMaterial.ingredient_version_id.in_(versions),
            )
        )
    )
    if not rows:
        return None
    return sum((Decimal(row.net_quantity) for row in rows), ZERO)


def create_requisition(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_REQUISITION_CREATE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "procurement.requisition.create", body)
    if replay is not None:
        return _get(session, ProcurementRequisition, org, replay.resource_id)
    row = ProcurementRequisition(
        organization_id=org,
        public_code=_next_code(session, org, "REQ"),
        establishment_id=body["establishment_id"],
        inventory_location_id=body.get("inventory_location_id"),
        needed_by=date.fromisoformat(body["needed_by"]) if body.get("needed_by") else None,
        justification=body["justification"],
        origin_type=body.get("origin_type") or "manual",
        origin_id=body.get("origin_id"),
        status="draft",
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    for item in body.get("items") or []:
        session.add(
            ProcurementRequisitionItem(
                organization_id=org,
                procurement_requisition_id=row.id,
                inventory_item_id=item["inventory_item_id"],
                quantity=_qty(item["quantity"]),
                unit_code=item["unit_code"],
            )
        )
    _store_command(
        session, org, idempotency_key, "procurement.requisition.create", body, "procurement_requisition", row.id, principal.user_id
    )
    return row


def transition_requisition(session, principal, requisition_id, status, *, expected_version, idempotency_key):
    permission = (
        PERMISSION_PROCUREMENT_REQUISITION_APPROVE
        if status in {"approved", "rejected"}
        else PERMISSION_PROCUREMENT_REQUISITION_CREATE
    )
    require_permission(principal, permission)
    org = _org(principal)
    payload = {"requisition_id": str(requisition_id), "status": status}
    replay = _replay(session, org, idempotency_key, "procurement.requisition.transition", payload)
    if replay is not None:
        return _get(session, ProcurementRequisition, org, replay.resource_id)
    row = _get(session, ProcurementRequisition, org, requisition_id)
    _match(row, expected_version)
    allowed = {
        "draft": {"submitted", "cancelled"},
        "submitted": {"approved", "rejected", "cancelled"},
        "approved": {"converted", "cancelled"},
    }
    if status not in allowed.get(row.status or "draft", set()):
        raise InvalidStateError("transicao_invalida")
    row.status = status
    row.row_version = int(row.row_version or 1) + 1
    session.flush()
    _store_command(
        session,
        org,
        idempotency_key,
        "procurement.requisition.transition",
        payload,
        "procurement_requisition",
        row.id,
        principal.user_id,
    )
    return row


def create_quotation(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_QUOTATION_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "procurement.quotation.create", body)
    if replay is not None:
        return _get(session, ProcurementQuotation, org, replay.resource_id)
    if (body.get("currency") or CURRENCY) != CURRENCY:
        raise ValidationError("contrato_invalido")
    row = ProcurementQuotation(
        organization_id=org,
        supplier_id=body["supplier_id"],
        valid_until=date.fromisoformat(body["valid_until"]) if body.get("valid_until") else None,
        lead_time_days=body.get("lead_time_days"),
        conditions=body.get("conditions"),
        evidence_ref=body.get("evidence_ref"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    for item in body.get("items") or []:
        session.add(
            ProcurementQuotationItem(
                organization_id=org,
                procurement_quotation_id=row.id,
                inventory_item_id=item["inventory_item_id"],
                supplier_item_id=item.get("supplier_item_id"),
                quantity=_qty(item["quantity"]),
                package_quantity=_qty(item["package_quantity"]) if item.get("package_quantity") else None,
                unit_code=item["unit_code"],
                unit_price=_qty(item["unit_price"]),
            )
        )
    _store_command(
        session, org, idempotency_key, "procurement.quotation.create", body, "procurement_quotation", row.id, principal.user_id
    )
    return row


def compare_quotations(session: Session, principal: Principal, item_id) -> list[dict]:
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    org = _org(principal)
    rows = list(
        session.scalars(
            select(ProcurementQuotationItem).where(
                ProcurementQuotationItem.organization_id == org,
                ProcurementQuotationItem.inventory_item_id == item_id,
            )
        )
    )
    compared = []
    for row in rows:
        quote = session.get(ProcurementQuotation, row.procurement_quotation_id)
        unit = Decimal(row.unit_price)
        supplier = session.get(Supplier, quote.supplier_id) if quote is not None else None
        compared.append(
            {
                "quotation_id": str(row.procurement_quotation_id),
                "supplier_id": str(quote.supplier_id),
                "supplier_name": supplier.display_name if supplier is not None else None,
                "unit_price": format(unit, "f"),
                "lead_time_days": quote.lead_time_days,
                "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
                "chosen": False,
            }
        )
    compared.sort(key=lambda item: (Decimal(item["unit_price"]), item["lead_time_days"] or 10**9))
    return compared


def create_order(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_ORDER_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "procurement.order.create", body)
    if replay is not None:
        return _get(session, ProcurementOrder, org, replay.resource_id)
    if (body.get("currency") or CURRENCY) != CURRENCY:
        raise ValidationError("contrato_invalido")
    order = ProcurementOrder(
        organization_id=org,
        public_code=_next_code(session, org, "PO"),
        establishment_id=body["establishment_id"],
        supplier_id=body["supplier_id"],
        inventory_location_id=body["inventory_location_id"],
        expected_at=date.fromisoformat(body["expected_at"]) if body.get("expected_at") else None,
        status="draft",
        created_by_user_id=principal.user_id,
    )
    session.add(order)
    session.flush()
    revision = ProcurementOrderRevision(
        organization_id=org,
        procurement_order_id=order.id,
        revision_number=1,
        created_by_user_id=principal.user_id,
    )
    session.add(revision)
    session.flush()
    for item in body.get("items") or []:
        session.add(
            ProcurementOrderItem(
                organization_id=org,
                procurement_order_id=order.id,
                procurement_order_revision_id=revision.id,
                inventory_item_id=item["inventory_item_id"],
                supplier_item_id=item.get("supplier_item_id"),
                procurement_requisition_item_id=item.get("procurement_requisition_item_id"),
                procurement_quotation_item_id=item.get("procurement_quotation_item_id"),
                quantity=_qty(item["quantity"]),
                package_quantity=_qty(item["package_quantity"]) if item.get("package_quantity") else None,
                unit_code=item["unit_code"],
                unit_price=_qty(item["unit_price"]),
            )
        )
    _store_command(
        session, org, idempotency_key, "procurement.order.create", body, "procurement_order", order.id, principal.user_id
    )
    return order


def transition_order(session, principal, order_id, status, *, expected_version, idempotency_key):
    permission = (
        PERMISSION_PROCUREMENT_ORDER_APPROVE
        if status in {"approved", "issued"}
        else PERMISSION_PROCUREMENT_ORDER_MANAGE
    )
    require_permission(principal, permission)
    org = _org(principal)
    payload = {"order_id": str(order_id), "status": status}
    replay = _replay(session, org, idempotency_key, "procurement.order.transition", payload)
    if replay is not None:
        return _get(session, ProcurementOrder, org, replay.resource_id)
    row = _get(session, ProcurementOrder, org, order_id)
    _match(row, expected_version)
    allowed = {
        "draft": {"approved", "cancelled"},
        "approved": {"issued", "cancelled"},
        "issued": {"cancelled", "closed"},
        "partially_received": {"received", "closed"},
        "received": {"closed"},
    }
    if status not in allowed.get(row.status or "draft", set()):
        raise InvalidStateError("transicao_invalida")
    row.status = status
    row.row_version = int(row.row_version or 1) + 1
    session.flush()
    _store_command(
        session, org, idempotency_key, "procurement.order.transition", payload, "procurement_order", row.id, principal.user_id
    )
    return row


def revise_order(session, principal, order_id, body: dict, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_ORDER_MANAGE)
    org = _org(principal)
    payload = {"order_id": str(order_id), **body}
    replay = _replay(session, org, idempotency_key, "procurement.order.revise", payload)
    if replay is not None:
        return _get(session, ProcurementOrder, org, replay.resource_id)
    order = _get(session, ProcurementOrder, org, order_id)
    _match(order, expected_version)
    if order.status not in {"issued", "partially_received"}:
        raise InvalidStateError("transicao_invalida")
    revision = ProcurementOrderRevision(
        organization_id=org,
        procurement_order_id=order.id,
        revision_number=int(order.current_revision) + 1,
        reason=body.get("reason"),
        created_by_user_id=principal.user_id,
    )
    session.add(revision)
    session.flush()
    for item in body.get("items") or []:
        session.add(
            ProcurementOrderItem(
                organization_id=org,
                procurement_order_id=order.id,
                procurement_order_revision_id=revision.id,
                inventory_item_id=item["inventory_item_id"],
                supplier_item_id=item.get("supplier_item_id"),
                quantity=_qty(item["quantity"]),
                package_quantity=_qty(item["package_quantity"]) if item.get("package_quantity") else None,
                unit_code=item["unit_code"],
                unit_price=_qty(item["unit_price"]),
            )
        )
    order.current_revision = revision.revision_number
    order.row_version = int(order.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "procurement.order.revise", payload, "procurement_order", order.id, principal.user_id
    )
    return order


def receive_order(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_RECEIVE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "procurement.receive", body)
    if replay is not None:
        return _get(session, ProcurementReceipt, org, replay.resource_id)
    order = _get(session, ProcurementOrder, org, body["procurement_order_id"])
    if order.status not in {"issued", "partially_received"}:
        raise InvalidStateError("transicao_invalida")
    location = _get(session, InventoryLocation, org, body.get("inventory_location_id") or order.inventory_location_id)
    receipt = ProcurementReceipt(
        organization_id=org,
        public_code=_next_code(session, org, "RCP"),
        procurement_order_id=order.id,
        inventory_location_id=location.id,
        evidence_ref=body.get("evidence_ref"),
        created_by_user_id=principal.user_id,
    )
    session.add(receipt)
    session.flush()
    policy = published_policy(session, org)
    for line in body.get("items") or []:
        order_item = _get(session, ProcurementOrderItem, org, line["procurement_order_item_id"])
        item = _get(session, InventoryItem, org, order_item.inventory_item_id)
        qty = _qty(line["quantity"])
        if item.expiry_control and policy.expiry_required and not line.get("expires_on"):
            raise ValidationError("contrato_invalido")
        lot = InventoryLot(
            organization_id=org,
            establishment_id=location.establishment_id,
            inventory_item_id=item.id,
            inventory_location_id=location.id,
            internal_lot_code=_next_code(session, org, "LOT"),
            supplier_lot_code=line.get("supplier_lot_code"),
            supplier_id=order.supplier_id,
            supplier_item_id=order_item.supplier_item_id,
            manufactured_on=date.fromisoformat(line["manufactured_on"]) if line.get("manufactured_on") else None,
            expires_on=date.fromisoformat(line["expires_on"]) if line.get("expires_on") else None,
            procurement_receipt_id=receipt.id,
            unit_code=line.get("unit_code") or item.unit_code,
            received_quantity=qty,
            status="quarantined" if line.get("quarantine") else "available",
            content_hash="",
            created_by_user_id=principal.user_id,
        )
        lot.content_hash = _hash_lot({"item": str(item.id), "qty": str(qty), "receipt": str(receipt.id)})
        session.add(lot)
        session.flush()
        divergence = {}
        if qty != Decimal(order_item.quantity):
            divergence["quantity"] = True
        if line.get("observed_unit_price") and _qty(line["observed_unit_price"]) != Decimal(order_item.unit_price):
            divergence["price"] = True
        receipt_item = ProcurementReceiptItem(
            organization_id=org,
            procurement_receipt_id=receipt.id,
            procurement_order_item_id=order_item.id,
            inventory_item_id=item.id,
            quantity=qty,
            unit_code=lot.unit_code,
            supplier_lot_code=lot.supplier_lot_code,
            manufactured_on=lot.manufactured_on,
            expires_on=lot.expires_on,
            observed_unit_price=_qty(line["observed_unit_price"]) if line.get("observed_unit_price") else None,
            inventory_lot_id=lot.id,
            divergence=divergence,
        )
        session.add(receipt_item)
        _post_movement(
            session,
            principal,
            {
                "movement_type": "receipt",
                "inventory_item_id": str(item.id),
                "inventory_lot_id": str(lot.id),
                "to_location_id": str(location.id),
                "quantity": format(qty, "f"),
                "unit_code": lot.unit_code,
                "origin_type": "procurement_receipt",
                "origin_id": str(receipt.id),
                "procurement_receipt_id": str(receipt.id),
            },
            idempotency_key=None,
            command="procurement.receive.inner",
        )
    receipt.status = "posted"
    received_qty = session.scalar(
        select(func.coalesce(func.sum(ProcurementReceiptItem.quantity), 0)).where(
            ProcurementReceiptItem.procurement_receipt_id.in_(
                select(ProcurementReceipt.id).where(ProcurementReceipt.procurement_order_id == order.id)
            )
        )
    )
    ordered_qty = session.scalar(
        select(func.coalesce(func.sum(ProcurementOrderItem.quantity), 0)).where(
            ProcurementOrderItem.procurement_order_id == order.id,
            ProcurementOrderItem.procurement_order_revision_id.in_(
                select(ProcurementOrderRevision.id).where(
                    ProcurementOrderRevision.procurement_order_id == order.id,
                    ProcurementOrderRevision.revision_number == order.current_revision,
                )
            ),
        )
    )
    order.status = "received" if Decimal(received_qty) >= Decimal(ordered_qty) else "partially_received"
    order.row_version = int(order.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "procurement.receive", body, "procurement_receipt", receipt.id, principal.user_id
    )
    session.add(
        AuditEvent(
            organization_id=org,
            actor_user_id=principal.user_id,
            event_type="procurement.received",
            aggregate_type="procurement_receipt",
            aggregate_id=receipt.id,
            payload={"order_id": str(order.id)},
        )
    )
    return receipt


def record_observed_price(session, principal, receipt_item_id, *, idempotency_key):
    require_permission(principal, PERMISSION_SUPPLIER_PRICE_RECORD)
    org = _org(principal)
    payload = {"receipt_item_id": str(receipt_item_id)}
    replay = _replay(session, org, idempotency_key, "procurement.price.observe", payload)
    if replay is not None:
        return session.get(SupplierItemPrice, replay.resource_id)
    item = _get(session, ProcurementReceiptItem, org, receipt_item_id)
    if item.observed_unit_price is None:
        raise ValidationError("contrato_invalido")
    order_item = session.get(ProcurementOrderItem, item.procurement_order_item_id)
    if order_item is None or order_item.supplier_item_id is None:
        raise ValidationError("recurso_nao_encontrado")
    price = SupplierItemPrice(
        supplier_item_id=order_item.supplier_item_id,
        unit_price=item.observed_unit_price,
        currency=item.currency,
        observed_at=_now(),
        source=f"receipt:{item.procurement_receipt_id}",
    )
    session.add(price)
    session.flush()
    _store_command(
        session, org, idempotency_key, "procurement.price.observe", payload, "supplier_item_price", price.id, principal.user_id
    )
    return price


def return_to_supplier(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PROCUREMENT_RETURN)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "procurement.return", body)
    if replay is not None:
        return _get(session, ProcurementReturn, org, replay.resource_id)
    receipt = _get(session, ProcurementReceipt, org, body["procurement_receipt_id"])
    lot = _get(session, InventoryLot, org, body["inventory_lot_id"])
    qty = _qty(body["quantity"])
    movement = _post_movement(
        session,
        principal,
        {
            "movement_type": "supplier_return",
            "inventory_item_id": str(lot.inventory_item_id),
            "inventory_lot_id": str(lot.id),
            "from_location_id": str(lot.inventory_location_id),
            "quantity": format(qty, "f"),
            "unit_code": lot.unit_code,
            "origin_type": "procurement_return",
            "origin_id": str(receipt.id),
            "procurement_receipt_id": str(receipt.id),
            "reason": body["reason"],
        },
        idempotency_key=None,
        command="procurement.return.inner",
    )
    row = ProcurementReturn(
        organization_id=org,
        public_code=_next_code(session, org, "RET"),
        procurement_receipt_id=receipt.id,
        inventory_lot_id=lot.id,
        quantity=qty,
        reason=body["reason"],
        inventory_movement_id=movement.id,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "procurement.return", body, "procurement_return", row.id, principal.user_id
    )
    return row


def refuse_automatic_purchase() -> None:
    raise ValidationError("compra_automatica_proibida")


def list_reservations(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(
        session.scalars(select(InventoryReservation).where(InventoryReservation.organization_id == _org(principal)))
    )


def list_picks(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(session.scalars(select(InventoryPick).where(InventoryPick.organization_id == _org(principal))))


def list_counts(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_INVENTORY_READ)
    return list(
        session.scalars(select(InventoryCountSession).where(InventoryCountSession.organization_id == _org(principal)))
    )


def list_requisitions(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    return list(
        session.scalars(select(ProcurementRequisition).where(ProcurementRequisition.organization_id == _org(principal)))
    )


def list_quotations(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    return list(
        session.scalars(select(ProcurementQuotation).where(ProcurementQuotation.organization_id == _org(principal)))
    )


def list_orders(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    return list(session.scalars(select(ProcurementOrder).where(ProcurementOrder.organization_id == _org(principal))))


def list_receipts(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    return list(session.scalars(select(ProcurementReceipt).where(ProcurementReceipt.organization_id == _org(principal))))


def list_returns(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_PROCUREMENT_READ)
    return list(session.scalars(select(ProcurementReturn).where(ProcurementReturn.organization_id == _org(principal))))


def current_order_items(session: Session, order: ProcurementOrder) -> list[ProcurementOrderItem]:
    revision = session.scalar(
        select(ProcurementOrderRevision).where(
            ProcurementOrderRevision.procurement_order_id == order.id,
            ProcurementOrderRevision.revision_number == order.current_revision,
        )
    )
    if revision is None:
        return []
    return list(
        session.scalars(
            select(ProcurementOrderItem).where(ProcurementOrderItem.procurement_order_revision_id == revision.id)
        )
    )


def count_variances(session: Session, count_session: InventoryCountSession) -> list[dict]:
    scopes = list(
        session.scalars(
            select(InventoryCountScope).where(InventoryCountScope.inventory_count_session_id == count_session.id)
        )
    )
    rows = []
    for scope in scopes:
        first = _latest_count(session, scope.id, 1)
        second = _latest_count(session, scope.id, 2) if count_session.require_second_count else first
        counted = second if second is not None else first
        rows.append(
            {
                "scope_id": str(scope.id),
                "inventory_item_id": str(scope.inventory_item_id),
                "inventory_lot_id": str(scope.inventory_lot_id),
                "expected": format(Decimal(scope.expected_quantity), "f"),
                "counted": None if counted is None else format(counted, "f"),
                "variance": None if counted is None else format(counted - Decimal(scope.expected_quantity), "f"),
            }
        )
    return rows


def replenishment_items(session: Session, suggestion_id) -> list[InventoryReplenishmentItem]:
    return list(
        session.scalars(
            select(InventoryReplenishmentItem).where(
                InventoryReplenishmentItem.inventory_replenishment_suggestion_id == suggestion_id
            )
        )
    )


def pick_lines(session: Session, pick_id) -> list[InventoryPickLine]:
    return list(session.scalars(select(InventoryPickLine).where(InventoryPickLine.inventory_pick_id == pick_id)))


def requisition_items(session: Session, requisition_id) -> list[ProcurementRequisitionItem]:
    return list(
        session.scalars(
            select(ProcurementRequisitionItem).where(
                ProcurementRequisitionItem.procurement_requisition_id == requisition_id
            )
        )
    )


def quotation_items(session: Session, quotation_id) -> list[ProcurementQuotationItem]:
    return list(
        session.scalars(
            select(ProcurementQuotationItem).where(ProcurementQuotationItem.procurement_quotation_id == quotation_id)
        )
    )


def receipt_items(session: Session, receipt_id) -> list[ProcurementReceiptItem]:
    return list(
        session.scalars(select(ProcurementReceiptItem).where(ProcurementReceiptItem.procurement_receipt_id == receipt_id))
    )


def reservation_allocations(session: Session, reservation_id) -> list[InventoryReservationAllocation]:
    return list(
        session.scalars(
            select(InventoryReservationAllocation).where(
                InventoryReservationAllocation.inventory_reservation_id == reservation_id
            )
        )
    )


def rebuild_balance(session: Session, organization_id, lot_id) -> Decimal:
    physical = session.scalar(
        select(func.coalesce(func.sum(InventoryMovement.canonical_quantity * InventoryMovement.sign), 0)).where(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.inventory_lot_id == lot_id,
        )
    )
    return Decimal(physical)


def traceability(session: Session, principal: Principal, *, lot_id=None, order_id=None) -> dict:
    require_permission(principal, PERMISSION_INVENTORY_READ)
    org = _org(principal)
    events = []
    if lot_id:
        lot = _get(session, InventoryLot, org, lot_id)
        events.append({"type": "lot", "id": str(lot.id), "code": lot.internal_lot_code, "status": lot.status})
        if lot.procurement_receipt_id:
            receipt = session.get(ProcurementReceipt, lot.procurement_receipt_id)
            if receipt is not None:
                events.append(
                    {
                        "type": "receipt",
                        "id": str(receipt.id),
                        "code": receipt.public_code,
                        "order_id": str(receipt.procurement_order_id),
                    }
                )
                order = session.get(ProcurementOrder, receipt.procurement_order_id)
                if order is not None:
                    events.append(
                        {
                            "type": "purchase_order",
                            "id": str(order.id),
                            "code": order.public_code,
                            "supplier_id": str(order.supplier_id),
                        }
                    )
        for movement in session.scalars(
            select(InventoryMovement)
            .where(InventoryMovement.inventory_lot_id == lot.id)
            .order_by(InventoryMovement.created_at)
        ):
            events.append(
                {
                    "type": "movement",
                    "id": str(movement.id),
                    "movement_type": movement.movement_type,
                    "quantity": format(movement.canonical_quantity, "f"),
                    "origin_type": movement.origin_type,
                    "origin_id": None if movement.origin_id is None else str(movement.origin_id),
                    "production_order_id": None
                    if movement.production_order_id is None
                    else str(movement.production_order_id),
                    "hash": movement.content_hash,
                }
            )
        for alloc in session.scalars(
            select(InventoryReservationAllocation).where(InventoryReservationAllocation.inventory_lot_id == lot.id)
        ):
            reservation = session.get(InventoryReservation, alloc.inventory_reservation_id)
            events.append(
                {
                    "type": "reservation",
                    "id": str(alloc.inventory_reservation_id),
                    "order_id": None if reservation is None else str(reservation.production_order_id),
                    "quantity": format(alloc.quantity, "f"),
                }
            )
    if order_id:
        order = _get(session, ProductionOrder, org, order_id)
        events.append({"type": "production_order", "id": str(order.id), "code": order.public_code, "status": order.status})
        for reservation in session.scalars(
            select(InventoryReservation).where(InventoryReservation.production_order_id == order.id)
        ):
            events.append(
                {
                    "type": "reservation",
                    "id": str(reservation.id),
                    "status": reservation.status,
                    "required": format(reservation.required_quantity, "f"),
                }
            )
        for pick in session.scalars(select(InventoryPick).where(InventoryPick.production_order_id == order.id)):
            events.append({"type": "pick", "id": str(pick.id), "code": pick.public_code, "status": pick.status})
    return {"events": events, "source": "canonical_projection"}