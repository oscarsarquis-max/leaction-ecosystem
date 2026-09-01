"""Projeção da receita ligada ao produto via Formulation.technical_product_id.

Não infere por código/nome. Sem preços. Sem conversão massa→unidade.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import (
    Formulation,
    FormulationItem,
    FormulationVersion,
    ProcessStep,
    ScaleCalculation,
)
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion, MeasurementUnit


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def current_recipe_projection(
    session: Session, product_id: UUID, organization_id: UUID
) -> dict | None:
    formulations = list(
        session.scalars(
            select(Formulation).where(
                Formulation.technical_product_id == product_id,
                Formulation.organization_id == organization_id,
            )
        )
    )
    if not formulations:
        return None

    formulation_ids = [row.id for row in formulations]
    versions = list(
        session.scalars(
            select(FormulationVersion).where(
                FormulationVersion.formulation_id.in_(formulation_ids),
                FormulationVersion.organization_id == organization_id,
            )
        )
    )
    if not versions:
        return None

    published = [row for row in versions if row.status == "published"]
    chosen = max(published, key=lambda row: (row.published_at or row.created_at, row.version_number)) if published else max(
        versions, key=lambda row: (row.version_number, row.created_at)
    )
    identity = next(row for row in formulations if row.id == chosen.formulation_id)
    return _project_version(session, identity, chosen, organization_id)


def _project_version(
    session: Session,
    identity: Formulation,
    version: FormulationVersion,
    organization_id: UUID,
) -> dict:
    items = list(
        session.scalars(
            select(FormulationItem)
            .where(
                FormulationItem.formulation_version_id == version.id,
                FormulationItem.organization_id == organization_id,
            )
            .order_by(FormulationItem.sequence)
        )
    )
    steps = list(
        session.scalars(
            select(ProcessStep)
            .where(
                ProcessStep.formulation_version_id == version.id,
                ProcessStep.organization_id == organization_id,
            )
            .order_by(ProcessStep.sequence)
        )
    )
    scale = session.scalar(
        select(ScaleCalculation)
        .where(
            ScaleCalculation.formulation_version_id == version.id,
            ScaleCalculation.organization_id == organization_id,
        )
        .order_by(ScaleCalculation.created_at.desc())
        .limit(1)
    )
    yield_mass = None
    if scale is not None:
        yield_mass = _dec(scale.input_target_total_dough_mass or scale.required_pre_bake_mass)

    version_ids = {item.ingredient_version_id for item in items}
    unit_ids = {item.measurement_unit_id for item in items}
    versions = list(
        session.scalars(
            select(IngredientVersion).where(
                IngredientVersion.id.in_(version_ids),
                IngredientVersion.organization_id == organization_id,
            )
        )
    ) if version_ids else []
    version_by_id = {row.id: row for row in versions}
    ingredient_ids = {row.ingredient_id for row in versions}
    ingredients = list(
        session.scalars(
            select(Ingredient).where(
                Ingredient.id.in_(ingredient_ids),
                Ingredient.organization_id == organization_id,
            )
        )
    ) if ingredient_ids else []
    ingredient_by_id = {row.id: row for row in ingredients}
    units = list(
        session.scalars(select(MeasurementUnit).where(MeasurementUnit.id.in_(unit_ids)))
    ) if unit_ids else []
    unit_by_id = {row.id: row for row in units}

    projected_items = []
    for item in items:
        iver = version_by_id.get(item.ingredient_version_id)
        ingredient = None if iver is None else ingredient_by_id.get(iver.ingredient_id)
        unit = unit_by_id.get(item.measurement_unit_id)
        projected_items.append(
            {
                "ingredient_id": None if ingredient is None else str(ingredient.id),
                "code": None if ingredient is None else ingredient.code,
                "display_name": None if ingredient is None else ingredient.display_name,
                "quantity": _dec(item.net_quantity),
                "unit": None if unit is None else (unit.symbol or unit.code),
                "role": item.role,
                "is_flour_basis": item.is_flour_basis,
            }
        )

    return {
        "id": str(identity.id),
        "code": identity.code,
        "display_name": identity.display_name,
        "formulation_status": identity.status,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "version_status": version.status,
        "published_at": None if version.published_at is None else version.published_at.isoformat(),
        "is_published": version.status == "published",
        "yield_mass_g": yield_mass,
        "items": projected_items,
        "steps": [
            {
                "sequence": step.sequence,
                "title": step.title,
                "instructions": step.instructions,
            }
            for step in steps
        ],
    }
