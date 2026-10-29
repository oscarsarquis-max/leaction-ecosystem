"""Isolamento organizacional da camada normal. Sem HTTP."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.nutrition_calculation.models import NutritionCalculation


class NutritionAccessError(ValueError):
    """Cálculo inexistente ou de outra organização."""


def get_nutrition_calculation(
    session: Session,
    organization_id: UUID,
    calculation_id: UUID,
) -> NutritionCalculation:
    row = session.get(NutritionCalculation, calculation_id)
    if row is None or row.organization_id != organization_id:
        raise NutritionAccessError("cálculo nutricional inacessível nesta organização")
    return row
