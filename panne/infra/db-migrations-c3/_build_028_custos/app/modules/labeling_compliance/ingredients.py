"""Lista candidata de ingredientes a partir do snapshot da formulação."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import FormulationItem
from app.modules.ingredient_catalog.models import (
    Ingredient,
    IngredientComposition,
    IngredientVersion,
)


def candidate_ingredients(session: Session, formulation_version_id) -> list[dict]:
    items = list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == formulation_version_id)
            .order_by(FormulationItem.net_quantity.desc(), FormulationItem.sequence)
        )
    )
    rows = []
    for index, item in enumerate(items, start=1):
        version = session.get(IngredientVersion, item.ingredient_version_id)
        ingredient = None if version is None else session.get(Ingredient, version.ingredient_id)
        components = []
        gap = None
        compound = False
        if ingredient is not None and ingredient.ingredient_type == "composite":
            compound = True
            parts = list(
                session.scalars(
                    select(IngredientComposition)
                    .where(IngredientComposition.parent_ingredient_version_id == version.id)
                    .order_by(IngredientComposition.sequence)
                )
            )
            if not parts:
                gap = "Ingrediente composto sem componentes conhecidos."
            for part in parts:
                child = session.get(IngredientVersion, part.component_ingredient_version_id)
                child_id = None if child is None else session.get(Ingredient, child.ingredient_id)
                components.append(
                    {
                        "ingredient_version_id": str(part.component_ingredient_version_id),
                        "name": None if child_id is None else child_id.display_name,
                        "quantity": format(part.quantity, "f"),
                    }
                )
        rows.append(
            {
                "sequence": index,
                "display_name": "Componente não identificado" if ingredient is None else ingredient.display_name,
                "ingredient_version_id": item.ingredient_version_id,
                "net_quantity_g": item.net_quantity,
                "compound": compound,
                "components": components,
                "gap": gap,
            }
        )
    return rows
