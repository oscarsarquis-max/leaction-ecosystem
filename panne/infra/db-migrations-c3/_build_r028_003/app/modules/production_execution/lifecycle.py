from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_BATCH_COMPLETE,
    PERMISSION_PRODUCTION_ORDER_COMPLETE,
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE,
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
    COMMAND_COMPLETE_BATCH,
    COMMAND_COMPLETE_ORDER,
    COMMAND_MARK_READY,
    COMMAND_RESUME_ORDER,
    COMMAND_SHORT_CLOSE_ORDER,
    EVENT_BATCH_STATUS_CHANGED,
    EVENT_ORDER_COMPLETED,
    EVENT_ORDER_READY,
    EVENT_ORDER_RESUMED,
    EVENT_ORDER_SHORT_CLOSED,
    POLICY_WEIGHING_NOT_APPLICABLE,
    POLICY_WEIGHING_OPTIONAL,
    POLICY_WEIGHING_REQUIRED,
    SESSION_OPEN,
    STEP_COMPLETED,
    STEP_SKIPPED,
    VERIFICATION_SECOND_PERSON,
)
from app.modules.production_execution.dependencies import assert_execution_dependencies
from app.modules.production_execution.models import (
    ProductionStepExecution,
    ProductionWeighingSession,
)
from app.modules.production_execution.occurrences import open_blocking_occurrences
from app.modules.production_execution.policy import require_policy
from app.modules.production_execution.projections import (
    current_weighing_entries,
    effective_weighed_quantity,
    material_accepted,
    project_consumption,
    project_yield,
    within_completion_tolerance,
)
from app.modules.production_planning.constants import (
    BATCH_STATUS_COMPLETED,
    BATCH_STATUS_IN_PROGRESS,
    BATCH_STATUS_IN_WEIGHING,
    BATCH_STATUS_ON_HOLD,
    BATCH_STATUS_PENDING,
    BATCH_STATUS_READY,
    BATCH_STATUS_SHORT_CLOSED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_READY,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SHORT_CLOSED,
)
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionOrder,
    ProductionOrderStep,
)


def _weighing_satisfied(session: Session, order: ProductionOrder, batch: ProductionBatch) -> bool:
    policy = require_policy(session, order.id)
    open_session = session.scalar(
        select(ProductionWeighingSession).where(
            ProductionWeighingSession.production_batch_id == batch.id,
            ProductionWeighingSession.status == SESSION_OPEN,
        )
    )
    if open_session is not None:
        return False
    materials = list(
        session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_batch_id == batch.id
            )
        )
    )
    if policy.weighing_policy == POLICY_WEIGHING_NOT_APPLICABLE:
        return True
    if policy.weighing_policy == POLICY_WEIGHING_OPTIONAL:
        for material in materials:
            if current_weighing_entries(session, material.id):
                if (
                    policy.verification_policy == VERIFICATION_SECOND_PERSON
                    and not material_accepted(session, material.id)
                ):
                    return False
        return True
    if policy.weighing_policy != POLICY_WEIGHING_REQUIRED:
        return False
    for material in materials:
        if effective_weighed_quantity(session, material.id) <= 0:
            return False
        if policy.verification_policy == VERIFICATION_SECOND_PERSON:
            if not material_accepted(session, material.id):
                return False
    return True


def _steps_done(session: Session, batch: ProductionBatch) -> bool:
    steps = list(
        session.scalars(
            select(ProductionOrderStep).where(
                ProductionOrderStep.production_order_id == batch.production_order_id
            )
        )
    )
    if not steps:
        return False
    for step in steps:
        run = session.scalar(
            select(ProductionStepExecution).where(
                ProductionStepExecution.production_batch_id == batch.id,
                ProductionStepExecution.production_order_step_id == step.id,
            )
        )
        if run is None or run.status not in {STEP_COMPLETED, STEP_SKIPPED}:
            return False
    return True


def _minimum_consumption(session: Session, batch: ProductionBatch) -> bool:
    materials = list(
        session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_batch_id == batch.id
            )
        )
    )
    return any(project_consumption(session, material.id)["consume"] > 0 for material in materials)


def _assert_completable(session: Session, order: ProductionOrder, batch: ProductionBatch) -> None:
    if not _weighing_satisfied(session, order, batch):
        raise ValidationError("pesagem incompleta")
    if not _steps_done(session, batch):
        raise ValidationError("etapas incompletas")
    if not _minimum_consumption(session, batch):
        raise ValidationError("consumo mínimo ausente")
    projection = project_yield(session, batch)
    if projection.completeness != "complete":
        raise ValidationError("rendimento incompleto")
    if open_blocking_occurrences(session, order.id):
        raise InvalidStateError("ocorrencia_bloqueante")
    assert_execution_dependencies(session, order)


def mark_order_ready(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = org_id(principal)
    order = lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_MARK_READY)
    if replay is not None:
        return order
    if order.status not in {ORDER_STATUS_RELEASED, ORDER_STATUS_IN_WEIGHING}:
        raise InvalidStateError("transicao_invalida")
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    for batch in batches:
        if not _weighing_satisfied(session, order, batch):
            raise ValidationError("pesagem incompleta")
        if batch.status in {BATCH_STATUS_PENDING, BATCH_STATUS_IN_WEIGHING}:
            batch.status = BATCH_STATUS_READY
            bump(batch)
    order.status = ORDER_STATUS_READY
    bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_READY,
        command=COMMAND_MARK_READY,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"public_code": order.public_code},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def resume_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = org_id(principal)
    order = lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_RESUME_ORDER)
    if replay is not None:
        return order
    if order.status != ORDER_STATUS_ON_HOLD:
        raise InvalidStateError("transicao_invalida")
    target = order.held_from_status or ORDER_STATUS_RELEASED
    order.status = target
    order.hold_reason = None
    bump(order)
    for batch in session.scalars(
        select(ProductionBatch).where(
            ProductionBatch.production_order_id == order.id,
            ProductionBatch.status == BATCH_STATUS_ON_HOLD,
        )
    ):
        batch.status = batch.held_from_status or BATCH_STATUS_IN_PROGRESS
        bump(batch)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_RESUMED,
        command=COMMAND_RESUME_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"public_code": order.public_code},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def complete_batch(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionBatch:
    permit(principal, PERMISSION_PRODUCTION_BATCH_COMPLETE)
    organization_id = org_id(principal)
    batch = lock_batch(session, batch_id, organization_id, expected_row_version)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_COMPLETE_BATCH)
    if replay is not None:
        return batch
    order = lock_order(session, batch.production_order_id, organization_id, None)
    if batch.status not in {BATCH_STATUS_IN_PROGRESS, BATCH_STATUS_READY}:
        raise InvalidStateError("transicao_invalida")
    _assert_completable(session, order, batch)
    policy = require_policy(session, order.id)
    projection = project_yield(session, batch)
    if not within_completion_tolerance(
        projection, batch.target_quantity, policy.completion_tolerance
    ):
        raise ValidationError("resultado fora da tolerância")
    previous = batch.status
    batch.status = BATCH_STATUS_COMPLETED
    batch.completed_at = now()
    bump(batch)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_BATCH_STATUS_CHANGED,
        command=COMMAND_COMPLETE_BATCH,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "batch_id": str(batch.id),
            "from_status": previous,
            "to_status": BATCH_STATUS_COMPLETED,
        },
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch.id,
    )
    return batch


def complete_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    permit(principal, PERMISSION_PRODUCTION_ORDER_COMPLETE)
    organization_id = org_id(principal)
    order = lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_COMPLETE_ORDER)
    if replay is not None:
        return order
    if order.status not in {ORDER_STATUS_IN_PROGRESS, ORDER_STATUS_READY}:
        raise InvalidStateError("transicao_invalida")
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    if any(batch.status == BATCH_STATUS_SHORT_CLOSED for batch in batches):
        raise InvalidStateError("short_closed_nao_e_conclusao")
    policy = require_policy(session, order.id)
    digests: list[str] = []
    for batch in batches:
        if batch.status != BATCH_STATUS_COMPLETED:
            _assert_completable(session, order, batch)
            projection = project_yield(session, batch)
            if not within_completion_tolerance(
                projection, batch.target_quantity, policy.completion_tolerance
            ):
                raise ValidationError("resultado fora da tolerância")
            batch.status = BATCH_STATUS_COMPLETED
            batch.completed_at = now()
            bump(batch)
        else:
            projection = project_yield(session, batch)
        digests.append(projection.digest())
    order.status = ORDER_STATUS_COMPLETED
    order.completed_at = now()
    order.completed_by_user_id = principal.user_id
    bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_COMPLETED,
        command=COMMAND_COMPLETE_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"public_code": order.public_code, "result_digest": "".join(digests)},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def short_close_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    permit(principal, PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE)
    organization_id = org_id(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    order = lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_SHORT_CLOSE_ORDER
    )
    if replay is not None:
        return order
    if order.status not in {
        ORDER_STATUS_RELEASED,
        ORDER_STATUS_IN_PROGRESS,
        ORDER_STATUS_READY,
        ORDER_STATUS_IN_WEIGHING,
        ORDER_STATUS_ON_HOLD,
    }:
        raise InvalidStateError("transicao_invalida")
    policy = require_policy(session, order.id)
    if not policy.allow_short_close:
        raise InvalidStateError("encerramento_nao_permitido")
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    digests: list[str] = []
    all_within = True
    for batch in batches:
        projection = project_yield(session, batch)
        digests.append(projection.digest())
        if not within_completion_tolerance(
            projection, batch.target_quantity, policy.completion_tolerance
        ):
            all_within = False
        if batch.status not in {BATCH_STATUS_COMPLETED, BATCH_STATUS_SHORT_CLOSED}:
            batch.status = BATCH_STATUS_SHORT_CLOSED
            batch.short_closed_at = now()
            bump(batch)
    if all_within and all(
        project_yield(session, batch).completeness == "complete" for batch in batches
    ):
        raise ValidationError("use conclusão normal")
    order.status = ORDER_STATUS_SHORT_CLOSED
    order.short_closed_at = now()
    order.short_closed_by_user_id = principal.user_id
    order.short_close_reason = reason.strip()
    bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_SHORT_CLOSED,
        command=COMMAND_SHORT_CLOSE_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "public_code": order.public_code,
            "reason": reason.strip(),
            "result_digest": "".join(digests),
        },
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order
