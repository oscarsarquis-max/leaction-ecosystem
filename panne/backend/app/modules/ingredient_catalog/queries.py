from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.completeness import project_completeness
from app.modules.ingredient_catalog.models import (
    Allergen,
    DataSource,
    Ingredient,
    IngredientAllergen,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
    UnitConversion,
)


def list_ingredients(
    session: Session,
    organization_id: UUID,
    *,
    q: str | None,
    status: str | None,
    version_status: str | None,
    allergen_id: UUID | None,
    supplier_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Ingredient, IngredientVersion | None]], int]:
    query = (
        select(Ingredient)
        .where(Ingredient.organization_id == organization_id)
        .order_by(Ingredient.display_name, Ingredient.code)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(Ingredient.display_name.ilike(pattern), Ingredient.code.ilike(pattern))
        )
    if status:
        query = query.where(Ingredient.status == status)
    if version_status:
        query = query.join(
            IngredientVersion,
            (IngredientVersion.ingredient_id == Ingredient.id)
            & (IngredientVersion.status == version_status),
        )
    if allergen_id:
        query = (
            query.join(IngredientVersion, IngredientVersion.ingredient_id == Ingredient.id)
            .join(
                IngredientAllergen,
                IngredientAllergen.ingredient_version_id == IngredientVersion.id,
            )
            .where(IngredientAllergen.allergen_id == allergen_id)
        )
    if supplier_id:
        query = query.join(SupplierItem, SupplierItem.ingredient_id == Ingredient.id).where(
            SupplierItem.supplier_id == supplier_id
        )
    total = session.scalar(select(func.count()).select_from(query.distinct().subquery())) or 0
    identities = session.scalars(query.distinct().offset(offset).limit(limit)).all()
    rows: list[tuple[Ingredient, IngredientVersion | None]] = []
    for identity in identities:
        version = session.scalar(
            select(IngredientVersion).where(
                IngredientVersion.ingredient_id == identity.id,
                IngredientVersion.status == "published",
            )
        )
        if version is None:
            version = session.scalar(
                select(IngredientVersion)
                .where(IngredientVersion.ingredient_id == identity.id)
                .order_by(IngredientVersion.version_number.desc())
            )
        rows.append((identity, version))
    return rows, total


def versions_of(
    session: Session, organization_id: UUID, ingredient_id: UUID
) -> list[IngredientVersion]:
    return list(
        session.scalars(
            select(IngredientVersion)
            .where(
                IngredientVersion.organization_id == organization_id,
                IngredientVersion.ingredient_id == ingredient_id,
            )
            .order_by(IngredientVersion.version_number.desc())
        )
    )


def composition_of(session: Session, version_id: UUID) -> list[IngredientComposition]:
    return list(
        session.scalars(
            select(IngredientComposition)
            .where(IngredientComposition.parent_ingredient_version_id == version_id)
            .order_by(IngredientComposition.sequence)
        )
    )


def nutrients_of(session: Session, version_id: UUID) -> list[IngredientNutrient]:
    return list(
        session.scalars(
            select(IngredientNutrient).where(IngredientNutrient.ingredient_version_id == version_id)
        )
    )


def allergens_of(session: Session, version_id: UUID) -> list[IngredientAllergen]:
    return list(
        session.scalars(
            select(IngredientAllergen).where(IngredientAllergen.ingredient_version_id == version_id)
        )
    )


def items_of_ingredient(
    session: Session, organization_id: UUID, ingredient_id: UUID
) -> list[SupplierItem]:
    return list(
        session.scalars(
            select(SupplierItem).where(
                SupplierItem.organization_id == organization_id,
                SupplierItem.ingredient_id == ingredient_id,
            )
        )
    )


def latest_price(session: Session, item_id: UUID) -> SupplierItemPrice | None:
    return session.scalar(
        select(SupplierItemPrice)
        .where(SupplierItemPrice.supplier_item_id == item_id)
        .order_by(SupplierItemPrice.observed_at.desc(), SupplierItemPrice.created_at.desc())
    )


def prices_of(session: Session, item_id: UUID) -> list[SupplierItemPrice]:
    return list(
        session.scalars(
            select(SupplierItemPrice)
            .where(SupplierItemPrice.supplier_item_id == item_id)
            .order_by(SupplierItemPrice.observed_at.desc())
        )
    )


def list_suppliers(session: Session, organization_id: UUID, q: str | None) -> list[Supplier]:
    query = (
        select(Supplier)
        .where(Supplier.organization_id == organization_id)
        .order_by(Supplier.display_name)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Supplier.display_name.ilike(pattern), Supplier.code.ilike(pattern)))
    return list(session.scalars(query))


def catalog_units(session: Session) -> list[MeasurementUnit]:
    return list(
        session.scalars(
            select(MeasurementUnit)
            .where(MeasurementUnit.status == "active")
            .order_by(MeasurementUnit.code)
        )
    )


def catalog_conversions(session: Session) -> list[UnitConversion]:
    return list(session.scalars(select(UnitConversion).where(UnitConversion.status == "active")))


def catalog_nutrients(session: Session) -> list[NutrientDefinition]:
    return list(
        session.scalars(
            select(NutrientDefinition)
            .where(NutrientDefinition.status == "active")
            .order_by(NutrientDefinition.name)
        )
    )


def catalog_allergens(session: Session) -> list[Allergen]:
    return list(
        session.scalars(select(Allergen).where(Allergen.status == "active").order_by(Allergen.name))
    )


def catalog_sources(session: Session) -> list[DataSource]:
    return list(
        session.scalars(
            select(DataSource).where(DataSource.status == "active").order_by(DataSource.title)
        )
    )


def completeness_of(session: Session, identity: Ingredient, version: IngredientVersion) -> dict:
    return project_completeness(session, identity, version)
