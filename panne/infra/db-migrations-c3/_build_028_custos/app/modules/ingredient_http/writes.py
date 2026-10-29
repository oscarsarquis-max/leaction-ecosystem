from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.ingredient_catalog.commands import (
    create_ingredient,
    create_supplier,
    create_supplier_item,
    create_version,
    publish_version,
    record_price,
    remove_composition,
    retire_version,
    update_draft,
    update_identity,
    update_supplier,
    upsert_allergen,
    upsert_composition,
    upsert_nutrient,
)
from app.modules.ingredient_catalog.models import IngredientVersion
from app.modules.ingredient_http.schemas import (
    AllergenWrite,
    CompositionWrite,
    DraftPatch,
    IdentityPatch,
    IngredientCreate,
    NutrientWrite,
    PriceWrite,
    SupplierCreate,
    SupplierItemCreate,
    SupplierPatch,
    VersionCreate,
)
from app.modules.ingredient_http.serialize import (
    allergen_out,
    composition_out,
    ingredient_card,
    item_out,
    nutrient_out,
    price_out,
    supplier_out,
    version_out,
    versioned,
)
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain

router = APIRouter()


def _keys(idempotency_key: str | None, x_correlation_id: str | None, if_match: str | None = None):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key), parse_if_match(if_match, required=False)


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


@router.post("/ingredients")
def post_ingredient(
    organization_id: UUID,
    body: IngredientCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_ingredient(
            session,
            principal,
            code=body.code,
            display_name=body.display_name,
            ingredient_type=body.ingredient_type,
            nutrition_basis_unit_id=body.nutrition_basis_unit_id,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    first = session.scalar(
        select(IngredientVersion)
        .where(IngredientVersion.ingredient_id == row.id)
        .order_by(IngredientVersion.version_number)
    )
    return versioned(ingredient_card(row, first), row.row_version)


@router.patch("/ingredients/{ingredient_id}")
def patch_ingredient(
    organization_id: UUID,
    ingredient_id: UUID,
    body: IdentityPatch,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: update_identity(
            session,
            principal,
            ingredient_id=ingredient_id,
            display_name=body.display_name,
            code=body.code,
            status=body.status,
            expected_version=match,
        )
    )
    return versioned(ingredient_card(row, None), row.row_version)


@router.post("/ingredients/{ingredient_id}/versions")
def post_version(
    organization_id: UUID,
    ingredient_id: UUID,
    body: VersionCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_version(
            session,
            principal,
            ingredient_id=ingredient_id,
            source_version_id=body.source_version_id,
            nutrition_basis_unit_id=body.nutrition_basis_unit_id,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.patch("/ingredients/{ingredient_id}/versions/{version_id}")
def patch_version(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    body: DraftPatch,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: update_draft(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            notes=body.notes,
            data_source_id=body.data_source_id,
            expected_version=match,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/ingredients/{ingredient_id}/versions/{version_id}/publish")
def post_publish(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, match = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: publish_version(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            expected_version=match,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/ingredients/{ingredient_id}/versions/{version_id}/retire")
def post_retire(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, match = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: retire_version(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            expected_version=match,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/ingredients/{ingredient_id}/versions/{version_id}/composition")
def post_composition(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    body: CompositionWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: upsert_composition(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            component_version_id=body.component_version_id,
            component_type=body.component_type,
            quantity=body.quantity,
            measurement_unit_id=body.measurement_unit_id,
            sequence=body.sequence,
            expected_version=match,
        )
    )
    return {"data": composition_out(row)}


@router.delete("/ingredients/{ingredient_id}/versions/{version_id}/composition/{composition_id}")
def delete_composition(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    composition_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    _run(
        lambda: remove_composition(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            composition_id=composition_id,
            expected_version=match,
        )
    )
    return {"data": {"ok": True}}


@router.post("/ingredients/{ingredient_id}/versions/{version_id}/nutrients")
def post_nutrient(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    body: NutrientWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: upsert_nutrient(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            nutrient_id=body.nutrient_id,
            value=body.value,
            value_status=body.value_status,
            limit_of_quantification=body.limit_of_quantification,
            loq_unit_id=body.loq_unit_id,
            method_or_source=body.method_or_source,
            expected_version=match,
        )
    )
    return {"data": nutrient_out(row)}


@router.post("/ingredients/{ingredient_id}/versions/{version_id}/allergens")
def post_allergen(
    organization_id: UUID,
    ingredient_id: UUID,
    version_id: UUID,
    body: AllergenWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: upsert_allergen(
            session,
            principal,
            ingredient_id=ingredient_id,
            version_id=version_id,
            allergen_id=body.allergen_id,
            presence=body.presence,
            data_source_id=body.data_source_id,
            evidence_note=body.evidence_note,
            expected_version=match,
        )
    )
    return {"data": allergen_out(row)}


@router.post("/suppliers")
def post_supplier(
    organization_id: UUID,
    body: SupplierCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_supplier(
            session,
            principal,
            code=body.code,
            display_name=body.display_name,
            idempotency_key=key,
        )
    )
    return versioned(supplier_out(row), row.row_version)


@router.patch("/suppliers/{supplier_id}")
def patch_supplier(
    organization_id: UUID,
    supplier_id: UUID,
    body: SupplierPatch,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: update_supplier(
            session,
            principal,
            supplier_id=supplier_id,
            display_name=body.display_name,
            status=body.status,
            expected_version=match,
        )
    )
    return versioned(supplier_out(row), row.row_version)


@router.post("/suppliers/{supplier_id}/items")
def post_item(
    organization_id: UUID,
    supplier_id: UUID,
    body: SupplierItemCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_supplier_item(
            session,
            principal,
            supplier_id=supplier_id,
            ingredient_id=body.ingredient_id,
            supplier_sku=body.supplier_sku,
            description=body.description,
            package_quantity=body.package_quantity,
            measurement_unit_id=body.measurement_unit_id,
            idempotency_key=key,
        )
    )
    return versioned(item_out(row), row.row_version)


@router.post("/items/{item_id}/prices")
def post_price(
    organization_id: UUID,
    item_id: UUID,
    body: PriceWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_price(
            session,
            principal,
            item_id=item_id,
            unit_price=body.unit_price,
            currency=body.currency,
            observed_at=body.observed_at,
            source=body.source,
            idempotency_key=key,
        )
    )
    return {"data": price_out(row)}
