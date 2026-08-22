from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.production_http.schemas import decimal_str


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "+00:00"
    return value.isoformat()


def plan_out(row) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "establishment_id": str(row.establishment_id),
        "operational_date": row.operational_date.isoformat(),
        "shift": row.shift,
        "status": row.status,
        "notes": row.notes,
        "row_version": row.row_version,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
        "scheduled_at": iso(row.scheduled_at),
    }


def plan_item_out(row) -> dict:
    return {
        "id": str(row.id),
        "technical_product_id": str(row.technical_product_id),
        "target_mode": row.target_mode,
        "target_quantity": decimal_str(row.target_quantity),
        "unit_weight_g": decimal_str(row.unit_weight_g),
        "priority": row.priority,
        "sort_order": row.sort_order,
        "notes": row.notes,
    }


def order_out(row) -> dict:
    return {
        "id": str(row.id),
        "public_code": row.public_code,
        "establishment_id": str(row.establishment_id),
        "plan_id": None if row.plan_id is None else str(row.plan_id),
        "technical_product_id": str(row.technical_product_id),
        "target_mode": row.target_mode,
        "target_quantity": decimal_str(row.target_quantity),
        "priority": row.priority,
        "status": row.status,
        "planned_start_at": iso(row.planned_start_at),
        "planned_end_at": iso(row.planned_end_at),
        "row_version": row.row_version,
        "materials_hash": getattr(row, "materials_hash", None),
        "steps_hash": getattr(row, "steps_hash", None),
        "snapshot_hash": getattr(row, "snapshot_hash", None),
    }


def batch_out(row) -> dict:
    return {
        "id": str(row.id),
        "production_order_id": str(row.production_order_id),
        "sequence": row.sequence,
        "operational_code": row.operational_code,
        "target_mode": row.target_mode,
        "target_quantity": decimal_str(row.target_quantity),
        "status": row.status,
        "row_version": row.row_version,
        "planned_start_at": iso(row.planned_start_at),
        "planned_end_at": iso(row.planned_end_at),
    }


def conversion_out(row) -> dict:
    return {
        "entered_quantity": decimal_str(row.quantity),
        "entered_unit": row.unit_code,
        "canonical_quantity": decimal_str(getattr(row, "canonical_quantity", row.quantity)),
        "canonical_unit": getattr(row, "canonical_unit_code", row.unit_code),
        "conversion_factor": decimal_str(getattr(row, "conversion_factor", Decimal("1"))),
        "conversion_source": getattr(row, "conversion_source", "legacy_identity"),
        "conversion_version": getattr(row, "conversion_version", "1"),
    }


def page(items: list, next_cursor: str | None) -> dict:
    return {"items": items, "next_cursor": next_cursor}


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    return f"{iso(created_at)}|{item_id}"


def decode_cursor(value: str | None) -> tuple[datetime | None, UUID | None]:
    if not value:
        return None, None
    stamp, _, raw_id = value.partition("|")
    try:
        return datetime.fromisoformat(stamp), UUID(raw_id)
    except ValueError:
        return None, None
