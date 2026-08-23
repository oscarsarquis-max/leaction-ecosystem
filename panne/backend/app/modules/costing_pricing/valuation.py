"""Seleção determinística de preço vigente. Ausência nunca vira zero."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID


def jsonable(payload: dict) -> dict:
    out = {}
    for key, value in payload.items():
        if isinstance(value, UUID):
            out[key] = str(value)
        elif isinstance(value, Decimal):
            out[key] = format(value, "f")
        else:
            out[key] = value
    return out

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.constants import ZERO
from app.modules.ingredient_catalog.models import (
    IngredientVersion,
    MeasurementUnit,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.production_planning.errors import ValidationError


def _same_dimension(left: MeasurementUnit, right: MeasurementUnit) -> bool:
    return left.dimension == right.dimension


def convert_quantity(
    quantity: Decimal,
    from_unit: MeasurementUnit,
    to_unit: MeasurementUnit,
) -> tuple[Decimal, Decimal, str]:
    if from_unit.id == to_unit.id:
        return quantity, Decimal("1"), "same_unit"
    if not _same_dimension(from_unit, to_unit):
        raise ValidationError("conversao_massa_volume_proibida")
    if from_unit.dimension != "mass":
        raise ValidationError("unidade_incompativel")
    from_si = Decimal(from_unit.si_factor)
    to_si = Decimal(to_unit.si_factor)
    if from_si <= ZERO or to_si <= ZERO:
        raise ValidationError("fator de conversão inválido")
    factor = from_si / to_si
    return quantity * factor, factor, "measurement_unit.si_factor"


def select_price(
    session: Session,
    *,
    ingredient_version_id: UUID,
    valuation_at: datetime,
    currency: str,
    criterion: str,
    explicit_item_id: UUID | None = None,
) -> dict | None:
    version = session.get(IngredientVersion, ingredient_version_id)
    if version is None:
        return None
    items = list(
        session.scalars(
            select(SupplierItem).where(
                SupplierItem.ingredient_id == version.ingredient_id,
                SupplierItem.organization_id == version.organization_id,
                SupplierItem.status == "active",
            )
        )
    )
    if explicit_item_id is not None:
        items = [row for row in items if row.id == explicit_item_id]
    candidates: list[tuple[SupplierItemPrice, SupplierItem]] = []
    for item in items:
        prices = list(
            session.scalars(
                select(SupplierItemPrice).where(
                    SupplierItemPrice.supplier_item_id == item.id,
                    SupplierItemPrice.observed_at <= valuation_at,
                )
            )
        )
        for price in prices:
            if price.currency != currency:
                raise ValidationError("moeda_incompativel")
            candidates.append((price, item))
    if not candidates:
        return None
    if criterion == "explicit_item" and explicit_item_id is None:
        return None
    price, item = max(
        candidates,
        key=lambda pair: (pair[0].observed_at, pair[0].created_at, pair[0].id),
    )
    supplier = session.get(Supplier, item.supplier_id)
    pack_unit = session.get(MeasurementUnit, item.measurement_unit_id)
    return {
        "supplier_id": None if supplier is None else supplier.id,
        "supplier_code": None if supplier is None else supplier.code,
        "supplier_item_id": item.id,
        "supplier_sku": item.supplier_sku,
        "unit_price": price.unit_price,
        "currency": price.currency,
        "package_quantity": item.package_quantity,
        "package_unit_id": item.measurement_unit_id,
        "package_unit_code": None if pack_unit is None else pack_unit.code,
        "observed_at": price.observed_at.isoformat(),
        "source": price.source,
        "price_id": price.id,
        "valuation_at": valuation_at.isoformat(),
        "criterion": criterion,
    }


def cost_for_quantity(
    session: Session,
    snapshot: dict,
    quantity: Decimal,
    quantity_unit_id: UUID,
) -> tuple[Decimal | None, dict]:
    pack_unit = session.get(MeasurementUnit, snapshot["package_unit_id"])
    qty_unit = session.get(MeasurementUnit, quantity_unit_id)
    if pack_unit is None or qty_unit is None:
        return None, {"reason": "unidade ausente"}
    converted, factor, source = convert_quantity(quantity, qty_unit, pack_unit)
    package_qty = Decimal(snapshot["package_quantity"])
    if package_qty <= ZERO:
        return None, {"reason": "embalagem inválida"}
    amount = (converted / package_qty) * Decimal(snapshot["unit_price"])
    evidence = jsonable(
        {
            **snapshot,
            "quantity": format(quantity, "f"),
            "converted_quantity": format(converted, "f"),
            "conversion_factor": format(factor, "f"),
            "conversion_source": source,
        }
    )
    return amount, evidence
