from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import (
    Allergen,
    DataSource,
    Ingredient,
    IngredientAllergen,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
    UnitConversion,
)
from app.modules.production_http.schemas import decimal_str, envelope


def _unit_ref(unit: MeasurementUnit | None) -> dict | None:
    if unit is None:
        return None
    return {
        "id": str(unit.id),
        "code": unit.code,
        "symbol": unit.symbol or unit.code,
        "name": unit.name,
        "dimension": unit.dimension,
    }


def _nutrient_ref(row: NutrientDefinition | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "group_code": row.group_code,
    }


def _allergen_ref(row: Allergen | None) -> dict | None:
    if row is None:
        return None
    return {"id": str(row.id), "code": row.code, "name": row.name}


def _supplier_ref(row: Supplier | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
    }


def load_nutrient_enrichments(
    session: Session, rows: list[IngredientNutrient]
) -> dict[UUID, tuple[dict | None, dict | None, dict | None]]:
    """Lote: nutriente + unidade do valor + unidade do LQ. Órfãos → None."""
    if not rows:
        return {}
    nutrient_ids = {row.nutrient_id for row in rows}
    loq_unit_ids = {row.loq_unit_id for row in rows if row.loq_unit_id is not None}
    nutrients = list(
        session.scalars(select(NutrientDefinition).where(NutrientDefinition.id.in_(nutrient_ids))).all()
    )
    nutrient_by_id = {row.id: row for row in nutrients}
    unit_ids = {row.unit_id for row in nutrients} | loq_unit_ids
    units = (
        list(session.scalars(select(MeasurementUnit).where(MeasurementUnit.id.in_(unit_ids))).all())
        if unit_ids
        else []
    )
    unit_by_id = {row.id: row for row in units}
    result: dict[UUID, tuple[dict | None, dict | None, dict | None]] = {}
    for row in rows:
        definition = nutrient_by_id.get(row.nutrient_id)
        value_unit = None if definition is None else unit_by_id.get(definition.unit_id)
        loq_unit = None if row.loq_unit_id is None else unit_by_id.get(row.loq_unit_id)
        result[row.id] = (_nutrient_ref(definition), _unit_ref(value_unit), _unit_ref(loq_unit))
    return result


def load_allergen_enrichments(
    session: Session, rows: list[IngredientAllergen]
) -> dict[UUID, dict | None]:
    """Lote: alergênico do catálogo. Órfãos → None."""
    if not rows:
        return {}
    allergen_ids = {row.allergen_id for row in rows}
    allergens = list(session.scalars(select(Allergen).where(Allergen.id.in_(allergen_ids))).all())
    allergen_by_id = {row.id: row for row in allergens}
    return {row.id: _allergen_ref(allergen_by_id.get(row.allergen_id)) for row in rows}


def load_item_enrichments(
    session: Session, organization_id: UUID, rows: list[SupplierItem]
) -> dict[UUID, tuple[dict | None, dict | None]]:
    """Lote: unidade + fornecedor org-scoped. Outra org / órfão → None."""
    if not rows:
        return {}
    unit_ids = {row.measurement_unit_id for row in rows}
    supplier_ids = {row.supplier_id for row in rows}
    units = list(
        session.scalars(select(MeasurementUnit).where(MeasurementUnit.id.in_(unit_ids))).all()
    )
    unit_by_id = {row.id: row for row in units}
    suppliers = list(
        session.scalars(
            select(Supplier).where(
                Supplier.id.in_(supplier_ids),
                Supplier.organization_id == organization_id,
            )
        ).all()
    )
    supplier_by_id = {row.id: row for row in suppliers}
    return {
        row.id: (
            _unit_ref(unit_by_id.get(row.measurement_unit_id)),
            _supplier_ref(supplier_by_id.get(row.supplier_id)),
        )
        for row in rows
    }


def _ingredient_ref(row: Ingredient | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
    }


def load_ingredient_refs(
    session: Session, organization_id: UUID, rows: list[SupplierItem]
) -> dict[UUID, dict | None]:
    """Lote: ingrediente org-scoped. Outra org / órfão → None."""
    if not rows:
        return {}
    ingredient_ids = {row.ingredient_id for row in rows}
    ingredients = list(
        session.scalars(
            select(Ingredient).where(
                Ingredient.id.in_(ingredient_ids),
                Ingredient.organization_id == organization_id,
            )
        ).all()
    )
    by_id = {row.id: row for row in ingredients}
    return {row.id: _ingredient_ref(by_id.get(row.ingredient_id)) for row in rows}


def ingredient_card(identity: Ingredient, version: IngredientVersion | None) -> dict:
    return {
        "id": str(identity.id),
        "code": identity.code,
        "display_name": identity.display_name,
        "ingredient_type": identity.ingredient_type,
        "status": identity.status,
        "row_version": identity.row_version,
        "current_version": None
        if version is None
        else {
            "id": str(version.id),
            "version_number": version.version_number,
            "status": version.status,
        },
    }


def version_out(row: IngredientVersion) -> dict:
    return {
        "id": str(row.id),
        "ingredient_id": str(row.ingredient_id),
        "version_number": row.version_number,
        "status": row.status,
        "data_source_id": None if row.data_source_id is None else str(row.data_source_id),
        "nutrition_basis_type": row.nutrition_basis_type,
        "nutrition_basis_quantity": decimal_str(row.nutrition_basis_quantity),
        "nutrition_basis_unit_id": str(row.nutrition_basis_unit_id),
        "notes": row.notes,
        "row_version": row.row_version,
        "created_by_user_id": (
            None if row.created_by_user_id is None else str(row.created_by_user_id)
        ),
    }


def composition_out(row: IngredientComposition) -> dict:
    return {
        "id": str(row.id),
        "component_version_id": str(row.component_ingredient_version_id),
        "component_type": row.component_type,
        "quantity": decimal_str(row.quantity),
        "measurement_unit_id": str(row.measurement_unit_id),
        "sequence": row.sequence,
    }


def nutrient_out(
    row: IngredientNutrient,
    *,
    nutrient: dict | None = None,
    unit: dict | None = None,
    loq_unit: dict | None = None,
) -> dict:
    return {
        "id": str(row.id),
        "nutrient_id": str(row.nutrient_id),
        "value": decimal_str(row.value),
        "value_status": row.value_status,
        "limit_of_quantification": decimal_str(row.limit_of_quantification),
        "loq_unit_id": None if row.loq_unit_id is None else str(row.loq_unit_id),
        "method_or_source": row.method_or_source,
        "nutrient": nutrient,
        "unit": unit,
        "loq_unit": loq_unit,
    }


def allergen_out(row: IngredientAllergen, *, allergen: dict | None = None) -> dict:
    return {
        "id": str(row.id),
        "allergen_id": str(row.allergen_id),
        "presence": row.presence,
        "data_source_id": None if row.data_source_id is None else str(row.data_source_id),
        "evidence_note": row.evidence_note,
        "allergen": allergen,
    }


def supplier_out(row: Supplier, *, active_item_count: int | None = None) -> dict:
    payload = {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "status": row.status,
        "row_version": row.row_version,
    }
    if active_item_count is not None:
        payload["active_item_count"] = active_item_count
    return payload


def item_out(
    row: SupplierItem,
    latest: SupplierItemPrice | None = None,
    *,
    unit: dict | None = None,
    supplier: dict | None = None,
    ingredient: dict | None = None,
    include_purchase: bool = True,
) -> dict:
    purchase = None
    if include_purchase and latest is not None:
        purchase = {
            "unit_price": decimal_str(latest.unit_price),
            "currency": latest.currency,
            "observed_at": latest.observed_at.isoformat(),
        }
    return {
        "id": str(row.id),
        "supplier_id": str(row.supplier_id),
        "ingredient_id": str(row.ingredient_id),
        "supplier_sku": row.supplier_sku,
        "description": row.description,
        "package_quantity": decimal_str(row.package_quantity),
        "measurement_unit_id": str(row.measurement_unit_id),
        "status": row.status,
        "row_version": row.row_version,
        "unit": unit,
        "supplier": supplier,
        "ingredient": ingredient,
        "latest_purchase": purchase,
    }


def price_out(row: SupplierItemPrice, *, is_latest: bool = False) -> dict:
    return {
        "id": str(row.id),
        "supplier_item_id": str(row.supplier_item_id),
        "unit_price": decimal_str(row.unit_price),
        "currency": row.currency,
        "observed_at": row.observed_at.isoformat(),
        "source": row.source,
        "is_latest": is_latest,
    }


def unit_out(row: MeasurementUnit) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "dimension": row.dimension,
        "symbol": row.symbol,
        "access": "somente_leitura",
    }


def conversion_out(row: UnitConversion) -> dict:
    return {
        "id": str(row.id),
        "from_unit_id": str(row.from_unit_id),
        "to_unit_id": str(row.to_unit_id),
        "factor": decimal_str(row.factor),
        "access": "somente_leitura",
    }


def nutrient_def_out(row: NutrientDefinition) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "unit_id": str(row.unit_id),
        "group_code": row.group_code,
        "access": "somente_leitura",
    }


def allergen_def_out(row: Allergen) -> dict:
    return {"id": str(row.id), "code": row.code, "name": row.name, "access": "somente_leitura"}


def source_out(row: DataSource) -> dict:
    return {
        "id": str(row.id),
        "source_type": row.source_type,
        "title": row.title,
        "version_label": row.version_label,
        "status": row.status,
        "access": "somente_leitura",
    }


def versioned(payload: dict, row_version: int) -> dict:
    return envelope(payload, row_version)
