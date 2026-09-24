from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import ConflictError, NotFoundError, ProductError
from app.domain.money import slugify
from app.models.catalog import DoughType
from app.models.products import Product
from app.models.schedule import RecipeBase


def list_recipe_bases(session: Session, *, include_inactive: bool = False) -> list[RecipeBase]:
    stmt = select(RecipeBase).order_by(RecipeBase.name, RecipeBase.code)
    if not include_inactive:
        stmt = stmt.where(RecipeBase.is_active.is_(True))
    return list(session.scalars(stmt))


def create_recipe_base(session: Session, *, code: str, name: str) -> RecipeBase:
    cleaned_code = _clean_code(code)
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ProductError("informe o nome da receita-base")
    if session.scalar(select(RecipeBase.id).where(RecipeBase.code == cleaned_code)):
        raise ConflictError("já existe uma receita-base com essa referência")
    row = RecipeBase(code=cleaned_code, name=cleaned_name, is_active=True)
    session.add(row)
    session.flush()
    return row


def update_recipe_base(
    session: Session, base_id: UUID, *, code: str, name: str, is_active: bool
) -> RecipeBase:
    row = session.get(RecipeBase, base_id)
    if row is None:
        raise NotFoundError("receita-base não encontrada")
    cleaned_code = _clean_code(code)
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ProductError("informe o nome da receita-base")
    other = session.scalar(
        select(RecipeBase.id).where(RecipeBase.code == cleaned_code, RecipeBase.id != base_id)
    )
    if other is not None:
        raise ConflictError("já existe uma receita-base com essa referência")
    if not is_active:
        linked = int(
            session.scalar(
                select(func.count()).select_from(Product).where(Product.recipe_base_id == base_id)
            )
            or 0
        ) + int(
            session.scalar(
                select(func.count())
                .select_from(DoughType)
                .where(DoughType.recipe_base_id == base_id)
            )
            or 0
        )
        if linked:
            raise ConflictError(
                "esta receita-base ainda está vinculada; remova os vínculos antes de desativar"
            )
    row.code = cleaned_code
    row.name = cleaned_name
    row.is_active = is_active
    session.flush()
    return row


def link_dough_type(
    session: Session, dough_type_id: UUID, recipe_base_id: UUID | None
) -> DoughType:
    dough = session.get(DoughType, dough_type_id)
    if dough is None:
        raise NotFoundError("massa não encontrada")
    if recipe_base_id is not None:
        base = session.get(RecipeBase, recipe_base_id)
        if base is None or not base.is_active:
            raise ProductError("receita-base não encontrada")
    dough.recipe_base_id = recipe_base_id
    session.flush()
    return dough


def _clean_code(code: str) -> str:
    cleaned = slugify(code).upper().replace("_", "-")
    if not cleaned:
        raise ProductError("informe uma referência estável para a receita-base")
    return cleaned[:40]
