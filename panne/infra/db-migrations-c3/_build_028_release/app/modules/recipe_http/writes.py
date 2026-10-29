from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.formula_lab.commands import (
    create_recipe,
    create_reference,
    create_version,
    link_reference,
    publish_version,
    record_approval,
    record_nutrition,
    record_scale,
    record_trial,
    record_trial_measurement,
    remove_item,
    remove_step,
    retire_version,
    simulate_scale,
    unlink_reference,
    update_draft,
    update_identity,
    update_trial_status,
    upsert_item,
    upsert_step,
)
from app.modules.formula_lab.models import FormulationVersion
from app.modules.identity_organization.authorization import Principal
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.recipe_http.schemas import (
    ApprovalWrite,
    DraftPatch,
    ItemWrite,
    MeasurementWrite,
    RecipeCreate,
    RecipePatch,
    ReferenceCreate,
    ReferenceLinkWrite,
    ScaleWrite,
    StepWrite,
    TrialStatusWrite,
    TrialWrite,
    VersionCreate,
)
from app.modules.recipe_http.serialize import (
    approval_out,
    item_out,
    measurement_out,
    nutrition_out,
    recipe_card,
    reference_link_out,
    reference_out,
    scale_out,
    scale_result_out,
    step_out,
    trial_out,
    version_out,
    versioned,
)

router = APIRouter()


def _keys(idempotency_key: str | None, x_correlation_id: str | None, if_match: str | None = None):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key), parse_if_match(if_match, required=False)


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


@router.post("/recipes")
def post_recipe(
    organization_id: UUID,
    body: RecipeCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_recipe(
            session,
            principal,
            product_code=body.product_code or body.code,
            product_name=body.product_name or body.display_name,
            recipe_code=body.code,
            recipe_name=body.display_name,
            idempotency_key=key,
        )
    )
    first = session.scalar(
        select(FormulationVersion)
        .where(FormulationVersion.formulation_id == row.id)
        .order_by(FormulationVersion.version_number)
    )
    return versioned(recipe_card(row, first), row.row_version)


@router.patch("/recipes/{recipe_id}")
def patch_recipe(
    organization_id: UUID,
    recipe_id: UUID,
    body: RecipePatch,
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
            recipe_id,
            display_name=body.display_name,
            status=body.status,
            expected_version=match,
        )
    )
    return versioned(recipe_card(row, None), row.row_version)


@router.post("/recipes/{recipe_id}/versions")
def post_version(
    organization_id: UUID,
    recipe_id: UUID,
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
            recipe_id,
            source_version_id=body.source_version_id,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.patch("/recipes/{recipe_id}/versions/{version_id}")
def patch_version(
    organization_id: UUID,
    recipe_id: UUID,
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
            version_id,
            notes=body.notes,
            yield_units=body.yield_units,
            target_unit_weight_g=body.target_unit_weight_g,
            expected_bake_loss_rate=body.expected_bake_loss_rate,
            expected_version=match,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/recipes/{recipe_id}/versions/{version_id}/publish")
def post_publish(
    organization_id: UUID,
    recipe_id: UUID,
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
            version_id,
            expected_version=match,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/recipes/{recipe_id}/versions/{version_id}/retire")
def post_retire(
    organization_id: UUID,
    recipe_id: UUID,
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
            version_id,
            expected_version=match,
            idempotency_key=key,
        )
    )
    return versioned(version_out(row), row.row_version)


@router.post("/recipes/{recipe_id}/versions/{version_id}/items")
def post_item(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: ItemWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: upsert_item(
            session,
            principal,
            version_id,
            ingredient_version_id=body.ingredient_version_id,
            sequence=body.sequence,
            net_quantity=body.net_quantity,
            measurement_unit_id=body.measurement_unit_id,
            correction_factor=body.correction_factor,
            is_flour_basis=body.is_flour_basis,
            role=body.role,
            notes=body.notes,
            expected_version=match,
        )
    )
    return {"data": item_out(row)}


@router.delete("/recipes/{recipe_id}/versions/{version_id}/items/{item_id}")
def delete_item(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    _run(lambda: remove_item(session, principal, version_id, item_id, match))
    return {"data": {"ok": True}}


@router.post("/recipes/{recipe_id}/versions/{version_id}/steps")
def post_step(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: StepWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: upsert_step(
            session,
            principal,
            version_id,
            sequence=body.sequence,
            title=body.title,
            instructions=body.instructions,
            duration_seconds=body.duration_seconds,
            temperature_celsius=body.temperature_celsius,
            expected_version=match,
        )
    )
    return {"data": step_out(row)}


@router.delete("/recipes/{recipe_id}/versions/{version_id}/steps/{step_id}")
def delete_step(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    step_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    _run(lambda: remove_step(session, principal, version_id, step_id, match))
    return {"data": {"ok": True}}


@router.post("/recipes/{recipe_id}/versions/{version_id}/scale/simulate")
def post_scale_simulate(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: ScaleWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    result = _run(
        lambda: simulate_scale(
            session,
            principal,
            version_id,
            mode=body.mode,
            target_total_dough_mass=body.target_total_dough_mass,
            unit_count=body.unit_count,
            final_unit_weight_g=body.final_unit_weight_g,
            bake_loss_rate=body.bake_loss_rate,
        )
    )
    return {"data": scale_result_out(result)}


@router.post("/recipes/{recipe_id}/versions/{version_id}/scale")
def post_scale(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: ScaleWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_scale(
            session,
            principal,
            version_id,
            mode=body.mode,
            target_total_dough_mass=body.target_total_dough_mass,
            unit_count=body.unit_count,
            final_unit_weight_g=body.final_unit_weight_g,
            bake_loss_rate=body.bake_loss_rate,
            idempotency_key=key,
        )
    )
    return {"data": scale_out(row)}


@router.post("/recipes/{recipe_id}/versions/{version_id}/nutrition")
def post_nutrition(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(lambda: record_nutrition(session, principal, version_id, idempotency_key=key))
    return {"data": nutrition_out(row)}


@router.post("/recipes/{recipe_id}/versions/{version_id}/approvals")
def post_approval(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: ApprovalWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_approval(
            session,
            principal,
            version_id,
            decision=body.decision,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    return {"data": approval_out(row)}


@router.post("/recipes/{recipe_id}/versions/{version_id}/trials")
def post_trial(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    body: TrialWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_trial(
            session,
            principal,
            version_id,
            code=body.code,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    return {"data": trial_out(row)}


@router.patch("/recipes/{recipe_id}/versions/{version_id}/trials/{trial_id}")
def patch_trial(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    trial_id: UUID,
    body: TrialStatusWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    row = _run(
        lambda: update_trial_status(
            session, principal, trial_id, status=body.status, notes=body.notes
        )
    )
    return {"data": trial_out(row)}


@router.post("/recipes/{recipe_id}/versions/{version_id}/trials/{trial_id}/measurements")
def post_measurement(
    organization_id: UUID,
    recipe_id: UUID,
    version_id: UUID,
    trial_id: UUID,
    body: MeasurementWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    row = _run(
        lambda: record_trial_measurement(
            session,
            principal,
            trial_id,
            measurement_type=body.measurement_type,
            value=body.value,
            measurement_unit_id=body.measurement_unit_id,
            notes=body.notes,
        )
    )
    return {"data": measurement_out(row)}


@router.post("/recipe-references")
def post_reference(
    organization_id: UUID,
    body: ReferenceCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_reference(
            session,
            principal,
            title=body.title,
            source_type=body.source_type,
            source_url=body.source_url,
            author=body.author,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    return versioned(reference_out(row), row.row_version)


@router.post("/recipes/{recipe_id}/references")
def post_link(
    organization_id: UUID,
    recipe_id: UUID,
    body: ReferenceLinkWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    row = _run(
        lambda: link_reference(
            session,
            principal,
            recipe_id,
            body.recipe_reference_id,
            body.role,
            match,
        )
    )
    return {"data": reference_link_out(row)}


@router.delete("/recipes/{recipe_id}/references/{link_id}")
def delete_link(
    organization_id: UUID,
    recipe_id: UUID,
    link_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=True)
    _run(lambda: unlink_reference(session, principal, recipe_id, link_id, match))
    return {"data": {"ok": True}}
