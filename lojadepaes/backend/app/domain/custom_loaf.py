from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ConfirmationError, NotFoundError
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.models.schedule import RecipeBase
from app.models.catalog import (
    BreadShape,
    DoughIngredientCompatibility,
    DoughShapeCompatibility,
    DoughType,
    Ingredient,
)


RETIRED_DOUGH_SLUGS = ("sourdough-classico", "integral", "multigraos")

CREATOR_PREPARATIONS = (
    (
        "fermentacao-natural-curta",
        "Fermentação natural curta (Classic sourdough)",
        "Massa de fermentação natural, de preparo mais curto.",
        "FERMENTACAO-NATURAL-CURTA",
    ),
    (
        "maturada",
        "Maturada (Long fermentation)",
        "Massa que descansa mais tempo antes de assar.",
        "MATURADA",
    ),
    (
        "sovada",
        "Sovada (Kneaded dough)",
        "Massa trabalhada à mão, de miolo mais regular.",
        "SOVADA",
    ),
)

ASSISTANT_SHAPES = (
    ("rustico-de-cesto", "Rústico de cesto", "Crosta marcante, desenho de farinha e fatias generosas."),
    ("pao-de-forma", "Pão de forma", "Topo abaulado e fatias regulares para os seus rituais."),
)

ITALIAN_FLOUR_SLUG = "farinha-branca-italiana"
ITALIAN_FLOUR_PUBLIC_DESCRIPTION = "Farinha branca de origem italiana, para uma massa mais clara."
CREATOR_FLOURS = (
    ("farinha-branca-strong-white", "Branca (Strong white)", "Farinha branca de trigo."),
    ("farinha-integral-trigo", "Integral de trigo (Whole wheat)", "Farinha de trigo integral."),
    ("farinha-integral-centeio", "Integral de centeio (Whole rye)", "Farinha de centeio integral."),
    ("farinha-fuba", "Fubá (Corn)", "Farinha de milho."),
)
ASSISTANT_INCLUSIONS = (
    ("nozes", "Nozes", "Crocância delicada na fatia."),
    ("castanha-de-caju", "Castanha de caju", "Sabor amanteigado e textura macia."),
    ("granola", "Granola", "Crocância de cereais e um toque adocicado."),
    ("tomate-seco", "Tomate seco", "Acidez e doçura concentradas."),
    ("berinjela", "Berinjela", "Sabor suave e miolo mais úmido."),
    ("queijo-parmesao", "Queijo parmesão", "Salgado e aromático no miolo."),
)

PREP_REVIEW_MESSAGE = (
    "O preparo desta seleção não está mais disponível. Revise só a fermentação e o preparo; "
    "farinha, complementos e texto livre foram mantidos."
)
FLOUR_REVIEW_MESSAGE = (
    "A farinha desta seleção não está mais disponível. Revise só a farinha; "
    "o preparo, os complementos e o texto livre foram mantidos."
)


def _recipe_base(session: Session, code: str, name: str) -> RecipeBase:
    row = session.scalar(select(RecipeBase).where(RecipeBase.code == code))
    if row is not None:
        return row
    return create_recipe_base(session, code=code, name=name)


def ensure_assistant_choices(session: Session) -> None:
    """Farinha e fermentação/preparo são escolhas independentes do criador."""
    for slug in RETIRED_DOUGH_SLUGS:
        dough = session.scalar(select(DoughType).where(DoughType.slug == slug))
        if dough is None:
            continue
        dough.creator_kind = "retired_mass"
        if dough.is_active:
            dough.is_active = False
    doughs: list[DoughType] = []
    for index, (slug, name, description, base_code) in enumerate(CREATOR_PREPARATIONS):
        dough = session.scalar(select(DoughType).where(DoughType.slug == slug))
        base = _recipe_base(session, base_code, name)
        if dough is None:
            dough = DoughType(
                name=name,
                slug=slug,
                short_description=description,
                sort_order=index,
                is_active=True,
                creator_kind="preparation",
                recipe_base_id=base.id,
            )
            session.add(dough)
            session.flush()
        else:
            dough.creator_kind = "preparation"
            if dough.recipe_base_id is None:
                dough.recipe_base_id = base.id
        doughs.append(dough)
    shapes: list[BreadShape] = []
    for index, (slug, name, description) in enumerate(ASSISTANT_SHAPES):
        shape = session.scalar(select(BreadShape).where(BreadShape.slug == slug))
        if shape is None:
            shape = BreadShape(
                name=name,
                slug=slug,
                description=description,
                crust_crumb_notes=description,
                sort_order=index,
                is_active=True,
            )
            session.add(shape)
            session.flush()
        shapes.append(shape)
    for dough in doughs:
        for shape in shapes:
            exists = session.scalar(
                select(DoughShapeCompatibility.id).where(
                    DoughShapeCompatibility.dough_type_id == dough.id,
                    DoughShapeCompatibility.bread_shape_id == shape.id,
                )
            )
            if exists is None:
                session.add(
                    DoughShapeCompatibility(dough_type_id=dough.id, bread_shape_id=shape.id)
                )
    session.flush()
    _ensure_flour_and_inclusions(session)


def _ensure_flour_and_inclusions(session: Session) -> None:
    italian = session.scalar(select(Ingredient).where(Ingredient.slug == ITALIAN_FLOUR_SLUG))
    if italian is None:
        session.add(
            Ingredient(
                name="Farinha branca italiana",
                slug=ITALIAN_FLOUR_SLUG,
                description=ITALIAN_FLOUR_PUBLIC_DESCRIPTION,
                sort_order=0,
                is_active=False,
                surcharge_cents=None,
                assistant_role="flour",
            )
        )
    else:
        italian.assistant_role = "flour"
        if italian.is_active:
            italian.is_active = False
        if "pendentes de configuração" in (italian.description or ""):
            italian.description = ITALIAN_FLOUR_PUBLIC_DESCRIPTION
    for index, (slug, name, description) in enumerate(CREATOR_FLOURS):
        row = session.scalar(select(Ingredient).where(Ingredient.slug == slug))
        if row is None:
            session.add(
                Ingredient(
                    name=name,
                    slug=slug,
                    description=description,
                    sort_order=index + 1,
                    is_active=True,
                    surcharge_cents=None,
                    assistant_role="flour",
                )
            )
            continue
        row.assistant_role = "flour"
    for index, (slug, name, description) in enumerate(ASSISTANT_INCLUSIONS):
        row = session.scalar(select(Ingredient).where(Ingredient.slug == slug))
        if row is None:
            session.add(
                Ingredient(
                    name=name,
                    slug=slug,
                    description=description,
                    sort_order=index + 1,
                    is_active=True,
                    surcharge_cents=None,
                    assistant_role="inclusion",
                )
            )
            continue
        if row.assistant_role != "flour":
            row.assistant_role = "inclusion"
        if not row.is_active:
            row.is_active = True
    session.flush()


def _public_ingredient(ingredient: Ingredient, compatible: list[str]) -> dict:
    return {
        "id": str(ingredient.id),
        "name": ingredient.name,
        "description": ingredient.description,
        "assistant_role": ingredient.assistant_role,
        "compatible_dough_ids": compatible,
        "compatibility_pending": not compatible,
    }


def public_builder_catalog(session: Session) -> dict:
    ensure_assistant_choices(session)
    settings = ensure_schedule_settings(session)
    doughs = list(
        session.scalars(
            select(DoughType)
            .where(DoughType.is_active.is_(True), DoughType.creator_kind == "preparation")
            .order_by(DoughType.sort_order, DoughType.name)
        )
    )
    ingredients = list(
        session.scalars(select(Ingredient).where(Ingredient.is_active.is_(True)).order_by(Ingredient.sort_order, Ingredient.name))
    )
    shapes = list(
        session.scalars(select(BreadShape).where(BreadShape.is_active.is_(True)).order_by(BreadShape.sort_order, BreadShape.name))
    )
    ingredient_links = list(session.scalars(select(DoughIngredientCompatibility)))
    shape_links = list(session.scalars(select(DoughShapeCompatibility)))
    ingredient_map: dict[UUID, list[str]] = {}
    for row in ingredient_links:
        ingredient_map.setdefault(row.ingredient_id, []).append(str(row.dough_type_id))
    shape_map: dict[UUID, list[str]] = {}
    for row in shape_links:
        shape_map.setdefault(row.bread_shape_id, []).append(str(row.dough_type_id))
    return {
        "price_cents": settings.custom_loaf_price_cents,
        "weight_grams": settings.custom_loaf_weight_grams,
        "currency": "BRL",
        "fulfillment": "pickup",
        "doughs": [
            {
                "id": str(dough.id),
                "name": dough.name,
                "description": dough.short_description,
                "recipe_base_pending": dough.recipe_base_id is None,
            }
            for dough in doughs
        ],
        "flours": [
            _public_ingredient(ingredient, ingredient_map.get(ingredient.id, []))
            for ingredient in ingredients
            if ingredient.assistant_role == "flour"
        ],
        "ingredients": [
            _public_ingredient(ingredient, ingredient_map.get(ingredient.id, []))
            for ingredient in ingredients
            if ingredient.assistant_role != "flour"
        ],
        "shapes": [
            {
                "id": str(shape.id),
                "name": shape.name,
                "description": shape.description,
                "compatible_dough_ids": shape_map.get(shape.id, []),
                "compatibility_pending": not shape_map.get(shape.id),
            }
            for shape in shapes
        ],
    }


def validate_public_custom_choices(
    dough: DoughType | None,
    ingredients: list[Ingredient],
) -> None:
    if dough is None:
        raise ConfirmationError("informe a fermentação e o preparo da massa")
    if dough.creator_kind == "retired_mass" or (
        dough.creator_kind == "preparation" and not dough.is_active
    ):
        raise ConfirmationError(PREP_REVIEW_MESSAGE)
    if dough.creator_kind == "preparation":
        flours = [item for item in ingredients if item.assistant_role == "flour"]
        inactive = [item for item in flours if not item.is_active]
        active = [item for item in flours if item.is_active]
        if inactive and not active:
            raise ConfirmationError(FLOUR_REVIEW_MESSAGE)
        if not active:
            raise ConfirmationError("informe a farinha e como vamos preparar a massa")
        if len(active) > 1:
            raise ConfirmationError("escolha uma farinha")


def update_custom_loaf_price(session: Session, price_cents: int, weight_grams: int) -> dict:
    if price_cents <= 0 or weight_grams <= 0:
        raise ConfirmationError("informe preço e peso maiores que zero")
    row = ensure_schedule_settings(session)
    row.custom_loaf_price_cents = price_cents
    row.custom_loaf_weight_grams = weight_grams
    session.flush()
    return {"price_cents": row.custom_loaf_price_cents, "weight_grams": row.custom_loaf_weight_grams}


def list_ingredients(session: Session) -> list[dict]:
    rows = list(session.scalars(select(Ingredient).order_by(Ingredient.sort_order, Ingredient.name)))
    links = list(session.scalars(select(DoughIngredientCompatibility)))
    by_ingredient: dict[UUID, list[str]] = {}
    for row in links:
        by_ingredient.setdefault(row.ingredient_id, []).append(str(row.dough_type_id))
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "is_active": row.is_active,
            "surcharge_cents": row.surcharge_cents,
            "surcharge_pending": row.surcharge_cents is None,
            "assistant_role": row.assistant_role,
            "compatible_dough_ids": by_ingredient.get(row.id, []),
            "admin_note": (
                "Propriedades, alergênicos e compatibilidades ainda pendentes de revisão."
                if row.assistant_role == "flour"
                else None
            ),
        }
        for row in rows
    ]


def update_ingredient(session: Session, ingredient_id: UUID, payload: dict) -> dict:
    row = session.get(Ingredient, ingredient_id)
    if row is None:
        raise NotFoundError("ingrediente não encontrado")
    name = str(payload.get("name") or "").strip()
    description = str(payload.get("description") or "").strip()
    if not name or len(name) > 120:
        raise ConfirmationError("informe o nome do ingrediente")
    if not description or len(description) > 280:
        raise ConfirmationError("informe a descrição do ingrediente")
    row.name = name
    row.description = description
    row.is_active = bool(payload.get("is_active", True))
    dough_ids = payload.get("compatible_dough_ids")
    if isinstance(dough_ids, list):
        existing = list(
            session.scalars(
                select(DoughIngredientCompatibility).where(
                    DoughIngredientCompatibility.ingredient_id == row.id
                )
            )
        )
        for link in existing:
            session.delete(link)
        session.flush()
        for raw in dough_ids:
            dough = session.get(DoughType, UUID(str(raw)))
            if dough is None:
                raise ConfirmationError("massa informada não existe")
            session.add(DoughIngredientCompatibility(dough_type_id=dough.id, ingredient_id=row.id))
    session.flush()
    return {"id": str(row.id), "name": row.name, "is_active": row.is_active}
