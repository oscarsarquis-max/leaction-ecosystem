from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.agenda import service
from app.modules.agenda.schemas import (
    AgendaBoardOut,
    AgendaEventCreate,
    AgendaEventOut,
    AgendaEventUpdate,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get(
    "/board",
    response_model=AgendaBoardOut,
    operation_id="getAgendaBoard",
    summary="Organization agenda board (calendar + day + overdue)",
)
def get_board(
    ctx: OrgContextDep,
    selected_date: date | None = Query(default=None),
) -> AgendaBoardOut:
    return service.get_board(ctx, selected_date)


@router.post(
    "/sync",
    response_model=dict,
    operation_id="syncAgendaAutoEvents",
    summary="Sync automatic events from domain dates",
)
def sync_auto(ctx: OrgContextDep) -> dict:
    n = service.sync_auto_events(ctx)
    return {"synced": n}


@router.get(
    "/events",
    response_model=list[AgendaEventOut],
    operation_id="listAgendaEvents",
)
def list_events(
    ctx: OrgContextDep,
    day: date = Query(..., description="Day in organization timezone (YYYY-MM-DD)"),
) -> list[AgendaEventOut]:
    return service.list_events(ctx, day)


@router.get(
    "/events/{event_id}",
    response_model=AgendaEventOut,
    operation_id="getAgendaEvent",
    responses={404: ERROR_RESPONSES[404]},
)
def get_event(event_id: UUID, ctx: OrgContextDep) -> AgendaEventOut:
    return service.get_event(ctx, event_id)


@router.post(
    "/events",
    response_model=AgendaEventOut,
    status_code=201,
    operation_id="createAgendaEvent",
    responses={400: ERROR_RESPONSES[400], 403: ERROR_RESPONSES[403]},
)
def create_event(
    payload: AgendaEventCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AgendaEventOut:
    return service.create_event(ctx, payload)


@router.patch(
    "/events/{event_id}",
    response_model=AgendaEventOut,
    operation_id="updateAgendaEvent",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def update_event(
    event_id: UUID,
    payload: AgendaEventUpdate,
    ctx: OrgContextDep,
) -> AgendaEventOut:
    return service.update_event(ctx, event_id, payload)
