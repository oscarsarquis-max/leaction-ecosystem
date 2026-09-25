"""Código interno de ingrediente: ING-000001 por organização.

A unicidade vale no insert. O preview não reserva. Fechar o diálogo não incrementa.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import Ingredient, IngredientCodeCounter

CODE_PREFIX = "ING"
CODE_WIDTH = 6


def format_ingredient_code(value: int) -> str:
    return f"{CODE_PREFIX}-{int(value):0{CODE_WIDTH}d}"


def _used(session: Session, organization_id, code: str) -> bool:
    return (
        session.scalar(
            select(func.count())
            .select_from(Ingredient)
            .where(Ingredient.organization_id == organization_id, func.lower(Ingredient.code) == code.casefold())
        )
        or 0
    ) > 0


def peek_suggested_code(session: Session, organization_id) -> str:
    counter = session.scalar(
        select(IngredientCodeCounter).where(IngredientCodeCounter.organization_id == organization_id)
    )
    start = int(counter.last_value) + 1 if counter is not None else 1
    candidate = start
    while candidate < start + 10000:
        code = format_ingredient_code(candidate)
        if not _used(session, organization_id, code):
            return code
        candidate += 1
    return format_ingredient_code(candidate)


def allocate_ingredient_code(session: Session, organization_id) -> str:
    counter = session.scalar(
        select(IngredientCodeCounter)
        .where(IngredientCodeCounter.organization_id == organization_id)
        .with_for_update()
    )
    if counter is None:
        from sqlalchemy.exc import IntegrityError

        try:
            with session.begin_nested():
                session.add(IngredientCodeCounter(organization_id=organization_id, last_value=0))
                session.flush()
        except IntegrityError:
            pass
        counter = session.scalar(
            select(IngredientCodeCounter)
            .where(IngredientCodeCounter.organization_id == organization_id)
            .with_for_update()
        )
    if counter is None:
        raise RuntimeError("ingredient_code_counter_missing")
    while True:
        counter.last_value = int(counter.last_value) + 1
        code = format_ingredient_code(counter.last_value)
        if not _used(session, organization_id, code):
            return code
