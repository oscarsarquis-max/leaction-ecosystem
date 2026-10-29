from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.scale import base_total_net_mass
from app.modules.formula_lab.completeness import project_completeness
from app.modules.formula_lab.version_references import version_references_of
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
    TechnicalProduct,
    Trial,
    TrialMeasurement,
)
from app.modules.formula_lab.rules import (
    bakers_percentages,
    derived_gross_quantity,
    total_flour_mass,
)
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion
from app.modules.nutrition_calculation.models import NutritionCalculation, NutritionCalculationItem


def list_recipes(
    session: Session,
    organization_id: UUID,
    *,
    q: str | None,
    status: str | None,
    version_status: str | None,
    ingredient_id: UUID | None,
    published_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Formulation, FormulationVersion | None]], int]:
    query = (
        select(Formulation)
        .where(Formulation.organization_id == organization_id)
        .order_by(Formulation.display_name, Formulation.code)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(Formulation.display_name.ilike(pattern), Formulation.code.ilike(pattern))
        )
    if status:
        query = query.where(Formulation.status == status)
    if published_only or version_status or ingredient_id:
        query = query.join(
            FormulationVersion, FormulationVersion.formulation_id == Formulation.id
        )
        if published_only:
            query = query.where(FormulationVersion.status == "published")
        elif version_status:
            query = query.where(FormulationVersion.status == version_status)
        if ingredient_id:
            query = (
                query.join(
                    FormulationItem,
                    FormulationItem.formulation_version_id == FormulationVersion.id,
                )
                .join(
                    IngredientVersion,
                    IngredientVersion.id == FormulationItem.ingredient_version_id,
                )
                .where(IngredientVersion.ingredient_id == ingredient_id)
            )
    total = session.scalar(select(func.count()).select_from(query.distinct().subquery())) or 0
    identities = session.scalars(query.distinct().offset(offset).limit(limit)).all()
    rows: list[tuple[Formulation, FormulationVersion | None]] = []
    for identity in identities:
        version = session.scalar(
            select(FormulationVersion).where(
                FormulationVersion.formulation_id == identity.id,
                FormulationVersion.status == "published",
            )
        )
        if version is None and not published_only:
            version = session.scalar(
                select(FormulationVersion)
                .where(FormulationVersion.formulation_id == identity.id)
                .order_by(FormulationVersion.version_number.desc())
            )
        rows.append((identity, version))
    return rows, total


def versions_of(
    session: Session, organization_id: UUID, formulation_id: UUID
) -> list[FormulationVersion]:
    return list(
        session.scalars(
            select(FormulationVersion)
            .where(
                FormulationVersion.organization_id == organization_id,
                FormulationVersion.formulation_id == formulation_id,
            )
            .order_by(FormulationVersion.version_number.desc())
        )
    )


def items_of(session: Session, version_id: UUID) -> list[FormulationItem]:
    return list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == version_id)
            .order_by(FormulationItem.sequence)
        )
    )


def steps_of(session: Session, version_id: UUID) -> list[ProcessStep]:
    return list(
        session.scalars(
            select(ProcessStep)
            .where(ProcessStep.formulation_version_id == version_id)
            .order_by(ProcessStep.sequence)
        )
    )


def approvals_of(session: Session, version_id: UUID) -> list[Approval]:
    return list(
        session.scalars(
            select(Approval)
            .where(Approval.formulation_version_id == version_id)
            .order_by(Approval.occurred_at.desc(), Approval.id.desc())
        )
    )


def references_of(session: Session, formulation_id: UUID) -> list[FormulationRecipeReference]:
    return list(
        session.scalars(
            select(FormulationRecipeReference).where(
                FormulationRecipeReference.formulation_id == formulation_id
            )
        )
    )


def version_refs_of(session: Session, version_id: UUID):
    return version_references_of(session, version_id)


def list_references(
    session: Session, organization_id: UUID, q: str | None
) -> list[RecipeReference]:
    query = select(RecipeReference).where(RecipeReference.organization_id == organization_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(RecipeReference.title.ilike(pattern))
    return list(session.scalars(query.order_by(RecipeReference.title)))


def scales_of(session: Session, version_id: UUID) -> list[ScaleCalculation]:
    return list(
        session.scalars(
            select(ScaleCalculation)
            .where(ScaleCalculation.formulation_version_id == version_id)
            .order_by(ScaleCalculation.created_at.desc())
        )
    )


def scale_items_of(session: Session, scale_id: UUID) -> list[ScaleCalculationItem]:
    return list(
        session.scalars(
            select(ScaleCalculationItem)
            .where(ScaleCalculationItem.scale_calculation_id == scale_id)
            .order_by(ScaleCalculationItem.sequence)
        )
    )


def trials_of(session: Session, version_id: UUID) -> list[Trial]:
    return list(
        session.scalars(
            select(Trial)
            .where(Trial.formulation_version_id == version_id)
            .order_by(Trial.created_at.desc())
        )
    )


def measurements_of(session: Session, trial_id: UUID) -> list[TrialMeasurement]:
    return list(
        session.scalars(
            select(TrialMeasurement)
            .where(TrialMeasurement.trial_id == trial_id)
            .order_by(TrialMeasurement.recorded_at.desc())
        )
    )


def latest_nutrition(session: Session, version_id: UUID) -> NutritionCalculation | None:
    return session.scalar(
        select(NutritionCalculation)
        .where(NutritionCalculation.formulation_version_id == version_id)
        .order_by(NutritionCalculation.calculated_at.desc())
    )


def nutrition_items_of(
    session: Session, calculation_id: UUID
) -> list[NutritionCalculationItem]:
    return list(
        session.scalars(
            select(NutritionCalculationItem).where(
                NutritionCalculationItem.nutrition_calculation_id == calculation_id
            )
        )
    )


def product_of(session: Session, product_id: UUID) -> TechnicalProduct | None:
    return session.get(TechnicalProduct, product_id)


def bakers_view(session: Session, version_id: UUID) -> dict:
    items = items_of(session, version_id)
    flour = total_flour_mass(items)
    percents = bakers_percentages(items)
    return {
        "flour_mass": None if flour is None else str(flour),
        "explained_absence": flour is None,
        "items": [
            {
                "id": str(item.id),
                "net_quantity": str(item.net_quantity),
                "gross_quantity": str(
                    derived_gross_quantity(item.net_quantity, item.correction_factor)
                ),
                "is_flour_basis": item.is_flour_basis,
                "bakers_percentage": (
                    None if percents is None else str(percents[item.id])
                ),
            }
            for item in items
        ],
    }


def yield_of(session: Session, version: FormulationVersion) -> dict:
    items = items_of(session, version.id)
    base = None
    if items:
        try:
            base = base_total_net_mass(items)
        except ValueError:
            base = None
    nutrition = latest_nutrition(session, version.id)
    expected_final = None
    if version.yield_units and version.target_unit_weight_g is not None:
        expected_final = Decimal(version.yield_units) * version.target_unit_weight_g
    return {
        "base_net_mass": None if base is None else str(base),
        "yield_units": version.yield_units,
        "target_unit_weight_g": None
        if version.target_unit_weight_g is None
        else str(version.target_unit_weight_g),
        "expected_bake_loss_rate": None
        if version.expected_bake_loss_rate is None
        else str(version.expected_bake_loss_rate),
        "expected_final_mass_g": None if expected_final is None else str(expected_final),
        "portion_mass_g": None
        if nutrition is None or nutrition.portion_mass_g is None
        else str(nutrition.portion_mass_g),
    }


def completeness_of(session: Session, recipe: Formulation, version: FormulationVersion) -> dict:
    return project_completeness(session, recipe, version)


def ingredient_label(session: Session, ingredient_version_id: UUID) -> str:
    version = session.get(IngredientVersion, ingredient_version_id)
    if version is None:
        return str(ingredient_version_id)
    identity = session.get(Ingredient, version.ingredient_id)
    if identity is None:
        return str(ingredient_version_id)
    return f"{identity.display_name} v{version.version_number}"
