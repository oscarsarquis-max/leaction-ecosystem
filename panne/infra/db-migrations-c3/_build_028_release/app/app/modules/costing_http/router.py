from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.costing_http.serialize import calculation_out, policy_out, price_out, simulation_out
from app.modules.costing_pricing import services
from app.modules.identity_organization.authorization import Principal
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


class PolicyBody(StrictModel):
    code: str
    display_name: str | None = None
    currency: str = "BRL"
    timezone: str = "America/Sao_Paulo"
    price_criterion: str = "latest_observed"
    use_gross_quantity: bool = True
    include_return: bool = True
    include_waste: bool = True
    include_leftover: bool = False
    include_scrap: bool = True
    use_sellable_yield: bool = True
    enabled_categories: list[str] | None = None
    allocation_notes: str | None = None
    presentation_decimals: int = 2
    justification: str | None = None
    effective_from: str


class AssumptionBody(StrictModel):
    category: str
    code: str
    amount: str
    unit_code: str = "BRL"
    currency: str | None = None
    channel: str | None = None
    nature: str = "indirect"
    behavior: str = "fixed"
    reason: str
    effective_from: str
    effective_to: str | None = None


class CalculateBody(StrictModel):
    kind: str
    policy_version_id: str
    valuation_at: str
    formulation_version_id: str | None = None
    scale_calculation_id: str | None = None
    production_order_id: str | None = None
    production_batch_id: str | None = None
    supplier_item_id: str | None = None
    planned_batches: int | None = None


class SimulateBody(StrictModel):
    kind: str
    channel: str = "own_counter"
    factor: str | None = None
    percent: str | None = None
    target_rate: str | None = None
    variable_expense_rate: str | None = None
    price: str | None = None
    variable_product: str | None = None
    variable_selling: str | None = None
    fixed_allocated: str | None = None
    called_tax: bool = False


class PracticedBody(StrictModel):
    technical_product_id: str
    channel: str
    amount: str
    currency: str = "BRL"
    valid_from: str
    valid_to: str | None = None
    establishment_id: str | None = None
    simulation_id: str | None = None
    justification: str | None = None


class DecideBody(StrictModel):
    decision: str
    notes: str | None = None
    reinforced_confirmation: bool = False


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)
        raise


def _command_keys(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key)


@router.get("/costing/policies")
def list_policies(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    rows = _run(lambda: services.list_policies(session, principal))
    return {
        "items": [
            policy_out(row, services.latest_version(session, row.id)) for row in rows
        ]
    }


@router.post("/costing/policies")
def create_policy(
    body: PolicyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.create_policy(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": policy_out(row, services.latest_version(session, row.id)), "row_version": row.row_version}


@router.post("/costing/policies/{policy_id}/publish")
def publish_policy(
    policy_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.publish_policy(
            session,
            principal,
            policy_id,
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": policy_out(row, services.latest_version(session, row.id)), "row_version": row.row_version}


@router.post("/costing/policy-versions/{version_id}/assumptions")
def add_assumption(
    version_id: UUID,
    body: AssumptionBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.add_assumption(
            session, principal, version_id, body.model_dump(), idempotency_key=idempotency_key
        )
    )
    return {"data": {"id": str(row.id), "category": row.category, "quality": row.quality}}


@router.get("/costing/calculations")
def list_calculations(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    kind: str | None = None,
):
    rows = _run(lambda: services.list_calculations(session, principal, kind))
    marked = services.invalidated_ids(session, principal.selected.organization_id)
    return {
        "items": [calculation_out(row, invalidated=row.id in marked) for row in rows]
    }


@router.post("/costing/calculations")
def create_calculation(
    body: CalculateBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(lambda: services.run_calculation(session, principal, body.model_dump(), idempotency_key=idempotency_key))
    return {"data": calculation_out(row)}


@router.get("/costing/calculations/{calc_id}")
def get_calculation(
    calc_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    payload = _run(lambda: services.calculation_detail(session, principal, calc_id))
    marked = services.invalidated_ids(session, principal.selected.organization_id)
    calc = payload["calculation"]
    return {
        "data": {
            **calculation_out(calc, invalidated=calc.id in marked),
            "components": payload["components"],
            "gaps": [{"code": row.code, "message": row.message} for row in payload["gaps"]],
        }
    }


@router.get("/costing/calculations/{left_id}/compare/{right_id}")
def compare(
    left_id: UUID,
    right_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"data": _run(lambda: services.compare(session, principal, left_id, right_id))}


@router.post("/costing/calculations/{calc_id}/invalidate")
def invalidate(
    calc_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    reason: str = "invalidado",
):
    row = _run(
        lambda: services.invalidate_calculation(
            session, principal, calc_id, reason, idempotency_key=idempotency_key
        )
    )
    return {"data": calculation_out(row, invalidated=True)}


@router.get("/pricing/simulations")
def list_simulations(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [simulation_out(row) for row in _run(lambda: services.list_simulations(session, principal))]}


@router.post("/costing/calculations/{calc_id}/simulations")
def simulate(
    calc_id: UUID,
    body: SimulateBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.simulate_price(
            session, principal, calc_id, body.model_dump(), idempotency_key=idempotency_key
        )
    )
    return {"data": simulation_out(row)}


@router.get("/pricing/practiced")
def list_prices(
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return {"items": [price_out(row) for row in _run(lambda: services.list_prices(session, principal))]}


@router.post("/pricing/practiced")
def create_price(
    body: PracticedBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
):
    row = _run(
        lambda: services.create_practiced_price(
            session, principal, body.model_dump(), idempotency_key=idempotency_key
        )
    )
    return {"data": price_out(row), "row_version": row.row_version}


@router.post("/pricing/practiced/{price_id}/decide")
def decide_price(
    price_id: UUID,
    body: DecideBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[UUID, Depends(_command_keys)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    row = _run(
        lambda: services.decide_price(
            session,
            principal,
            price_id,
            body.model_dump(),
            expected_version=parse_if_match(if_match, required=False),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": price_out(row), "row_version": row.row_version}
