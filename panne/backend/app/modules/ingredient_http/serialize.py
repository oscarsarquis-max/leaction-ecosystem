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


def nutrient_out(row: IngredientNutrient) -> dict:
    return {
        "id": str(row.id),
        "nutrient_id": str(row.nutrient_id),
        "value": decimal_str(row.value),
        "value_status": row.value_status,
        "limit_of_quantification": decimal_str(row.limit_of_quantification),
        "loq_unit_id": None if row.loq_unit_id is None else str(row.loq_unit_id),
        "method_or_source": row.method_or_source,
    }


def allergen_out(row: IngredientAllergen) -> dict:
    return {
        "id": str(row.id),
        "allergen_id": str(row.allergen_id),
        "presence": row.presence,
        "data_source_id": None if row.data_source_id is None else str(row.data_source_id),
        "evidence_note": row.evidence_note,
    }


def supplier_out(row: Supplier) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "status": row.status,
        "row_version": row.row_version,
    }


def item_out(row: SupplierItem, latest: SupplierItemPrice | None = None) -> dict:
    payload = {
        "id": str(row.id),
        "supplier_id": str(row.supplier_id),
        "ingredient_id": str(row.ingredient_id),
        "supplier_sku": row.supplier_sku,
        "description": row.description,
        "package_quantity": decimal_str(row.package_quantity),
        "measurement_unit_id": str(row.measurement_unit_id),
        "status": row.status,
        "row_version": row.row_version,
        "latest_purchase": None
        if latest is None
        else {
            "unit_price": decimal_str(latest.unit_price),
            "currency": latest.currency,
            "observed_at": latest.observed_at.isoformat(),
        },
    }
    return payload


def price_out(row: SupplierItemPrice) -> dict:
    return {
        "id": str(row.id),
        "supplier_item_id": str(row.supplier_item_id),
        "unit_price": decimal_str(row.unit_price),
        "currency": row.currency,
        "observed_at": row.observed_at.isoformat(),
        "source": row.source,
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
