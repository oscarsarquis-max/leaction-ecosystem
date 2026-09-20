from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ConfirmationError
from app.models.catalog import (
    BreadShape,
    DoughIngredientCompatibility,
    DoughShapeCompatibility,
    DoughType,
    Ingredient,
)
from app.models.orders import OrderItem, OrderItemIngredient


def assert_item_sellable(
    session: Session, item: OrderItem
) -> tuple[DoughType, BreadShape, list[Ingredient]]:
    dough = session.get(DoughType, item.dough_type_id)
    shape = session.get(BreadShape, item.bread_shape_id)
    if dough is None or shape is None:
        raise ConfirmationError("catálogo referenciado não encontrado")
    if not dough.is_active or not shape.is_active:
        raise ConfirmationError("massa ou formato inativo")
    shape_ok = session.scalar(
        select(DoughShapeCompatibility.id).where(
            DoughShapeCompatibility.dough_type_id == dough.id,
            DoughShapeCompatibility.bread_shape_id == shape.id,
        )
    )
    if shape_ok is None:
        raise ConfirmationError("formato não autorizado para a massa")
    extras = session.scalars(
        select(OrderItemIngredient).where(OrderItemIngredient.order_item_id == item.id)
    ).all()
    ingredients: list[Ingredient] = []
    seen: set[UUID] = set()
    for extra in extras:
        if extra.ingredient_id in seen:
            raise ConfirmationError("ingrediente duplicado no item")
        seen.add(extra.ingredient_id)
        ingredient = session.get(Ingredient, extra.ingredient_id)
        if ingredient is None or not ingredient.is_active:
            raise ConfirmationError("inclusão inativa ou inexistente")
        compat = session.scalar(
            select(DoughIngredientCompatibility.id).where(
                DoughIngredientCompatibility.dough_type_id == dough.id,
                DoughIngredientCompatibility.ingredient_id == ingredient.id,
            )
        )
        if compat is None:
            raise ConfirmationError("inclusão não autorizada para a massa")
        ingredients.append(ingredient)
    return dough, shape, ingredients
