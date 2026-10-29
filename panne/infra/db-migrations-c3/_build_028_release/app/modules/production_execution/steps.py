from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    Principal,
)
from app.modules.production_execution.access import (
    bump,
    lock_batch,
    lock_order,
    now,
    org_id,
    permit,
)
from app.modules.production_execution.constants import (
    COMMAND_CANCEL_STEP,
    COMMAND_COMPLETE_STEP,
    COMMAND_HOLD_STEP,
    COMMAND_MARK_STEP_READY,
    COMMAND_RESUME_STEP,
    COMMAND_SKIP_STEP,
    COMMAND_START_STEP,
    EVENT_STEP_TRANSITIONED,
    STEP_CANCELLED,
    STEP_COMPLETED,
    STEP_IN_PROGRESS,
    STEP_ON_HOLD,
    STEP_PENDING,
    STEP_READY,
    STEP_SKIPPED,
)
from app.modules.production_execution.dependencies import assert_execution_dependencies
from app.modules.production_execution.models import (
    ProductionStepExecution,
    ProductionStepExecutionEvent,
)
from app.modules.production_planning.constants import (
    BATCH_STATUS_IN_PROGRESS,
    BATCH_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_READY,
)
from app.modules.production_planning.errors import (
    ConcurrencyError,
    InvalidStateError,
    ValidationError,
)
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import ProductionOrderStep
from app.modules.production_planning.support import as_decimal

_TRANSITIONS = {
    (STEP_PENDING, STEP_READY): COMMAND_MARK_STEP_READY,
    (STEP_READY, STEP_IN_PROGRESS): COMMAND_START_STEP,
    (STEP_IN_PROGRESS, STEP_ON_HOLD): COMMAND_HOLD_STEP,
    (STEP_ON_HOLD, STEP_IN_PROGRESS): COMMAND_RESUME_STEP,
    (STEP_IN_PROGRESS, STEP_COMPLETED): COMMAND_COMPLETE_STEP,
    (STEP_READY, STEP_SKIPPED): COMMAND_SKIP_STEP,
    (STEP_PENDING, STEP_SKIPPED): COMMAND_SKIP_STEP,
    (STEP_PENDING, STEP_CANCELLED): COMMAND_CANCEL_STEP,
    (STEP_READY, STEP_CANCELLED): COMMAND_CANCEL_STEP,
    (STEP_ON_HOLD, STEP_CANCELLED): COMMAND_CANCEL_STEP,
}


def _execution(
    session: Session, batch_id: UUID, step_id: UUID, organization_id: UUID, order_id: UUID
) -> ProductionStepExecution:
    row = session.scalar(
        select(ProductionStepExecution)
        .where(
            ProductionStepExecution.production_batch_id == batch_id,
            ProductionStepExecution.production_order_step_id == step_id,
        )
        .with_for_update()
    )
    if row is None:
        row = ProductionStepExecution(
            organization_id=organization_id,
            production_order_id=order_id,
            production_batch_id=batch_id,
            production_order_step_id=step_id,
            status=STEP_PENDING,
        )
        session.add(row)
        session.flush()
        row = session.scalar(
            select(ProductionStepExecution)
            .where(ProductionStepExecution.id == row.id)
            .with_for_update()
        )
        assert row is not None
    return row


def _previous_done(session: Session, batch_id: UUID, step: ProductionOrderStep) -> bool:
    previous = list(
        session.scalars(
            select(ProductionOrderStep)
            .where(
                ProductionOrderStep.production_order_id == step.production_order_id,
                ProductionOrderStep.sequence < step.sequence,
            )
            .order_by(ProductionOrderStep.sequence)
        )
    )
    for prior in previous:
        run = session.scalar(
            select(ProductionStepExecution).where(
                ProductionStepExecution.production_batch_id == batch_id,
                ProductionStepExecution.production_order_step_id == prior.id,
            )
        )
        if run is None or run.status not in {STEP_COMPLETED, STEP_SKIPPED}:
            return False
    return True


def _transition(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    target: str,
    command: str,
    idempotency_key: UUID,
    expected_row_version: int | None,
    notes: str | None = None,
    measured_temperature: Decimal | int | str | None = None,
    measured_time_seconds: int | None = None,
    require_reason: bool = False,
) -> ProductionStepExecution:
    permit(principal, PERMISSION_PRODUCTION_STEP_EXECUTE)
    organization_id = org_id(principal)
    replay = existing_idempotent(session, organization_id, idempotency_key, command)
    batch = lock_batch(session, batch_id, organization_id, None)
    order = lock_order(session, batch.production_order_id, organization_id, None)
    step = session.get(ProductionOrderStep, order_step_id)
    if step is None or step.organization_id != organization_id:
        raise ValidationError("etapa inválida")
    if step.production_order_id != order.id:
        raise ValidationError("etapa inválida")
    run = _execution(session, batch.id, step.id, organization_id, order.id)
    if replay is not None:
        return run
    if expected_row_version is not None and run.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    if require_reason and not (notes and notes.strip()):
        raise ValidationError("motivo obrigatório")
    allowed = {
        src for (src, dest), cmd in _TRANSITIONS.items() if dest == target and cmd == command
    }
    if run.status not in allowed:
        raise InvalidStateError("transicao_invalida")
    if target in {STEP_READY, STEP_IN_PROGRESS} and not _previous_done(session, batch.id, step):
        raise InvalidStateError("sequencia_bloqueada")
    if target == STEP_IN_PROGRESS:
        if order.status not in {ORDER_STATUS_READY, ORDER_STATUS_IN_PROGRESS}:
            raise InvalidStateError("transicao_invalida")
        if batch.status not in {BATCH_STATUS_READY, BATCH_STATUS_IN_PROGRESS}:
            raise InvalidStateError("transicao_invalida")
        assert_execution_dependencies(session, order)
    from_status = run.status
    run.status = target
    run.operator_user_id = principal.user_id
    run.notes = notes.strip() if notes else run.notes
    if measured_temperature is not None:
        run.measured_temperature = as_decimal(measured_temperature, "temperatura")
    if measured_time_seconds is not None:
        run.measured_time_seconds = measured_time_seconds
    if target == STEP_IN_PROGRESS and run.started_at is None:
        run.started_at = now()
    if target in {STEP_COMPLETED, STEP_SKIPPED, STEP_CANCELLED}:
        run.ended_at = now()
        if run.started_at is not None:
            run.measured_duration_seconds = int((run.ended_at - run.started_at).total_seconds())
    bump(run)
    session.add(
        ProductionStepExecutionEvent(
            organization_id=organization_id,
            execution_id=run.id,
            from_status=from_status,
            to_status=target,
            actor_user_id=principal.user_id,
            occurred_at=now(),
            notes=notes.strip() if notes else None,
        )
    )
    if target == STEP_IN_PROGRESS:
        if batch.status == BATCH_STATUS_READY:
            batch.status = BATCH_STATUS_IN_PROGRESS
            batch.started_at = batch.started_at or now()
            bump(batch)
        if order.status == ORDER_STATUS_READY:
            order.status = ORDER_STATUS_IN_PROGRESS
            bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_STEP_TRANSITIONED,
        command=command,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"execution_id": str(run.id), "from_status": from_status, "to_status": target},
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch.id,
    )
    return run


def mark_step_ready(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_READY,
        command=COMMAND_MARK_STEP_READY,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
    )


def start_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
    measured_temperature: Decimal | int | str | None = None,
    measured_time_seconds: int | None = None,
    notes: str | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_IN_PROGRESS,
        command=COMMAND_START_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
        notes=notes,
        measured_temperature=measured_temperature,
        measured_time_seconds=measured_time_seconds,
    )


def hold_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_ON_HOLD,
        command=COMMAND_HOLD_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
        notes=reason,
        require_reason=True,
    )


def resume_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_IN_PROGRESS,
        command=COMMAND_RESUME_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
    )


def complete_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
    notes: str | None = None,
    measured_temperature: Decimal | int | str | None = None,
    measured_time_seconds: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_COMPLETED,
        command=COMMAND_COMPLETE_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
        notes=notes,
        measured_temperature=measured_temperature,
        measured_time_seconds=measured_time_seconds,
    )


def skip_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_SKIPPED,
        command=COMMAND_SKIP_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
        notes=reason,
        require_reason=True,
    )


def cancel_step(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    order_step_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionStepExecution:
    return _transition(
        session,
        principal,
        batch_id=batch_id,
        order_step_id=order_step_id,
        target=STEP_CANCELLED,
        command=COMMAND_CANCEL_STEP,
        idempotency_key=idempotency_key,
        expected_row_version=expected_row_version,
        notes=reason,
        require_reason=True,
    )
