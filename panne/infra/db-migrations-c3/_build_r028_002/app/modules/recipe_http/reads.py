from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.formula_lab.commands import require_read, require_sheet_read
from app.modules.formula_lab.models import Formulation, FormulationVersion
from app.modules.formula_lab.queries import (
    approvals_of,
    bakers_view,
    completeness_of,
    items_of,
    latest_nutrition,
    list_recipes,
    list_references,
    measurements_of,
    nutrition_items_of,
    references_of,
    version_refs_of,
    scale_items_of,
    scales_of,
    steps_of,
    trials_of,
    versions_of,
    yield_of,
)
from app.modules.formula_lab.sheet import project_technical_sheet
from app.modules.identity_organization.authorization import (
    PERMISSION_RECIPE_APPROVE,
    PERMISSION_RECIPE_PUBLISH,
    PERMISSION_RECIPE_REVIEW,
    PERMISSION_RECIPE_UPDATE_DRAFT,
    Principal,
)
from app.modules.production_http.deps import get_runtime_principal
from app.modules.production_http.errors import raise_domain
from app.modules.production_planning.errors import ValidationError
from app.modules.recipe_http.serialize import (
    approval_out,
    item_out,
    load_item_enrichments,
    measurement_out,
    nutrition_item_out,
    nutrition_out,
    recipe_card,
    reference_link_out,
    reference_out,
    version_reference_out,
    scale_item_out,
    scale_out,
    step_out,
    trial_out,
    version_out,
    versioned,
)

router = APIRouter()


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


def _identity(session: Session, organization_id: UUID, recipe_id: UUID) -> Formulation:
    row = session.get(Formulation, recipe_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _version(
    session: Session, organization_id: UUID, recipe_id: UUID, version_id: UUID
) -> FormulationVersion:
    row = session.get(FormulationVersion, version_id)
    if row is None or row.organization_id != organization_id or row.formulation_id != recipe_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _released_only(principal: Principal) -> bool:
    return not any(
        code in principal.permissions
        for code in (
            PERMISSION_RECIPE_UPDATE_DRAFT,
            PERMISSION_RECIPE_REVIEW,
            PERMISSION_RECIPE_APPROVE,
            PERMISSION_RECIPE_PUBLISH,
        )
    )


@router.get("/recipes")
def get_recipes(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: str | None = None,
    status: str | None = None,
    version_status: str | None = None,
    ingredient_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    require_read(principal)
    published_only = _released_only(principal)
    rows, total = _run(
        lambda: list_recipes(
            session,
            organization_id,
            q=q,
            status=status,
            version_status=version_status,
            ingredient_id=ingredient_id,
            published_only=published_only,
            limit=limit,
            offset=offset,
        )
    )
    return {
        "items": [recipe_card(identity, version) for identity, version in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/recipes/{recipe_id}")
def get_recipe(
    organization_id: UUID,
    recipe_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, recipe_id))
    history = versions_of(session, organization_id, recipe_id)
    if _released_only(principal):
        history = [item for item in history if item.status == "published"]
        if not history:
            raise_domain(ValidationError("recurso_nao_encontrado"))
    latest = history[0] if history else None
    return versioned(
        {
            **recipe_card(identity, latest),
            "versions": [version_out(item) for item in history],
        },
        identity.row_version,
    )


@router.get("/recipes/{recipe_id}/versions")
def get_versions(
    organization_id: UUID,
    recipe_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _identity(session, organization_id, recipe_id))
    history = versions_of(session, organization_id, recipe_id)
    if _released_only(principal):
        history = [item for item in history if item.status == "published"]
    return {"data": [version_out(item) for item in history]}


@router.get("/recipes/{recipe_id}/versions/{version_id}")
def get_version(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, recipe_id))
    version = _run(lambda: _version(session, organization_id, recipe_id, version_id))
    if _released_only(principal) and version.status != "published":
        raise_domain(ValidationError("recurso_nao_encontrado"))
    bakers = bakers_view(session, version.id)
    percents = {row["id"]: row["bakers_percentage"] for row in bakers["items"]}
    items = list(items_of(session, version.id))
    enrichments = load_item_enrichments(session, organization_id, items)
    return versioned(
        {
            "identity": recipe_card(identity, version),
            "version": version_out(version),
            "items": [
                item_out(
                    row,
                    percents.get(str(row.id)),
                    ingredient=enrichments.get(row.id, (None, None))[0],
                    unit=enrichments.get(row.id, (None, None))[1],
                )
                for row in items
            ],
            "steps": [step_out(row) for row in steps_of(session, version.id)],
            "bakers": bakers,
            "yield": yield_of(session, version),
            "completeness": completeness_of(session, identity, version),
        },
        version.row_version,
    )


@router.get("/recipes/{recipe_id}/versions/{version_id}/items")
def get_items(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    version = _run(lambda: _version(session, organization_id, recipe_id, version_id))
    bakers = bakers_view(session, version.id)
    percents = {row["id"]: row["bakers_percentage"] for row in bakers["items"]}
    items = list(items_of(session, version.id))
    enrichments = load_item_enrichments(session, organization_id, items)
    return {
        "data": [
            item_out(
                row,
                percents.get(str(row.id)),
                ingredient=enrichments.get(row.id, (None, None))[0],
                unit=enrichments.get(row.id, (None, None))[1],
            )
            for row in items
        ],
        "bakers": bakers,
    }


@router.get("/recipes/{recipe_id}/versions/{version_id}/steps")
def get_steps(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": [step_out(row) for row in steps_of(session, version_id)]}


@router.get("/recipes/{recipe_id}/versions/{version_id}/bakers")
def get_bakers(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": bakers_view(session, version_id)}


@router.get("/recipes/{recipe_id}/versions/{version_id}/yield")
def get_yield(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    version = _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": yield_of(session, version)}


@router.get("/recipes/{recipe_id}/versions/{version_id}/scales")
def get_scales(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {
        "data": [
            {
                **scale_out(row),
                "items": [scale_item_out(item) for item in scale_items_of(session, row.id)],
            }
            for row in scales_of(session, version_id)
        ]
    }


@router.get("/recipes/{recipe_id}/versions/{version_id}/trials")
def get_trials(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {
        "data": [
            {
                **trial_out(row),
                "measurements": [
                    measurement_out(item) for item in measurements_of(session, row.id)
                ],
            }
            for row in trials_of(session, version_id)
        ]
    }


@router.get("/recipes/{recipe_id}/versions/{version_id}/approvals")
def get_approvals(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": [approval_out(row) for row in approvals_of(session, version_id)]}


@router.get("/recipes/{recipe_id}/versions/{version_id}/nutrition")
def get_nutrition(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    row = latest_nutrition(session, version_id)
    if row is None:
        return {
            "data": None,
            "disclaimer": "Prévia técnica incompleta e não validada regulatoriamente.",
        }
    return {
        "data": {
            **nutrition_out(row),
            "items": [nutrition_item_out(item) for item in nutrition_items_of(session, row.id)],
        }
    }


@router.get("/recipes/{recipe_id}/versions/{version_id}/completeness")
def get_completeness(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    identity = _run(lambda: _identity(session, organization_id, recipe_id))
    version = _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": completeness_of(session, identity, version)}


@router.get("/recipes/{recipe_id}/versions/{version_id}/sheet")
def get_sheet(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_sheet_read(principal)
    identity = _run(lambda: _identity(session, organization_id, recipe_id))
    version = _run(lambda: _version(session, organization_id, recipe_id, version_id))
    if _released_only(principal) and version.status != "published":
        raise_domain(ValidationError("recurso_nao_encontrado"))
    org_name = ""
    if principal.selected is not None:
        org_name = principal.selected.organization_display_name
    payload = project_technical_sheet(
        session,
        identity,
        version,
        organization_name=org_name,
        actor_name=principal.display_name,
    )
    return {"data": payload}


@router.get("/recipes/{recipe_id}/references")
def get_recipe_references(
    organization_id: UUID,
    recipe_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _identity(session, organization_id, recipe_id))
    return {"data": [reference_link_out(row) for row in references_of(session, recipe_id)]}


@router.get("/recipes/{recipe_id}/versions/{version_id}/references")
def get_version_references(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    require_read(principal)
    _run(lambda: _version(session, organization_id, recipe_id, version_id))
    return {"data": [version_reference_out(row) for row in version_refs_of(session, version_id)]}


@router.get("/recipe-references")
def get_references(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    q: str | None = None,
):
    require_read(principal)
    return {"data": [reference_out(row) for row in list_references(session, organization_id, q)]}
