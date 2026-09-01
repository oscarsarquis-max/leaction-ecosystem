from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.formula_lab.models import ProductFamily, TechnicalProduct
from app.modules.identity_organization.authorization import Principal
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.product_catalog.commands import (
    assert_product_allows_production,
    create_family,
    create_product,
    has_published_recipe,
    has_process_steps_on_published_recipe,
    list_families,
    list_products_query,
    product_summary,
    related_order_count,
    related_recipe_count,
    require_product_read,
    set_product_status,
    update_family,
    update_product,
)
from app.modules.product_catalog.recipe_projection import current_recipe_projection
from app.modules.product_catalog.constants import (
    PURPOSE_FINAL,
    STATUS_ACTIVE,
    SUPPLY_PRODUCED,
)
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.production_planning.errors import ValidationError

router = APIRouter()


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


def _keys(idempotency_key: str | None, x_correlation_id: str | None, if_match: str | None = None):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key), parse_if_match(if_match, required=False)


class ProductCreate(BaseModel):
    code: str
    display_name: str
    description: str | None = None
    purpose: str = PURPOSE_FINAL
    supply_mode: str = SUPPLY_PRODUCED
    family_id: UUID | None = None
    stock_unit_id: UUID | None = None
    sale_unit_id: UUID | None = None
    net_content: Decimal | None = None
    net_content_unit_id: UUID | None = None
    default_shelf_life_days: int | None = None
    packaging_description: str | None = None
    status: str = STATUS_ACTIVE


class ProductPatch(BaseModel):
    code: str | None = None
    display_name: str | None = None
    description: str | None = None
    purpose: str | None = None
    supply_mode: str | None = None
    family_id: UUID | None = None
    stock_unit_id: UUID | None = None
    sale_unit_id: UUID | None = None
    net_content: Decimal | None = None
    net_content_unit_id: UUID | None = None
    default_shelf_life_days: int | None = None
    packaging_description: str | None = None


class ProductStatusBody(BaseModel):
    status: str


class FamilyCreate(BaseModel):
    code: str
    display_name: str
    description: str | None = None
    parent_id: UUID | None = None
    status: str = STATUS_ACTIVE


class FamilyPatch(BaseModel):
    code: str | None = None
    display_name: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    status: str | None = None


def _unit_label(session: Session, unit_id: UUID | None) -> dict | None:
    if unit_id is None:
        return None
    unit = session.get(MeasurementUnit, unit_id)
    if unit is None:
        return None
    return {"id": str(unit.id), "code": unit.code, "display_name": unit.name}


def _family_card(family: ProductFamily | None) -> dict | None:
    if family is None:
        return None
    return {
        "id": str(family.id),
        "code": family.code,
        "display_name": family.display_name,
        "status": family.status,
    }


def _recipe_status_label(has_recipe: bool, supply_mode: str) -> str:
    if supply_mode == "purchased":
        return "Não se aplica"
    if supply_mode in {"mixed", "combo"}:
        return "Modalidade em preparação"
    return "Com receita vigente" if has_recipe else "Sem receita vigente"


def product_card(session: Session, row: TechnicalProduct, *, organization_id: UUID) -> dict:
    family = session.get(ProductFamily, row.family_id) if row.family_id else None
    has_recipe = has_published_recipe(session, row.id, organization_id)
    has_steps = (
        has_process_steps_on_published_recipe(session, row.id, organization_id) if has_recipe else False
    )
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "description": row.description,
        "status": row.status,
        "purpose": row.purpose,
        "supply_mode": row.supply_mode,
        "family": _family_card(family),
        "has_published_recipe": has_recipe,
        "has_process_steps": has_steps,
        "recipe_status_label": _recipe_status_label(has_recipe, row.supply_mode),
        "stock_unit": _unit_label(session, row.stock_unit_id),
        "sale_unit": _unit_label(session, row.sale_unit_id),
        "net_content": str(row.net_content) if row.net_content is not None else None,
        "net_content_unit": _unit_label(session, row.net_content_unit_id),
        "default_shelf_life_days": row.default_shelf_life_days,
        "packaging_description": row.packaging_description,
        "row_version": row.row_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def product_detail(session: Session, row: TechnicalProduct, *, organization_id: UUID) -> dict:
    card = product_card(session, row, organization_id=organization_id)
    card["links"] = {
        "recipes_count": related_recipe_count(session, row.id, organization_id),
        "orders_count": related_order_count(session, row.id, organization_id),
    }
    card["operational_notes"] = []
    if row.supply_mode == "purchased":
        card["operational_notes"].append(
            "Recebimento e estoque de mercadoria serão completados no próximo ciclo."
        )
    if row.supply_mode in {"mixed", "combo"}:
        card["operational_notes"].append(
            "Modalidade em preparação — produção, recebimento e composição incompletos nesta fase."
        )
    if row.supply_mode == "produced" and not card["has_published_recipe"]:
        card["operational_notes"].append(
            "Cadastro válido sem receita; produção fica bloqueada até haver receita vigente."
        )
    # Origem: Formulation.technical_product_id (FK persistente). Sem inferência por código/nome.
    card["current_recipe"] = current_recipe_projection(session, row.id, organization_id)
    return card


@router.get("/products")
def get_products(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    purpose: Annotated[str | None, Query()] = None,
    supply_mode: Annotated[str | None, Query(alias="supply_mode")] = None,
    family_id: Annotated[UUID | None, Query()] = None,
    code: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    def action():
        require_product_read(principal)
        stmt = list_products_query(
            organization_id,
            q=q,
            status=status,
            purpose=purpose,
            supply_mode=supply_mode,
            family_id=family_id,
            code=code,
        )
        total = session.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
        items = session.execute(stmt.offset(offset).limit(limit)).scalars().all()
        return {
            "items": [product_card(session, row, organization_id=organization_id) for row in items],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    return _run(action)


@router.get("/products/summary")
def get_products_summary(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    def action():
        require_product_read(principal)
        return {"data": product_summary(session, organization_id)}

    return _run(action)


@router.get("/products/{product_id}")
def get_product(
    organization_id: UUID,
    product_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    def action():
        require_product_read(principal)
        row = session.get(TechnicalProduct, product_id)
        if row is None or row.organization_id != organization_id:
            raise ValidationError("recurso_nao_encontrado")
        return {"data": product_detail(session, row, organization_id=organization_id), "row_version": row.row_version}

    return _run(action)


@router.post("/products")
def post_product(
    organization_id: UUID,
    body: ProductCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    _keys(idempotency_key, x_correlation_id)

    def action():
        row = create_product(session, principal, **body.model_dump())
        session.flush()
        return {"data": product_detail(session, row, organization_id=organization_id), "row_version": row.row_version}

    return _run(action)


@router.patch("/products/{product_id}")
def patch_product(
    organization_id: UUID,
    product_id: UUID,
    body: ProductPatch,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    _, match = _keys(idempotency_key, x_correlation_id, if_match)

    def action():
        row = update_product(
            session,
            principal,
            product_id=product_id,
            expected_row_version=match,
            **body.model_dump(exclude_unset=True),
        )
        session.flush()
        return {"data": product_detail(session, row, organization_id=organization_id), "row_version": row.row_version}

    return _run(action)


@router.post("/products/{product_id}/status")
def post_product_status(
    organization_id: UUID,
    product_id: UUID,
    body: ProductStatusBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    _, match = _keys(idempotency_key, x_correlation_id, if_match)

    def action():
        row = set_product_status(
            session,
            principal,
            product_id=product_id,
            status=body.status,
            expected_row_version=match,
        )
        session.flush()
        return {"data": product_detail(session, row, organization_id=organization_id), "row_version": row.row_version}

    return _run(action)


@router.get("/product-families")
def get_families(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    def action():
        require_product_read(principal)
        rows = list_families(session, organization_id)
        return {
            "items": [
                {
                    "id": str(row.id),
                    "code": row.code,
                    "display_name": row.display_name,
                    "description": row.description,
                    "status": row.status,
                    "parent_id": str(row.parent_id) if row.parent_id else None,
                    "row_version": row.row_version,
                }
                for row in rows
            ]
        }

    return _run(action)


@router.post("/product-families")
def post_family(
    organization_id: UUID,
    body: FamilyCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    _keys(idempotency_key, x_correlation_id)

    def action():
        row = create_family(session, principal, **body.model_dump())
        session.flush()
        return {
            "data": {
                "id": str(row.id),
                "code": row.code,
                "display_name": row.display_name,
                "description": row.description,
                "status": row.status,
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "row_version": row.row_version,
            },
            "row_version": row.row_version,
        }

    return _run(action)


@router.patch("/product-families/{family_id}")
def patch_family(
    organization_id: UUID,
    family_id: UUID,
    body: FamilyPatch,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    _, match = _keys(idempotency_key, x_correlation_id, if_match)

    def action():
        row = update_family(
            session,
            principal,
            family_id=family_id,
            expected_row_version=match,
            **body.model_dump(exclude_unset=True),
        )
        session.flush()
        return {
            "data": {
                "id": str(row.id),
                "code": row.code,
                "display_name": row.display_name,
                "description": row.description,
                "status": row.status,
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "row_version": row.row_version,
            },
            "row_version": row.row_version,
        }

    return _run(action)


# Reexport for production guards / tests.
__all__ = ["router", "assert_product_allows_production"]
