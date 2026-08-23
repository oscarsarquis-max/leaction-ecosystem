from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.labeling_compliance import services
from app.modules.labeling_http.render import render_candidate
from app.modules.labeling_http.serialize import (
    bundle_out,
    dossier_card,
    dossier_detail,
    version_card,
)
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateBody(StrictModel):
    formulation_version_id: str
    nutrition_calculation_id: str | None = None
    establishment_id: str | None = None


class ProfileBody(StrictModel):
    jurisdiction: str | None = None
    evaluation_date: str | None = None
    packed_food: bool | None = None
    packed_away_from_consumer: bool | None = None
    packed_at_point_of_sale: bool | None = None
    packed_on_request: bool | None = None
    same_establishment: bool | None = None
    sales_channel: str | None = None
    food_service: bool | None = None
    physical_state: str | None = None
    ready_to_eat: bool | None = None
    regulatory_category_code: str | None = None
    category_confirmed: bool = False
    package_area_cm2: str | None = None
    net_content_g: str | None = None
    servings_per_package: int | None = None
    purpose: str | None = None
    destination_market: str | None = None
    establishment_id: str | None = None


class ReviewBody(StrictModel):
    decision: str
    notes: str | None = None


class MandatoryItemBody(StrictModel):
    code: str
    value: str | None = None
    claim: bool = False


class MandatoryBody(StrictModel):
    items: list[MandatoryItemBody]


class InvalidateBody(StrictModel):
    reason: str


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


@router.get("/labeling/dossiers")
def get_dossiers(
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    rows = _run(lambda: services.list_dossiers(session, principal))
    return {"items": [dossier_card(row) for row in rows], "total": len(rows)}


@router.post("/labeling/dossiers")
def post_dossier(
    body: CreateBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    key = require_idempotency_key(idempotency_key)
    row = _run(lambda: services.create_dossier(session, principal, body.model_dump(), idempotency_key=key))
    return {"data": dossier_card(row), "row_version": row.row_version}


@router.get("/labeling/dossiers/{dossier_id}")
def get_dossier(
    dossier_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    payload = _run(lambda: services.latest_bundle(session, principal, dossier_id))
    return {"data": dossier_detail(payload), "row_version": payload["dossier"].row_version}


@router.post("/labeling/dossiers/{dossier_id}/profile")
def post_profile(
    dossier_id: UUID,
    body: ProfileBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=False)
    row = _run(
        lambda: services.save_profile(
            session, principal, dossier_id, body.model_dump(), expected_version=match
        )
    )
    dossier = services.get_dossier(session, principal, dossier_id)
    return {
        "data": {"completeness": row.completeness, "id": str(row.id)},
        "row_version": dossier.row_version,
    }


@router.post("/labeling/dossiers/{dossier_id}/evaluate")
def post_evaluate(
    dossier_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    key = require_idempotency_key(idempotency_key)
    match = parse_if_match(if_match, required=False)
    version = _run(
        lambda: services.run_evaluation(
            session, principal, dossier_id, idempotency_key=key, expected_version=match
        )
    )
    dossier = services.get_dossier(session, principal, dossier_id)
    return {"data": version_card(version), "row_version": dossier.row_version}


@router.post("/labeling/dossiers/{dossier_id}/review")
def post_review(
    dossier_id: UUID,
    body: ReviewBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    key = require_idempotency_key(idempotency_key)
    match = parse_if_match(if_match, required=False)
    version = _run(
        lambda: services.review_version(
            session,
            principal,
            dossier_id,
            body.model_dump(),
            idempotency_key=key,
            expected_version=match,
        )
    )
    dossier = services.get_dossier(session, principal, dossier_id)
    return {"data": version_card(version), "row_version": dossier.row_version}


@router.post("/labeling/dossiers/{dossier_id}/invalidate")
def post_invalidate(
    dossier_id: UUID,
    body: InvalidateBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=False)
    version = _run(
        lambda: services.invalidate_version(
            session, principal, dossier_id, body.reason, expected_version=match
        )
    )
    dossier = services.get_dossier(session, principal, dossier_id)
    return {"data": version_card(version), "row_version": dossier.row_version}


@router.post("/labeling/dossiers/{dossier_id}/mandatory")
def post_mandatory(
    dossier_id: UUID,
    body: MandatoryBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=False)
    version = _run(
        lambda: services.edit_mandatory(
            session,
            principal,
            dossier_id,
            [item.model_dump() for item in body.items],
            expected_version=match,
        )
    )
    dossier = services.get_dossier(session, principal, dossier_id)
    return {"data": version_card(version), "row_version": dossier.row_version}


@router.get("/labeling/dossiers/{dossier_id}/versions")
def get_versions(
    dossier_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    rows = _run(lambda: services.list_versions(session, principal, dossier_id))
    return {"items": [version_card(row) for row in rows], "total": len(rows)}


@router.get("/labeling/dossiers/{dossier_id}/versions/{version_id}")
def get_version(
    dossier_id: UUID,
    version_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    version = _run(lambda: services.get_version(session, principal, dossier_id, version_id))
    return {"data": bundle_out(services.version_bundle(session, version))}


@router.get("/labeling/dossiers/{dossier_id}/compare")
def get_compare(
    dossier_id: UUID,
    left: UUID,
    right: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    payload = _run(lambda: services.compare_versions(session, principal, dossier_id, left, right))
    return {"data": {"left": bundle_out(payload["left"]), "right": bundle_out(payload["right"])}}


@router.get("/labeling/dossiers/{dossier_id}/render")
def get_render(
    dossier_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    _run(lambda: services.require_render(principal))
    payload = _run(lambda: services.latest_bundle(session, principal, dossier_id))
    detail = dossier_detail(payload)
    return {"data": {"html": render_candidate(detail), "candidate": detail.get("current")}}


@router.get("/labeling/assessments")
def get_assessments(
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    rows = _run(lambda: services.list_assessments(session, principal))
    return {
        "items": [
            {
                "id": str(row.id),
                "status": row.status,
                "proposal_summary": row.proposal_summary,
                "created_at": None if row.created_at is None else row.created_at.isoformat(),
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/labeling/candidates")
def get_candidates(
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    rows = _run(lambda: services.list_candidates(session, principal))
    return {
        "items": [
            {
                "id": str(row.id),
                "watermark": row.watermark,
                "payload_sha256": row.payload_sha256,
                "created_at": None if row.created_at is None else row.created_at.isoformat(),
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/labeling/portions")
def get_portions(principal: Annotated[Principal, Depends(get_runtime_principal)]):
    return {"items": _run(lambda: services.list_portions(principal))}


@router.get("/labeling/sources")
def get_sources(principal: Annotated[Principal, Depends(get_runtime_principal)]):
    return {"items": _run(lambda: services.list_sources(principal))}
