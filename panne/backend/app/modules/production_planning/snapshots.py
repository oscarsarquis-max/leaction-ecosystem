from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_quantity
from app.modules.formula_lab.models import (
    FormulationItem,
    ProcessStep,
    ScaleCalculation,
    ScaleCalculationItem,
)
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion, MeasurementUnit
from app.modules.production_planning.batches import split_target
from app.modules.production_planning.constants import TARGET_MODE_UNITS
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionOrder,
    ProductionOrderMaterial,
    ProductionOrderStep,
)
from app.modules.production_planning.support import digest


def build_release_snapshots(session: Session, order: ProductionOrder) -> tuple[str, str, str]:
    if order.scale_calculation_id is None or order.formulation_version_id is None:
        raise ValidationError("ordem sem escala ou formulação")
    scale = session.get(ScaleCalculation, order.scale_calculation_id)
    if scale is None:
        raise ValidationError("escala inexistente")
    items = list(
        session.scalars(
            select(ScaleCalculationItem)
            .where(ScaleCalculationItem.scale_calculation_id == scale.id)
            .order_by(ScaleCalculationItem.sequence)
        )
    )
    if not items:
        raise ValidationError("escala sem itens")
    materials: list[ProductionOrderMaterial] = []
    material_canonical: list[dict] = []
    for item in items:
        formulation_item = session.get(FormulationItem, item.formulation_item_id)
        ingredient_version = session.get(IngredientVersion, item.ingredient_version_id)
        unit = session.get(MeasurementUnit, item.measurement_unit_id)
        if formulation_item is None or ingredient_version is None or unit is None:
            raise ValidationError("snapshot incompleto")
        ingredient = session.get(Ingredient, ingredient_version.ingredient_id)
        if ingredient is None:
            raise ValidationError("ingrediente do snapshot ausente")
        row = ProductionOrderMaterial(
            organization_id=order.organization_id,
            production_order_id=order.id,
            formulation_item_id=item.formulation_item_id,
            ingredient_version_id=item.ingredient_version_id,
            operational_name=ingredient.display_name,
            measurement_unit_id=unit.id,
            unit_code=unit.code,
            unit_name=unit.name,
            net_quantity=item.scaled_net_quantity,
            correction_factor=item.base_correction_factor,
            gross_quantity=item.scaled_gross_quantity,
            bakers_percentage=item.bakers_percentage,
            is_flour_basis=formulation_item.is_flour_basis,
            presentation_sequence=item.sequence,
            algorithm_code=scale.algorithm_code,
            algorithm_version=scale.algorithm_version,
            rounding_mode=scale.rounding_mode,
            presentation_decimal_places=scale.presentation_decimal_places,
        )
        session.add(row)
        materials.append(row)
        material_canonical.append(
            {
                "sequence": item.sequence,
                "name": ingredient.display_name,
                "unit": unit.code,
                "net": format(item.scaled_net_quantity, "f"),
                "gross": format(item.scaled_gross_quantity, "f"),
                "factor": format(item.base_correction_factor, "f"),
                "percent": None
                if item.bakers_percentage is None
                else format(item.bakers_percentage, "f"),
                "flour": formulation_item.is_flour_basis,
                "algorithm": scale.algorithm_code,
                "algorithm_version": scale.algorithm_version,
            }
        )
    session.flush()
    steps = list(
        session.scalars(
            select(ProcessStep)
            .where(ProcessStep.formulation_version_id == order.formulation_version_id)
            .order_by(ProcessStep.sequence)
        )
    )
    step_canonical: list[dict] = []
    for step in steps:
        session.add(
            ProductionOrderStep(
                organization_id=order.organization_id,
                production_order_id=order.id,
                process_step_id=step.id,
                sequence=step.sequence,
                title=step.title,
                instructions=step.instructions,
                duration_seconds=step.duration_seconds,
                temperature_value=step.temperature_celsius,
                temperature_unit="celsius" if step.temperature_celsius is not None else None,
                notes=None,
                control_points=[],
            )
        )
        step_canonical.append(
            {
                "sequence": step.sequence,
                "title": step.title,
                "instructions": step.instructions,
                "duration": step.duration_seconds,
                "temperature": None
                if step.temperature_celsius is None
                else format(step.temperature_celsius, "f"),
            }
        )
    session.flush()
    _allocate_batches(session, order, materials)
    materials_hash = digest(material_canonical)
    steps_hash = digest(step_canonical)
    snapshot_hash = digest({"materials": materials_hash, "steps": steps_hash})
    return materials_hash, steps_hash, snapshot_hash


def _allocate_batches(
    session: Session,
    order: ProductionOrder,
    materials: list[ProductionOrderMaterial],
) -> None:
    batches = list(
        session.scalars(
            select(ProductionBatch)
            .where(ProductionBatch.production_order_id == order.id)
            .order_by(ProductionBatch.sequence)
        )
    )
    if not batches:
        raise ValidationError("ordem sem batelada")
    integer = order.target_mode == TARGET_MODE_UNITS
    for material in materials:
        nets = split_target(material.net_quantity, len(batches), integer_units=False)
        grosses = split_target(material.gross_quantity, len(batches), integer_units=False)
        if integer:
            pass
        for batch, (net, _, net_rem), (gross, _, _) in zip(
            batches, nets, grosses, strict=True
        ):
            session.add(
                ProductionBatchMaterial(
                    organization_id=order.organization_id,
                    production_batch_id=batch.id,
                    production_order_material_id=material.id,
                    planned_net_quantity=quantize_quantity(net),
                    planned_gross_quantity=quantize_quantity(gross),
                    remainder_applied=net_rem,
                )
            )
    session.flush()
    for material in materials:
        allocated = session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_order_material_id == material.id
            )
        )
        net_sum = sum((row.planned_net_quantity for row in allocated), Decimal("0"))
        if net_sum != material.net_quantity:
            raise ValidationError("alocacao de batelada diverge do snapshot")


def snapshot_complete(session: Session, order_id: UUID) -> bool:
    materials = session.scalars(
        select(ProductionOrderMaterial.id).where(
            ProductionOrderMaterial.production_order_id == order_id
        )
    ).all()
    return bool(materials)
