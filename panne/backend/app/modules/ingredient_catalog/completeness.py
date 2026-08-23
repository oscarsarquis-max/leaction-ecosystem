"""Projeção determinística de completude. Não declara conformidade."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import (
    Ingredient,
    IngredientAllergen,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    SupplierItem,
)

COMPLETE_NUTRIENT = {"measured", "known_zero"}


@dataclass(frozen=True)
class CompletenessItem:
    code: str
    label: str
    blocking: bool
    origin: str


def project_completeness(
    session: Session, identity: Ingredient, version: IngredientVersion
) -> dict:
    items: list[CompletenessItem] = []
    if not identity.code.strip() or not identity.display_name.strip():
        items.append(
            CompletenessItem(
                "identificacao",
                "Código e nome são obrigatórios.",
                True,
                "ingredient.code / ingredient.display_name",
            )
        )
    if identity.status != "active":
        items.append(
            CompletenessItem(
                "identidade_inativa",
                "Identidade inativa não pode publicar nova versão.",
                True,
                "ingredient.status",
            )
        )
    if version.nutrition_basis_type != "per_100g" or version.nutrition_basis_quantity != 100:
        items.append(
            CompletenessItem(
                "base_nutricional",
                "A base nutricional deve ser 100 g.",
                True,
                "ingredient_version.nutrition_basis_*",
            )
        )
    composition = session.scalars(
        select(IngredientComposition).where(
            IngredientComposition.parent_ingredient_version_id == version.id
        )
    ).all()
    if identity.ingredient_type in {"composite", "preparation"} and not composition:
        items.append(
            CompletenessItem(
                "composicao",
                "Composto ou preparação precisa de ao menos um constituinte.",
                True,
                "ingredient_composition",
            )
        )
    nutrients = session.scalars(
        select(IngredientNutrient).where(IngredientNutrient.ingredient_version_id == version.id)
    ).all()
    if not nutrients:
        items.append(
            CompletenessItem(
                "nutricao",
                "Nenhum nutriente declarado por 100 g.",
                False,
                "ingredient_nutrient",
            )
        )
    elif not any(row.value_status in COMPLETE_NUTRIENT for row in nutrients):
        items.append(
            CompletenessItem(
                "nutricao_incompleta",
                "Há nutrição, mas nenhum valor medido ou zero conhecido.",
                False,
                "ingredient_nutrient.value_status",
            )
        )
    if any(row.value_status == "below_loq" for row in nutrients):
        items.append(
            CompletenessItem(
                "nutricao_loq",
                "Há valor abaixo do LQ; ausência não foi convertida em zero.",
                False,
                "ingredient_nutrient.value_status=below_loq",
            )
        )
    allergens = session.scalars(
        select(IngredientAllergen).where(IngredientAllergen.ingredient_version_id == version.id)
    ).all()
    if not allergens:
        items.append(
            CompletenessItem(
                "alergenico_pendente",
                "Nenhum alergênico declarado. A revisão humana permanece pendente.",
                False,
                "ingredient_allergen",
            )
        )
    if version.data_source_id is None:
        items.append(
            CompletenessItem(
                "fonte_pendente",
                "Versão sem fonte técnica associada.",
                False,
                "ingredient_version.data_source_id",
            )
        )
    suppliers = session.scalars(
        select(SupplierItem).where(
            SupplierItem.ingredient_id == identity.id,
            SupplierItem.status == "active",
        )
    ).all()
    if not suppliers:
        items.append(
            CompletenessItem(
                "fornecedor",
                "Nenhum item de fornecedor ativo. Não bloqueia publicação.",
                False,
                "supplier_item",
            )
        )
    blockers = [item for item in items if item.blocking]
    return {
        "ready_to_publish": not blockers,
        "complete_dossier": not items,
        "items": [
            {
                "code": item.code,
                "label": item.label,
                "blocking": item.blocking,
                "origin": item.origin,
            }
            for item in items
        ],
    }
