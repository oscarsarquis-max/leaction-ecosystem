from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.ingredient_catalog.commands import require_read, require_supplier_read
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion
from app.modules.ingredient_catalog.queries import (
    allergens_of,
    catalog_allergens,
    catalog_conversions,
    catalog_nutrients,
    catalog_sources,
    catalog_units,
    completeness_of,
    composition_of,
    items_of_ingredient,
    latest_price,
    list_ingredients,
    list_suppliers,
    nutrients_of,
    prices_of,
    versions_of,
)
from app.modules.ingredient_http.serialize import (
    allergen_def_out,
    allergen_out,
    composition_out,
    conversion_out,
    ingredient_card,
    item_out,
    nutrient_def_out,
    nutrient_out,
    price_out,
    source_out,
    supplier_out,
    unit_out,
    version_out,
    versioned,
)
from app.modules.production_http.deps import get_runtime_principal
from app.modules.production_http.errors import raise_domain
from app.modules.production_planning.errors import ValidationError

router = APIRouter()


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


def _identity(session: Session, organization_id: UUID, ingredient_id: UUID) -> Ingredient:
    row = session.get(Ingredient, ingredient_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _version(
    session: Session, organization_id: UUID, ingredient_id: UUID, version_id: UUID
) -> IngredientVersion:
    row = session.get(IngredientVersion, version_id)
    if row is None or row.organization_id != organization_id or row.ingredient_id != ingredient_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


@router.get("/ingredients")
def get_ingredients(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: str | None = None,
    status: str | None = None,
    version_status: str | None = None,
    allergen_id: UUID | None = None,
    supplier_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    require_read(principal)
    rows, total = _run(
        lambda: list_ingredients(
            session,
            organization_id,
            q=q,
            status=status,
            version_status=version_status,
            allergen_id=allergen_id,
            supplier_id=supplier_id,
            limit=limit,
            offset=offset,
        )
    )
    return {
        "items": [ingredient_card(identity, version) for identity, version in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/ingredients/{ingredient_id}")
def get_ingredient(
    organization_id: UUID,
    ingredient_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, ingredient_id))
    history = versions_of(session, organization_id, ingredient_id)
    latest = history[0] if history else None
    return versioned(
        {
            **ingredient_card(identity, latest),
            "versions": [version_out(item) for item in history],
        },
        identity.row_version,
    )


@router.get("/ingredients/{ingredient_id}/versions")
def get_versions(
    organization_id: UUID,
    ingredient_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _identity(session, organization_id, ingredient_id))
    versions = versions_of(session, organization_id, ingredient_id)
    return {"data": [version_out(item) for item in versions]}


@router.get("/ingredients/{ingredient_id}/versions/{version_id}")
def get_version(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, ingredient_id))
    version = _run(lambda: _version(session, organization_id, ingredient_id, version_id))
    return versioned(
        {
            "identity": ingredient_card(identity, version),
            "version": version_out(version),
            "composition": [composition_out(item) for item in composition_of(session, version.id)],
            "nutrients": [nutrient_out(item) for item in nutrients_of(session, version.id)],
            "allergens": [allergen_out(item) for item in allergens_of(session, version.id)],
            "completeness": completeness_of(session, identity, version),
        },
        version.row_version,
    )


@router.get("/ingredients/{ingredient_id}/versions/{version_id}/completeness")
def get_completeness(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, ingredient_id))
    version = _run(lambda: _version(session, organization_id, ingredient_id, version_id))
    return {"data": completeness_of(session, identity, version)}


@router.get("/ingredients/{ingredient_id}/items")
def get_ingredient_items(
    organization_id: UUID,
    ingredient_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_supplier_read(principal)
    _run(lambda: _identity(session, organization_id, ingredient_id))
    items = items_of_ingredient(session, organization_id, ingredient_id)
    return {"data": [item_out(item, latest_price(session, item.id)) for item in items]}


@router.get("/suppliers")
def get_suppliers(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: str | None = None,
):
    require_supplier_read(principal)
    return {"data": [supplier_out(item) for item in list_suppliers(session, organization_id, q)]}


@router.get("/items/{item_id}/prices")
def get_prices(
    organization_id: UUID,
    item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_supplier_read(principal)
    return {"data": [price_out(item) for item in prices_of(session, item_id)]}


@router.get("/catalog/units")
def get_units(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    return {
        "data": [unit_out(item) for item in catalog_units(session)],
        "conversions": [conversion_out(item) for item in catalog_conversions(session)],
    }


@router.get("/catalog/nutrients")
def get_nutrient_catalog(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    return {"data": [nutrient_def_out(item) for item in catalog_nutrients(session)]}


@router.get("/catalog/allergens")
def get_allergen_catalog(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    return {"data": [allergen_def_out(item) for item in catalog_allergens(session)]}


@router.get("/catalog/sources")
def get_source_catalog(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    return {"data": [source_out(item) for item in catalog_sources(session)]}
