"""HTTP routes — Agile Action Execution Workspace (ISOI-007)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.agenda import service as agenda_service
from app.modules.agenda.schemas import AgendaEventOut
from app.modules.agile import board, ceremonies, execution, service
from app.modules.agile.schemas import (
    BoardMoveIn,
    BoardMoveOut,
    BoardOut,
    CeremonyRecordCreate,
    CeremonyRecordOut,
    CheckInCreate,
    CheckInOut,
    DependencyCreate,
    DependencyOut,
    ImpedimentCreate,
    ImpedimentOut,
    ImpedimentUpdate,
    SprintActivateIn,
    SprintCardAllocateIn,
    SprintCardOut,
    SprintCardPositionIn,
    SprintCardRemoveIn,
    SprintCompleteIn,
    SprintCreate,
    SprintMetricsOut,
    SprintOut,
    SprintUpdate,
    SquadCreate,
    SquadMembershipCreate,
    SquadMembershipOut,
    SquadMembershipUpdate,
    SquadOut,
    SquadUpdate,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(prefix="/organizations", tags=["agile"])


# --- Squads ---


@router.post(
    "/current/agile/squads",
    response_model=SquadOut,
    status_code=201,
    operation_id="createAgileSquad",
    responses={403: ERROR_RESPONSES[403], 422: ERROR_RESPONSES[422]},
)
def create_squad(payload: SquadCreate, ctx: OrgContextDep) -> SquadOut:
    return service.create_squad(ctx, payload)


@router.get(
    "/current/agile/squads",
    response_model=list[SquadOut],
    operation_id="listAgileSquads",
)
def list_squads(
    ctx: OrgContextDep,
    status: str | None = Query(default=None),
) -> list[SquadOut]:
    return service.list_squads(ctx, status=status)


@router.get(
    "/current/agile/squads/{squad_id}",
    response_model=SquadOut,
    operation_id="getAgileSquad",
    responses={404: ERROR_RESPONSES[404]},
)
def get_squad(squad_id: UUID, ctx: OrgContextDep) -> SquadOut:
    return service.get_squad(ctx, squad_id)


@router.patch(
    "/current/agile/squads/{squad_id}",
    response_model=SquadOut,
    operation_id="patchAgileSquad",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def patch_squad(
    squad_id: UUID, payload: SquadUpdate, ctx: OrgContextDep
) -> SquadOut:
    return service.update_squad(ctx, squad_id, payload)


@router.post(
    "/current/agile/squads/{squad_id}/memberships",
    response_model=SquadMembershipOut,
    status_code=201,
    operation_id="addAgileSquadMembership",
    responses={403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def add_squad_membership(
    squad_id: UUID, payload: SquadMembershipCreate, ctx: OrgContextDep
) -> SquadMembershipOut:
    return service.add_squad_membership(ctx, squad_id, payload)


@router.get(
    "/current/agile/squads/{squad_id}/memberships",
    response_model=list[SquadMembershipOut],
    operation_id="listAgileSquadMemberships",
)
def list_squad_memberships(squad_id: UUID, ctx: OrgContextDep) -> list[SquadMembershipOut]:
    return service.list_squad_memberships(ctx, squad_id)


@router.patch(
    "/current/agile/squads/{squad_id}/memberships/{membership_id}",
    response_model=SquadMembershipOut,
    operation_id="patchAgileSquadMembership",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def patch_squad_membership(
    squad_id: UUID,
    membership_id: UUID,
    payload: SquadMembershipUpdate,
    ctx: OrgContextDep,
) -> SquadMembershipOut:
    return service.update_squad_membership(ctx, squad_id, membership_id, payload)


# --- Sprints ---


@router.post(
    "/current/agile/sprints",
    response_model=SprintOut,
    status_code=201,
    operation_id="createAgileSprint",
)
def create_sprint(payload: SprintCreate, ctx: OrgContextDep) -> SprintOut:
    return service.create_sprint(ctx, payload)


@router.get(
    "/current/agile/sprints",
    response_model=list[SprintOut],
    operation_id="listAgileSprints",
)
def list_sprints(
    ctx: OrgContextDep,
    squad_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[SprintOut]:
    return service.list_sprints(ctx, squad_id=squad_id, status=status)


@router.get(
    "/current/agile/sprints/{sprint_id}",
    response_model=SprintOut,
    operation_id="getAgileSprint",
    responses={404: ERROR_RESPONSES[404]},
)
def get_sprint(sprint_id: UUID, ctx: OrgContextDep) -> SprintOut:
    return service.get_sprint(ctx, sprint_id)


@router.patch(
    "/current/agile/sprints/{sprint_id}",
    response_model=SprintOut,
    operation_id="patchAgileSprint",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def patch_sprint(
    sprint_id: UUID, payload: SprintUpdate, ctx: OrgContextDep
) -> SprintOut:
    return service.update_sprint(ctx, sprint_id, payload)


@router.post(
    "/current/agile/sprints/{sprint_id}/activate",
    response_model=SprintOut,
    operation_id="activateAgileSprint",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def activate_sprint(
    sprint_id: UUID,
    ctx: OrgContextDep,
    payload: SprintActivateIn | None = None,
) -> SprintOut:
    return service.activate_sprint(ctx, sprint_id, payload)


@router.post(
    "/current/agile/sprints/{sprint_id}/complete",
    response_model=SprintOut,
    operation_id="completeAgileSprint",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def complete_sprint(
    sprint_id: UUID, payload: SprintCompleteIn, ctx: OrgContextDep
) -> SprintOut:
    return service.complete_sprint(ctx, sprint_id, payload)


@router.post(
    "/current/agile/sprints/{sprint_id}/cards",
    response_model=SprintCardOut,
    status_code=201,
    operation_id="allocateAgileSprintCard",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def allocate_card(
    sprint_id: UUID, payload: SprintCardAllocateIn, ctx: OrgContextDep
) -> SprintCardOut:
    return service.allocate_card(ctx, sprint_id, payload)


@router.delete(
    "/current/agile/sprints/{sprint_id}/cards/{action_item_id}",
    status_code=204,
    operation_id="removeAgileSprintCard",
    responses={404: ERROR_RESPONSES[404]},
)
def remove_card(
    sprint_id: UUID,
    action_item_id: UUID,
    ctx: OrgContextDep,
    payload: SprintCardRemoveIn | None = None,
) -> None:
    reason = payload.removal_reason if payload else ""
    service.remove_card(ctx, sprint_id, action_item_id, removal_reason=reason)


@router.patch(
    "/current/agile/sprints/{sprint_id}/cards/{action_item_id}/position",
    response_model=SprintCardOut,
    operation_id="repositionAgileSprintCard",
    responses={404: ERROR_RESPONSES[404]},
)
def reposition_card(
    sprint_id: UUID,
    action_item_id: UUID,
    payload: SprintCardPositionIn,
    ctx: OrgContextDep,
) -> SprintCardOut:
    return service.update_card_position(ctx, sprint_id, action_item_id, payload)


@router.get(
    "/current/agile/sprints/{sprint_id}/metrics",
    response_model=SprintMetricsOut,
    operation_id="getAgileSprintMetrics",
    responses={404: ERROR_RESPONSES[404]},
)
def sprint_metrics(sprint_id: UUID, ctx: OrgContextDep) -> SprintMetricsOut:
    return service.get_sprint_metrics(ctx, sprint_id)


@router.get(
    "/current/agile/sprints/{sprint_id}/agenda-events",
    response_model=list[AgendaEventOut],
    operation_id="listAgileSprintAgendaEvents",
    summary="Agenda events of one sprint (single call, no per-day fan-out)",
    responses={404: ERROR_RESPONSES[404]},
)
def list_sprint_agenda_events(
    sprint_id: UUID, ctx: OrgContextDep
) -> list[AgendaEventOut]:
    return agenda_service.list_sprint_events(ctx, sprint_id)


@router.post(
    "/current/agile/sprints/{sprint_id}/ceremony-records",
    response_model=CeremonyRecordOut,
    status_code=201,
    operation_id="createAgileCeremonyRecord",
)
def create_ceremony_record(
    sprint_id: UUID, payload: CeremonyRecordCreate, ctx: OrgContextDep
) -> CeremonyRecordOut:
    return ceremonies.create_ceremony_record(ctx, sprint_id, payload)


@router.get(
    "/current/agile/sprints/{sprint_id}/ceremony-records",
    response_model=list[CeremonyRecordOut],
    operation_id="listAgileCeremonyRecords",
)
def list_ceremony_records(
    sprint_id: UUID,
    ctx: OrgContextDep,
    ceremony_type: str | None = Query(default=None),
) -> list[CeremonyRecordOut]:
    return ceremonies.list_ceremony_records(ctx, sprint_id, ceremony_type=ceremony_type)


# --- Board ---


@router.get(
    "/current/agile/board",
    response_model=BoardOut,
    operation_id="getAgileBoard",
)
def get_board(
    ctx: OrgContextDep,
    squad_id: UUID | None = Query(default=None),
    sprint_id: UUID | None = Query(default=None),
) -> BoardOut:
    return board.get_board(ctx, squad_id=squad_id, sprint_id=sprint_id)


@router.post(
    "/current/agile/board/move",
    response_model=BoardMoveOut,
    operation_id="moveAgileBoardCard",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def move_board_card(payload: BoardMoveIn, ctx: OrgContextDep) -> BoardMoveOut:
    return board.move_card(ctx, payload)


# --- Action execution (check-ins, impediments, dependencies) ---


@router.post(
    "/current/actions/{action_item_id}/check-ins",
    response_model=CheckInOut,
    status_code=201,
    operation_id="createActionExecutionCheckIn",
)
def create_check_in(
    action_item_id: UUID,
    payload: CheckInCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> CheckInOut:
    if _idempotency_key and not payload.idempotency_key:
        payload = payload.model_copy(update={"idempotency_key": _idempotency_key})
    return execution.create_check_in(ctx, action_item_id, payload)


@router.get(
    "/current/actions/{action_item_id}/check-ins",
    response_model=list[CheckInOut],
    operation_id="listActionExecutionCheckIns",
)
def list_check_ins(action_item_id: UUID, ctx: OrgContextDep) -> list[CheckInOut]:
    return execution.list_check_ins(ctx, action_item_id)


@router.post(
    "/current/actions/{action_item_id}/impediments",
    response_model=ImpedimentOut,
    status_code=201,
    operation_id="createActionImpediment",
)
def create_impediment(
    action_item_id: UUID, payload: ImpedimentCreate, ctx: OrgContextDep
) -> ImpedimentOut:
    return execution.create_impediment(ctx, action_item_id, payload)


@router.get(
    "/current/actions/{action_item_id}/impediments",
    response_model=list[ImpedimentOut],
    operation_id="listActionImpediments",
)
def list_impediments(action_item_id: UUID, ctx: OrgContextDep) -> list[ImpedimentOut]:
    return execution.list_impediments(ctx, action_item_id)


@router.patch(
    "/current/actions/{action_item_id}/impediments/{impediment_id}",
    response_model=ImpedimentOut,
    operation_id="patchActionImpediment",
    responses={404: ERROR_RESPONSES[404]},
)
def patch_impediment(
    action_item_id: UUID,
    impediment_id: UUID,
    payload: ImpedimentUpdate,
    ctx: OrgContextDep,
) -> ImpedimentOut:
    return execution.update_impediment(ctx, action_item_id, impediment_id, payload)


@router.post(
    "/current/actions/{action_item_id}/dependencies",
    response_model=DependencyOut,
    status_code=201,
    operation_id="createActionDependency",
    responses={409: ERROR_RESPONSES[409]},
)
def create_dependency(
    action_item_id: UUID, payload: DependencyCreate, ctx: OrgContextDep
) -> DependencyOut:
    return execution.create_dependency(ctx, action_item_id, payload)


@router.get(
    "/current/actions/{action_item_id}/dependencies",
    response_model=list[DependencyOut],
    operation_id="listActionDependencies",
)
def list_dependencies(
    action_item_id: UUID,
    ctx: OrgContextDep,
    include_removed: bool = Query(
        default=False,
        description="Include soft-removed dependencies (history)",
    ),
) -> list[DependencyOut]:
    return execution.list_dependencies(
        ctx, action_item_id, include_removed=include_removed
    )


@router.delete(
    "/current/actions/{action_item_id}/dependencies/{dependency_id}",
    status_code=204,
    operation_id="deleteActionDependency",
    responses={404: ERROR_RESPONSES[404]},
)
def delete_dependency(
    action_item_id: UUID, dependency_id: UUID, ctx: OrgContextDep
) -> None:
    execution.delete_dependency(ctx, action_item_id, dependency_id)
