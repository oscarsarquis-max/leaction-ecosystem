"""Filtros fechados, intervalo [início, fim) e fuso da organização."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.modules.production_planning.errors import ValidationError
from app.modules.reporting_analytics.constants import (
    DEFAULT_PERIOD_DAYS,
    DEFAULT_TIMEZONE,
    MAX_PERIOD_DAYS,
)

ALLOWED_FILTER_KEYS = frozenset(
    {
        "period_start",
        "period_end",
        "timezone",
        "establishment_id",
        "technical_product_id",
        "formulation_id",
        "formulation_version_id",
        "production_order_id",
        "production_batch_id",
        "status",
        "ingredient_id",
        "supplier_id",
        "cost_category",
        "price_channel",
        "compliance_status",
        "cursor",
        "limit",
        "order_by",
    }
)
ALLOWED_ORDER_BY = frozenset({"created_at", "public_code", "status", "occurred_at", "amount"})


def _parse_uuid(value, field: str) -> UUID | None:
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ValidationError("filtro_invalido") from exc


def _parse_dt(value, tz: ZoneInfo) -> datetime | None:
    if value in (None, ""):
        return None
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("filtro_invalido") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed


@dataclass(frozen=True)
class ReportFilters:
    period_start: datetime
    period_end: datetime
    timezone: str
    establishment_id: UUID | None = None
    technical_product_id: UUID | None = None
    formulation_id: UUID | None = None
    formulation_version_id: UUID | None = None
    production_order_id: UUID | None = None
    production_batch_id: UUID | None = None
    status: str | None = None
    ingredient_id: UUID | None = None
    supplier_id: UUID | None = None
    cost_category: str | None = None
    price_channel: str | None = None
    compliance_status: str | None = None
    cursor: str | None = None
    limit: int = 50
    order_by: str = "created_at"

    def as_dict(self) -> dict:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "timezone": self.timezone,
            "establishment_id": None if self.establishment_id is None else str(self.establishment_id),
            "technical_product_id": None
            if self.technical_product_id is None
            else str(self.technical_product_id),
            "formulation_id": None if self.formulation_id is None else str(self.formulation_id),
            "formulation_version_id": None
            if self.formulation_version_id is None
            else str(self.formulation_version_id),
            "production_order_id": None
            if self.production_order_id is None
            else str(self.production_order_id),
            "production_batch_id": None
            if self.production_batch_id is None
            else str(self.production_batch_id),
            "status": self.status,
            "ingredient_id": None if self.ingredient_id is None else str(self.ingredient_id),
            "supplier_id": None if self.supplier_id is None else str(self.supplier_id),
            "cost_category": self.cost_category,
            "price_channel": self.price_channel,
            "compliance_status": self.compliance_status,
            "limit": self.limit,
            "order_by": self.order_by,
        }


def normalize_filters(raw: dict | None, *, now: datetime | None = None) -> ReportFilters:
    payload = dict(raw or {})
    unknown = set(payload) - ALLOWED_FILTER_KEYS
    if unknown:
        raise ValidationError("filtro_invalido")
    timezone = str(payload.get("timezone") or DEFAULT_TIMEZONE)
    try:
        zone = ZoneInfo(timezone)
    except Exception as exc:
        raise ValidationError("filtro_invalido") from exc
    moment = now or datetime.now(UTC)
    local_now = moment.astimezone(zone)
    start = _parse_dt(payload.get("period_start"), zone)
    end = _parse_dt(payload.get("period_end"), zone)
    if start is None and end is None:
        end = local_now
        start = end - timedelta(days=DEFAULT_PERIOD_DAYS)
    if start is None or end is None:
        raise ValidationError("filtro_invalido")
    if end <= start:
        raise ValidationError("filtro_invalido")
    if (end - start) > timedelta(days=MAX_PERIOD_DAYS):
        raise ValidationError("periodo_excedido")
    order_by = str(payload.get("order_by") or "created_at")
    if order_by not in ALLOWED_ORDER_BY:
        raise ValidationError("filtro_invalido")
    try:
        limit = int(payload.get("limit") or 50)
    except (TypeError, ValueError) as exc:
        raise ValidationError("filtro_invalido") from exc
    if limit < 1 or limit > 200:
        raise ValidationError("filtro_invalido")
    return ReportFilters(
        period_start=start,
        period_end=end,
        timezone=timezone,
        establishment_id=_parse_uuid(payload.get("establishment_id"), "establishment_id"),
        technical_product_id=_parse_uuid(payload.get("technical_product_id"), "technical_product_id"),
        formulation_id=_parse_uuid(payload.get("formulation_id"), "formulation_id"),
        formulation_version_id=_parse_uuid(
            payload.get("formulation_version_id"), "formulation_version_id"
        ),
        production_order_id=_parse_uuid(payload.get("production_order_id"), "production_order_id"),
        production_batch_id=_parse_uuid(payload.get("production_batch_id"), "production_batch_id"),
        status=payload.get("status"),
        ingredient_id=_parse_uuid(payload.get("ingredient_id"), "ingredient_id"),
        supplier_id=_parse_uuid(payload.get("supplier_id"), "supplier_id"),
        cost_category=payload.get("cost_category"),
        price_channel=payload.get("price_channel"),
        compliance_status=payload.get("compliance_status"),
        cursor=payload.get("cursor"),
        limit=limit,
        order_by=order_by,
    )


def utc_window(filters: ReportFilters) -> tuple[datetime, datetime]:
    return filters.period_start.astimezone(UTC), filters.period_end.astimezone(UTC)
