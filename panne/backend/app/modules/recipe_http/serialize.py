from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.scale import ScaleResult
from app.modules.formula_lab.models import (
    Approval,
    Formulation,
    FormulationItem,
    FormulationRecipeReference,
    FormulationVersion,
    ProcessStep,
    RecipeReference,
    ScaleCalculation,
    ScaleCalculationItem,
    Trial,
    TrialMeasurement,
)
from app.modules.formula_lab.rules import derived_gross_quantity
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion, MeasurementUnit
from app.modules.nutrition_calculation.models import NutritionCalculation, NutritionCalculationItem
from app.modules.production_http.schemas import decimal_str, envelope


def recipe_card(identity: Formulation, version: FormulationVersion | None) -> dict:
    return {
        "id": str(identity.id),
        "code": identity.code,
        "display_name": identity.display_name,
        "status": identity.status,
        "technical_product_id": str(identity.technical_product_id),
        "row_version": identity.row_version,
        "current_version": None
        if version is None
        else {
            "id": str(version.id),
            "version_number": version.version_number,
            "status": version.status,
        },
    }


def version_out(row: FormulationVersion) -> dict:
    return {
        "id": str(row.id),
        "formulation_id": str(row.formulation_id),
        "version_number": row.version_number,
        "status": row.status,
        "yield_units": row.yield_units,
        "target_unit_weight_g": decimal_str(row.target_unit_weight_g),
        "expected_bake_loss_rate": decimal_str(row.expected_bake_loss_rate),
        "notes": row.notes,
        "published_at": None if row.published_at is None else row.published_at.isoformat(),
        "row_version": row.row_version,
        "created_by_user_id": (
            None if row.created_by_user_id is None else str(row.created_by_user_id)
        ),
    }


def _unit_ref(unit: MeasurementUnit | None) -> dict | None:
    if unit is None:
        return None
    return {
        "id": str(unit.id),
        "code": unit.code,
        "symbol": unit.symbol or unit.code,
        "dimension": unit.dimension,
    }


def _ingredient_ref(
    identity: Ingredient | None, version: IngredientVersion | None
) -> dict | None:
    if identity is None or version is None:
        return None
    return {
        "id": str(identity.id),
        "code": identity.code,
        "display_name": identity.display_name,
        "version_id": str(version.id),
        "version_number": version.version_number,
    }


def load_item_enrichments(
    session: Session, organization_id: UUID, items: list[FormulationItem]
) -> dict[UUID, tuple[dict | None, dict | None]]:
    """Carrega ingredientes e unidades em lote, sempre com escopo da organização.

    Retorna mapa item_id → (ingredient_ref|None, unit_ref|None).
    Versão/ingrediente de outra org não hidrata (None).
    """
    if not items:
        return {}
    version_ids = {item.ingredient_version_id for item in items}
    unit_ids = {item.measurement_unit_id for item in items}
    versions = list(
        session.scalars(
            select(IngredientVersion).where(
                IngredientVersion.id.in_(version_ids),
                IngredientVersion.organization_id == organization_id,
            )
        ).all()
    )
    version_by_id = {row.id: row for row in versions}
    ingredient_ids = {row.ingredient_id for row in versions}
    ingredients = (
        list(
            session.scalars(
                select(Ingredient).where(
                    Ingredient.id.in_(ingredient_ids),
                    Ingredient.organization_id == organization_id,
                )
            ).all()
        )
        if ingredient_ids
        else []
    )
    ingredient_by_id = {row.id: row for row in ingredients}
    units = (
        list(session.scalars(select(MeasurementUnit).where(MeasurementUnit.id.in_(unit_ids))).all())
        if unit_ids
        else []
    )
    unit_by_id = {row.id: row for row in units}
    enriched: dict[UUID, tuple[dict | None, dict | None]] = {}
    for item in items:
        version = version_by_id.get(item.ingredient_version_id)
        identity = None if version is None else ingredient_by_id.get(version.ingredient_id)
        enriched[item.id] = (
            _ingredient_ref(identity, version),
            _unit_ref(unit_by_id.get(item.measurement_unit_id)),
        )
    return enriched


def item_out(
    row: FormulationItem,
    bakers_percentage: str | None = None,
    *,
    ingredient: dict | None = None,
    unit: dict | None = None,
) -> dict:
    return {
        "id": str(row.id),
        "ingredient_version_id": str(row.ingredient_version_id),
        "sequence": row.sequence,
        "net_quantity": decimal_str(row.net_quantity),
        "gross_quantity": decimal_str(
            derived_gross_quantity(row.net_quantity, row.correction_factor)
        ),
        "measurement_unit_id": str(row.measurement_unit_id),
        "correction_factor": decimal_str(row.correction_factor),
        "is_flour_basis": row.is_flour_basis,
        "role": row.role,
        "notes": row.notes,
        "bakers_percentage": bakers_percentage,
        "ingredient": ingredient,
        "unit": unit,
    }


def step_out(row: ProcessStep) -> dict:
    return {
        "id": str(row.id),
        "sequence": row.sequence,
        "title": row.title,
        "instructions": row.instructions,
        "duration_seconds": row.duration_seconds,
        "temperature_celsius": decimal_str(row.temperature_celsius),
    }


def approval_out(row: Approval) -> dict:
    return {
        "id": str(row.id),
        "decision": row.decision,
        "notes": row.notes,
        "occurred_at": row.occurred_at.isoformat(),
        "actor_user_id": str(row.actor_user_id),
    }


def reference_out(row: RecipeReference) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "source_type": row.source_type,
        "source_url": row.source_url,
        "author": row.author,
        "notes": row.notes,
        "row_version": row.row_version,
    }


def reference_link_out(row: FormulationRecipeReference) -> dict:
    return {
        "id": str(row.id),
        "recipe_reference_id": str(row.recipe_reference_id),
        "role": row.role,
    }


def version_reference_out(row) -> dict:
    return {
        "id": str(row.id),
        "recipe_reference_id": None
        if row.recipe_reference_id is None
        else str(row.recipe_reference_id),
        "role": row.role,
        "source_version_label": row.source_version_label,
        "locator_type": row.locator_type,
        "locator_value": row.locator_value,
        "content_hash": row.content_hash,
        "accessed_at": None if row.accessed_at is None else row.accessed_at.isoformat(),
        "snapshot": row.snapshot,
    }


def scale_out(row: ScaleCalculation) -> dict:
    return {
        "id": str(row.id),
        "calculation_mode": row.calculation_mode,
        "input_target_total_dough_mass": decimal_str(row.input_target_total_dough_mass),
        "input_unit_count": row.input_unit_count,
        "input_final_unit_weight_g": decimal_str(row.input_final_unit_weight_g),
        "input_bake_loss_rate": decimal_str(row.input_bake_loss_rate),
        "base_total_net_mass": decimal_str(row.base_total_net_mass),
        "scale_factor": decimal_str(row.scale_factor),
        "required_pre_bake_mass": decimal_str(row.required_pre_bake_mass),
        "algorithm_code": row.algorithm_code,
        "algorithm_version": row.algorithm_version,
        "rounding_mode": row.rounding_mode,
        "presentation_decimal_places": row.presentation_decimal_places,
    }


def scale_item_out(row: ScaleCalculationItem) -> dict:
    return {
        "id": str(row.id),
        "formulation_item_id": str(row.formulation_item_id),
        "sequence": row.sequence,
        "scaled_net_quantity": decimal_str(row.scaled_net_quantity),
        "scaled_gross_quantity": decimal_str(row.scaled_gross_quantity),
        "bakers_percentage": decimal_str(row.bakers_percentage),
    }


def scale_result_out(result: ScaleResult) -> dict:
    return {
        "calculation_mode": result.calculation_mode,
        "input_target_total_dough_mass": decimal_str(result.input_target_total_dough_mass),
        "input_unit_count": result.input_unit_count,
        "input_final_unit_weight_g": decimal_str(result.input_final_unit_weight_g),
        "input_bake_loss_rate": decimal_str(result.input_bake_loss_rate),
        "base_total_net_mass": decimal_str(result.base_total_net_mass),
        "scale_factor": decimal_str(result.scale_factor),
        "required_pre_bake_mass": decimal_str(result.required_pre_bake_mass),
        "items": [
            {
                "formulation_item_id": str(item.formulation_item_id),
                "sequence": item.sequence,
                "scaled_net_quantity": decimal_str(item.scaled_net_quantity),
                "scaled_gross_quantity": decimal_str(item.scaled_gross_quantity),
                "bakers_percentage": decimal_str(item.bakers_percentage),
            }
            for item in result.items
        ],
        "persisted": False,
    }


def trial_out(row: Trial) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "status": row.status,
        "notes": row.notes,
        "planned_on": None if row.planned_on is None else row.planned_on.isoformat(),
        "executed_on": None if row.executed_on is None else row.executed_on.isoformat(),
    }


def measurement_out(row: TrialMeasurement) -> dict:
    return {
        "id": str(row.id),
        "measurement_type": row.measurement_type,
        "value": decimal_str(row.value),
        "measurement_unit_id": None
        if row.measurement_unit_id is None
        else str(row.measurement_unit_id),
        "notes": row.notes,
        "recorded_at": row.recorded_at.isoformat(),
    }


def nutrition_out(row: NutritionCalculation) -> dict:
    return {
        "id": str(row.id),
        "status": row.status,
        "calculation_basis": row.calculation_basis,
        "is_simulation": row.is_simulation,
        "formula_net_mass_g": decimal_str(row.formula_net_mass_g),
        "expected_final_mass_g": decimal_str(row.expected_final_mass_g),
        "portion_mass_g": decimal_str(row.portion_mass_g),
        "algorithm_name": row.algorithm_name,
        "algorithm_version": row.algorithm_version,
        "disclaimer": "Prévia técnica incompleta e não validada regulatoriamente.",
    }


def nutrition_item_out(row: NutritionCalculationItem) -> dict:
    return {
        "id": str(row.id),
        "nutrient_definition_id": str(row.nutrient_definition_id),
        "whole_formula_amount": decimal_str(row.whole_formula_amount),
        "per_100g_amount": decimal_str(row.per_100g_amount),
        "technical_portion_amount": decimal_str(row.technical_portion_amount),
        "completeness_status": row.completeness_status,
    }


def versioned(payload: dict, row_version: int) -> dict:
    return envelope(payload, row_version)
