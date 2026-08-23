from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import (
    Formulation,
    FormulationItem,
    FormulationVersion,
    FormulationVersionRecipeReference,
    ProcessStep,
    Trial,
)
from app.modules.formula_lab.rules import latest_approval_decision, total_flour_mass
from app.modules.ingredient_catalog.models import IngredientVersion
from app.modules.nutrition_calculation.models import NutritionCalculation


def project_completeness(
    session: Session, recipe: Formulation, version: FormulationVersion
) -> dict:
    items = list(
        session.scalars(
            select(FormulationItem).where(FormulationItem.formulation_version_id == version.id)
        )
    )
    steps = list(
        session.scalars(
            select(ProcessStep).where(ProcessStep.formulation_version_id == version.id)
        )
    )
    refs = list(
        session.scalars(
            select(FormulationVersionRecipeReference).where(
                FormulationVersionRecipeReference.formulation_version_id == version.id
            )
        )
    )
    trials = list(
        session.scalars(select(Trial).where(Trial.formulation_version_id == version.id))
    )
    nutrition = session.scalar(
        select(NutritionCalculation)
        .where(NutritionCalculation.formulation_version_id == version.id)
        .order_by(NutritionCalculation.calculated_at.desc())
    )
    decision = latest_approval_decision(session, version.id)
    pending: list[dict] = []

    def add(code: str, label: str, blocking: bool, origin: str) -> None:
        pending.append({"code": code, "label": label, "blocking": blocking, "origin": origin})

    if not recipe.code or not recipe.display_name:
        add("identidade", "Identidade incompleta", True, "formulation")
    if not items:
        add("componentes", "Nenhum componente na versão", True, "formulation_item")
    unpublished = 0
    for item in items:
        ingredient = session.get(IngredientVersion, item.ingredient_version_id)
        if ingredient is None or ingredient.status != "published":
            unpublished += 1
    if unpublished:
        add(
            "ingredientes",
            "Há componente com versão de ingrediente não publicada",
            True,
            "ingredient_version",
        )
    if items and total_flour_mass(items) is None:
        add(
            "farinha",
            "Sem farinha-base: percentual do padeiro não se aplica",
            False,
            "formulation_item.is_flour_basis",
        )
    if not steps:
        add("etapas", "Processo sem etapas", True, "process_step")
    if version.yield_units is None and version.target_unit_weight_g is None:
        add("rendimento", "Rendimento ou peso final não informado", False, "formulation_version")
    if nutrition is None:
        add("nutricao", "Prévia nutricional técnica ausente", False, "nutrition_calculation")
    elif getattr(nutrition, "status", None) not in {None, "complete"}:
        add("nutricao", "Prévia nutricional técnica incompleta", False, "nutrition_calculation")
    if not refs:
        add("referencias", "Nenhuma referência associada", False, "recipe_reference")
    if not trials:
        add("trial", "Nenhum ensaio registrado", False, "trial")
    if decision != "approved":
        add("aprovacao", "Aprovação válida mais recente ausente", True, "approval")
    ready = not any(item["blocking"] for item in pending)
    return {
        "ready_to_publish": ready and version.status == "draft",
        "complete_dossier": not pending,
        "latest_decision": decision,
        "items": pending,
    }
