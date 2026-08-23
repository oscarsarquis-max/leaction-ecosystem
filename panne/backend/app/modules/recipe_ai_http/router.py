from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.ai_orchestration.service import (
    decide_proposal,
    get_proposal,
    list_proposals,
    materialize_recipe_proposal,
    propose_recipe,
    review_changes,
)
from app.modules.identity_organization.authorization import Principal
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.recipe_ai_http.serialize import grounding_out, proposal_card, proposal_detail

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProposeBody(StrictModel):
    intent: str
    base_formulation_version_id: str | None = None
    objective: str
    product_type: str | None = None
    yield_units: int | None = None
    target_quantity: str | None = None
    technical_traits: list[str] = Field(default_factory=list)
    required_components: list[str] = Field(default_factory=list)
    forbidden_components: list[str] = Field(default_factory=list)
    allergens_to_avoid: list[str] = Field(default_factory=list)
    process_limits: list[str] = Field(default_factory=list)
    selected_reference_ids: list[str] = Field(default_factory=list)
    selected_knowledge_source_ids: list[str] = Field(default_factory=list)
    allowed_ingredient_version_ids: list[str] = Field(default_factory=list)
    jurisdiction: str | None = None
    regulatory_purpose: str | None = None
    notes: str | None = None


class ChangeDecisionBody(StrictModel):
    change_key: str
    decision: str
    notes: str | None = None


class ChangesBody(StrictModel):
    decisions: list[ChangeDecisionBody]


class ReviewBody(StrictModel):
    decision: str
    notes: str | None = None
    confirm: bool = False


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


@router.post("/recipe-ai/proposals")
def post_proposal(
    body: ProposeBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    key = require_idempotency_key(idempotency_key)
    row = _run(lambda: propose_recipe(session, principal, body.model_dump(), idempotency_key=key))
    return {"data": proposal_detail(session, row), "row_version": row.row_version}


@router.get("/recipe-ai/proposals")
def get_proposals(
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    rows = _run(lambda: list_proposals(session, principal))
    return {"items": [proposal_card(row) for row in rows], "total": len(rows)}


@router.get("/recipe-ai/proposals/{proposal_id}")
def get_proposal_detail(
    proposal_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    row = _run(lambda: get_proposal(session, principal, proposal_id))
    return {"data": proposal_detail(session, row), "row_version": row.row_version}


@router.get("/recipe-ai/proposals/{proposal_id}/grounding")
def get_proposal_grounding(
    proposal_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    row = _run(lambda: get_proposal(session, principal, proposal_id))
    return {"data": grounding_out(session, row)}


@router.get("/recipe-ai/proposals/{proposal_id}/comparison")
def get_proposal_comparison(
    proposal_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    row = _run(lambda: get_proposal(session, principal, proposal_id))
    detail = proposal_detail(session, row)
    return {"data": {"changes": detail["changes"], "items": detail["items"]}}


@router.post("/recipe-ai/proposals/{proposal_id}/changes")
def post_proposal_changes(
    proposal_id: UUID,
    body: ChangesBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    match = parse_if_match(if_match, required=False)
    row = _run(
        lambda: review_changes(
            session,
            principal,
            proposal_id,
            decisions=[item.model_dump() for item in body.decisions],
            expected_version=match,
        )
    )
    return {"data": proposal_detail(session, row), "row_version": row.row_version}


@router.post("/recipe-ai/proposals/{proposal_id}/review")
def post_proposal_review(
    proposal_id: UUID,
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
    row = _run(
        lambda: decide_proposal(
            session,
            principal,
            proposal_id,
            decision=body.decision,
            notes=body.notes,
            confirm=body.confirm,
            idempotency_key=key,
            expected_version=match,
        )
    )
    return {"data": proposal_detail(session, row), "row_version": row.row_version}


@router.post("/recipe-ai/proposals/{proposal_id}/materialize")
def post_proposal_materialize(
    proposal_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    key = require_idempotency_key(idempotency_key)
    match = parse_if_match(if_match, required=False)
    row = _run(
        lambda: materialize_recipe_proposal(
            session,
            principal,
            proposal_id,
            idempotency_key=key,
            expected_version=match,
        )
    )
    return {"data": proposal_detail(session, row), "row_version": row.row_version}
