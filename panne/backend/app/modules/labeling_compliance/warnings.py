"""Advertências candidatas. Sem conclusão inventada pela IA."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import FormulationItem
from app.modules.ingredient_catalog.models import Allergen, IngredientAllergen, IngredientVersion


def candidate_warnings(session: Session, formulation_version_id) -> list[dict]:
    items = list(
        session.scalars(
            select(FormulationItem).where(
                FormulationItem.formulation_version_id == formulation_version_id
            )
        )
    )
    contains: dict[str, list[str]] = {}
    for item in items:
        rows = list(
            session.scalars(
                select(IngredientAllergen).where(
                    IngredientAllergen.ingredient_version_id == item.ingredient_version_id
                )
            )
        )
        for row in rows:
            allergen = session.get(Allergen, row.allergen_id)
            code = "desconhecido" if allergen is None else allergen.code
            if row.presence == "contains":
                contains.setdefault(code, []).append(str(item.ingredient_version_id))
    warnings = []
    if "gluten" in contains or "glúten" in contains:
        warnings.append(
            {
                "code": "gluten_contains",
                "kind": "gluten",
                "statement": "contém Glúten",
                "result": "manual_review_required",
                "evidence": {"ingredient_version_ids": contains.get("gluten") or contains.get("glúten")},
            }
        )
    else:
        warnings.append(
            {
                "code": "gluten_unknown",
                "kind": "gluten",
                "statement": "Declaração de glúten pendente. Ausência na fórmula não prova ausência.",
                "result": "insufficient_evidence",
                "evidence": {},
            }
        )
    for code, versions in contains.items():
        if code in {"gluten", "glúten"}:
            continue
        warnings.append(
            {
                "code": f"allergen_{code}",
                "kind": "allergen",
                "statement": f"CONTÉM {code}",
                "result": "manual_review_required",
                "evidence": {"ingredient_version_ids": versions},
            }
        )
    warnings.append(
        {
            "code": "may_contain",
            "kind": "cross_contact",
            "statement": "PODE CONTER exige evidência de processo ou instalações.",
            "result": "insufficient_evidence",
            "evidence": {},
        }
    )
    warnings.append(
        {
            "code": "lactose",
            "kind": "lactose",
            "statement": "Lactose sem evidência suficiente.",
            "result": "insufficient_evidence",
            "evidence": {},
        }
    )
    return warnings
