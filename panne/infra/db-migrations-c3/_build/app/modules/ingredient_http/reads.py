from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import (
    PERMISSION_COSTING_READ,
    PERMISSION_PROCUREMENT_ORDER_MANAGE,
    PERMISSION_SUPPLIER_PRICE_RECORD,
    Principal,
)
from app.modules.ingredient_catalog.commands import require_read, require_supplier_read
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion
from app.modules.ingredient_catalog.queries import (
    active_item_counts_by_supplier,
    allergens_of,
    catalog_allergens,
    catalog_conversions,
    catalog_nutrients,
    catalog_sources,
    catalog_units,
    completeness_of,
    composition_of,
    get_supplier,
    get_supplier_item,
    items_of_ingredient,
    items_of_supplier,
    latest_prices_of,
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
    load_allergen_enrichments,
    load_ingredient_refs,
    load_item_enrichments,
    load_nutrient_enrichments,
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


def _can_see_purchase_price(principal: Principal) -> bool:
    """Gating alinhado à superfície de compras/custos (não basta supplier.read)."""
    granted = principal.permissions
    return bool(
        {
            PERMISSION_SUPPLIER_PRICE_RECORD,
            PERMISSION_COSTING_READ,
            PERMISSION_PROCUREMENT_ORDER_MANAGE,
        }
        & granted
    )


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


def _dossier_payload(session: Session, identity: Ingredient, version: IngredientVersion) -> dict:
    nutrient_rows = nutrients_of(session, version.id)
    allergen_rows = allergens_of(session, version.id)
    nutrient_map = load_nutrient_enrichments(session, nutrient_rows)
    allergen_map = load_allergen_enrichments(session, allergen_rows)
    return {
        "identity": ingredient_card(identity, version),
        "version": version_out(version),
        "composition": [composition_out(item) for item in composition_of(session, version.id)],
        "nutrients": [
            nutrient_out(
                item,
                nutrient=nutrient_map[item.id][0],
                unit=nutrient_map[item.id][1],
                loq_unit=nutrient_map[item.id][2],
            )
            for item in nutrient_rows
        ],
        "allergens": [
            allergen_out(item, allergen=allergen_map[item.id]) for item in allergen_rows
        ],
        "completeness": completeness_of(session, identity, version),
    }


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
    return versioned(_dossier_payload(session, identity, version), version.row_version)


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
    enrichments = load_item_enrichments(session, organization_id, items)
    include_purchase = _can_see_purchase_price(principal)
    prices = (
        latest_prices_of(session, {item.id for item in items}) if include_purchase else {}
    )
    return {
        "data": [
            item_out(
                item,
                prices.get(item.id),
                unit=enrichments[item.id][0],
                supplier=enrichments[item.id][1],
                include_purchase=include_purchase,
            )
            for item in items
        ]
    }


@router.get("/suppliers")
def get_suppliers(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: str | None = None,
):
    require_supplier_read(principal)
    rows = list_suppliers(session, organization_id, q)
    counts = active_item_counts_by_supplier(
        session, organization_id, {row.id for row in rows}
    )
    return {
        "data": [
            supplier_out(item, active_item_count=counts.get(item.id, 0)) for item in rows
        ]
    }


@router.get("/suppliers/{supplier_id}")
def get_supplier_detail(
    organization_id: UUID,
    supplier_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_supplier_read(principal)
    supplier = _run(lambda: get_supplier(session, organization_id, supplier_id))
    if supplier is None:
        raise_domain(ValidationError("recurso_nao_encontrado"))
    items = items_of_supplier(session, organization_id, supplier_id)
    enrichments = load_item_enrichments(session, organization_id, items)
    ingredients = load_ingredient_refs(session, organization_id, items)
    include_purchase = _can_see_purchase_price(principal)
    prices = (
        latest_prices_of(session, {item.id for item in items}) if include_purchase else {}
    )
    counts = active_item_counts_by_supplier(session, organization_id, {supplier.id})
    return {
        "data": {
            **supplier_out(supplier, active_item_count=counts.get(supplier.id, 0)),
            "items": [
                item_out(
                    item,
                    prices.get(item.id),
                    unit=enrichments[item.id][0],
                    supplier=enrichments[item.id][1],
                    ingredient=ingredients[item.id],
                    include_purchase=include_purchase,
                )
                for item in items
            ],
            "price_access": include_purchase,
        }
    }


@router.get("/items/{item_id}/prices")
def get_prices(
    organization_id: UUID,
    item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_supplier_read(principal)
    item = _run(lambda: get_supplier_item(session, organization_id, item_id))
    if item is None:
        raise_domain(ValidationError("recurso_nao_encontrado"))
    if not _can_see_purchase_price(principal):
        return {"data": [], "price_access": False}
    history = prices_of(session, item_id)
    return {
        "data": [
            price_out(row, is_latest=(index == 0)) for index, row in enumerate(history)
        ],
        "price_access": True,
    }


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
