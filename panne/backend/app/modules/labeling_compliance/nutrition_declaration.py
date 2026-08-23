"""Projeção regulatória. Não altera o cálculo técnico."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import NutrientDefinition
from app.modules.labeling_compliance.constants import MANDATORY_NUTRIENTS
from app.modules.labeling_compliance.portions import get_portion
from app.modules.labeling_compliance.rounding import daily_value_percent, round_declared
from app.modules.nutrition_calculation.models import NutritionCalculation, NutritionCalculationItem


def load_technical_per_100g(session: Session, calculation: NutritionCalculation | None) -> dict:
    if calculation is None:
        return {}
    items = list(
        session.scalars(
            select(NutritionCalculationItem).where(
                NutritionCalculationItem.nutrition_calculation_id == calculation.id
            )
        )
    )
    if not items:
        return {}
    nutrients = {
        row.id: row
        for row in session.scalars(
            select(NutrientDefinition).where(
                NutrientDefinition.id.in_([item.nutrient_definition_id for item in items])
            )
        )
    }
    by_code: dict[str, NutritionCalculationItem] = {}
    for item in items:
        nutrient = nutrients.get(item.nutrient_definition_id)
        if nutrient is None:
            continue
        by_code[nutrient.code] = item
    return by_code


def project_declaration(
    session: Session,
    calculation: NutritionCalculation | None,
    *,
    category_code: str | None,
    servings: int | None,
) -> list[dict]:
    by_code = load_technical_per_100g(session, calculation)
    portion = get_portion(category_code)
    portion_g = None if portion is None else portion["reference_g"]
    lines = []
    for code in MANDATORY_NUTRIENTS:
        item = by_code.get(code)
        technical = None if item is None else item.per_100g_amount
        complete = (
            item is not None
            and item.completeness_status == "complete"
            and technical is not None
        )
        if not complete:
            lines.append(
                {
                    "nutrient_code": code,
                    "technical_per_100g": technical,
                    "regulatory_per_100g": None,
                    "declared_per_100g": None,
                    "declared_per_serving": None,
                    "daily_value_percent": None,
                    "completeness": "insufficient_evidence",
                    "presented": None,
                }
            )
            continue
        declared_100 = round_declared(code, technical)
        declared_serving = None
        if portion_g is not None:
            declared_serving = round_declared(code, technical * portion_g / Decimal("100"))
        lines.append(
            {
                "nutrient_code": code,
                "technical_per_100g": technical,
                "regulatory_per_100g": declared_100,
                "declared_per_100g": declared_100,
                "declared_per_serving": declared_serving,
                "daily_value_percent": daily_value_percent(code, declared_100),
                "completeness": "complete",
                "presented": format(declared_100, "f"),
            }
        )
    return lines
