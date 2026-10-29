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


def plan_out(row, *, item_count: int | None = None, items_summary: str | None = None) -> dict:
    payload = {
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
    if item_count is not None:
        payload["item_count"] = item_count
    if items_summary is not None:
        payload["items_summary"] = items_summary
    return payload


def plan_items_summary(display_names: list[str | None]) -> tuple[int, str]:
    """Resumo operacional da lista: não inventa produto principal em multi-item."""
    count = len(display_names)
    if count == 0:
        return 0, "Nenhum item planejado"
    named = [name.strip() for name in display_names if name and name.strip()]
    if count == 1:
        return 1, named[0] if named else "1 item planejado"
    if named:
        return count, f"{named[0]} e mais {count - 1}"
    return count, f"{count} itens planejados"


def plan_item_out(row, *, product=None) -> dict:
    payload = {
        "id": str(row.id),
        "technical_product_id": str(row.technical_product_id),
        "target_mode": row.target_mode,
        "target_quantity": decimal_str(row.target_quantity),
        "unit_weight_g": decimal_str(row.unit_weight_g),
        "priority": row.priority,
        "sort_order": row.sort_order,
        "notes": row.notes,
        "product": None,
    }
    if product is not None:
        payload["product"] = {
            "id": str(product.id),
            "code": product.code,
            "display_name": product.display_name,
        }
    return payload


def order_out(row, *, product=None, plan=None) -> dict:
    payload = {
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
        "product": None,
        "plan": None,
    }
    if product is not None:
        payload["product"] = {
            "id": str(product.id),
            "code": product.code,
            "display_name": product.display_name,
        }
    if plan is not None:
        payload["plan"] = {
            "id": str(plan.id),
            "public_code": plan.public_code,
        }
    return payload


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


def encode_plan_list_cursor(
    operational_date,
    shift: str | None,
    public_code: str,
    item_id: UUID,
) -> str:
    return f"{operational_date.isoformat()}|{shift or ''}|{public_code}|{item_id}"


def decode_plan_list_cursor(
    value: str | None,
) -> tuple[str, str, str, UUID] | None:
    if not value:
        return None
    try:
        date_part, shift_part, code_part, raw_id = value.split("|", 3)
        return date_part, shift_part, code_part, UUID(raw_id)
    except ValueError:
        return None
