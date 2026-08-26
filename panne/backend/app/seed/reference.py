"""Catálogos canônicos. Idempotente. Sem dados demonstrativos."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import Allergen, MeasurementUnit, NutrientDefinition

UNITS = (
    ("g", "grama", "gramas", "mass", "0.001", "g"),
    ("kg", "quilograma", "quilogramas", "mass", "1", "kg"),
    ("ml", "mililitro", "mililitros", "volume", "0.000001", "ml"),
    ("l", "litro", "litros", "volume", "0.001", "l"),
    ("un", "unidade", "unidades", "count", "1", "un"),
)

NUTRIENTS = (
    ("energy_kcal", "Energia", "g", "energy"),
    ("protein", "Proteína", "g", "macro"),
    ("carbohydrate", "Carboidrato", "g", "macro"),
    ("total_fat", "Gorduras totais", "g", "macro"),
    ("saturated_fat", "Gorduras saturadas", "g", "macro"),
    ("sodium", "Sódio", "g", "mineral"),
    ("fiber", "Fibra alimentar", "g", "macro"),
    ("sugars", "Açúcares", "g", "macro"),
)

ALLERGENS = (
    ("gluten", "Glúten"),
    ("milk", "Leite"),
    ("egg", "Ovo"),
    ("soy", "Soja"),
    ("sesame", "Gergelim"),
)


def seed_reference(session: Session) -> dict[str, int]:
    created = {"units": 0, "nutrients": 0, "allergens": 0}
    units: dict[str, MeasurementUnit] = {}
    for code, name, plural, dimension, factor, symbol in UNITS:
        row = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == code))
        if row is None:
            row = MeasurementUnit(
                code=code,
                name=name,
                plural_name=plural,
                dimension=dimension,
                si_factor=Decimal(factor),
                symbol=symbol,
                status="active",
            )
            session.add(row)
            session.flush()
            created["units"] += 1
        units[code] = row
    for code, name, unit_code, group in NUTRIENTS:
        row = session.scalar(select(NutrientDefinition).where(NutrientDefinition.code == code))
        if row is None:
            session.add(
                NutrientDefinition(
                    code=code,
                    name=name,
                    unit_id=units[unit_code].id,
                    group_code=group,
                    status="active",
                )
            )
            created["nutrients"] += 1
    for code, name in ALLERGENS:
        row = session.scalar(select(Allergen).where(Allergen.code == code))
        if row is None:
            session.add(Allergen(code=code, name=name, status="active"))
            created["allergens"] += 1
    session.flush()
    return created
