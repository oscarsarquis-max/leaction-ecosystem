from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_OCCURRENCE_RECORD,
    PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE,
    Principal,
)
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_RECORD_OCCURRENCE,
    COMMAND_RESOLVE_OCCURRENCE,
    EVENT_OCCURRENCE_RECORDED,
    EVENT_OCCURRENCE_RESOLVED,
    OCCURRENCE_CATEGORIES,
    OCCURRENCE_OPEN,
    OCCURRENCE_RESOLVED,
    SEVERITIES,
)
from app.modules.production_execution.models import ProductionOccurrence, ProductionOccurrenceEvent
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionOrder,
    ProductionOrderStep,
)


def record_occurrence(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    category: str,
    severity: str,
    description: str,
    idempotency_key: UUID,
    is_blocking: bool = False,
    batch_id: UUID | None = None,
    order_step_id: UUID | None = None,
    evidence_refs: list | None = None,
) -> ProductionOccurrence:
    permit(principal, PERMISSION_PRODUCTION_OCCURRENCE_RECORD)
    organization_id = org_id(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_RECORD_OCCURRENCE
    )
    if replay is not None:
        found = session.get(ProductionOccurrence, UUID(replay.payload["occurrence_id"]))
        if found is not None:
            return found
    if category not in OCCURRENCE_CATEGORIES:
        raise ValidationError("categoria inválida")
    if severity not in SEVERITIES:
        raise ValidationError("severidade inválida")
    if not description or not description.strip():
        raise ValidationError("descrição obrigatória")
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if batch_id is not None:
        batch = session.get(ProductionBatch, batch_id)
        if batch is None or batch.production_order_id != order.id:
            raise ValidationError("batelada inválida")
    if order_step_id is not None:
        step = session.get(ProductionOrderStep, order_step_id)
        if step is None or step.production_order_id != order.id:
            raise ValidationError("etapa inválida")
    row = ProductionOccurrence(
        organization_id=organization_id,
        production_order_id=order.id,
        production_batch_id=batch_id,
        production_order_step_id=order_step_id,
        category=category,
        severity=severity,
        description=description.strip(),
        is_blocking=is_blocking,
        status=OCCURRENCE_OPEN,
        opened_by_user_id=principal.user_id,
        opened_at=now(),
        evidence_refs=evidence_refs or [],
    )
    session.add(row)
    session.flush()
    session.add(
        ProductionOccurrenceEvent(
            organization_id=organization_id,
            occurrence_id=row.id,
            event_type="opened",
            actor_user_id=principal.user_id,
            occurred_at=now(),
        )
    )
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_OCCURRENCE_RECORDED,
        command=COMMAND_RECORD_OCCURRENCE,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "occurrence_id": str(row.id),
            "category": category,
            "blocking": "true" if is_blocking else "false",
        },
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch_id,
    )
    return row


def resolve_occurrence(
    session: Session,
    principal: Principal,
    *,
    occurrence_id: UUID,
    notes: str,
    idempotency_key: UUID,
) -> ProductionOccurrence:
    permit(principal, PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE)
    organization_id = org_id(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_RESOLVE_OCCURRENCE
    )
    row = session.get(ProductionOccurrence, occurrence_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("ocorrência inválida")
    if replay is not None:
        return row
    if not notes or not notes.strip():
        raise ValidationError("motivo obrigatório")
    if row.status != OCCURRENCE_OPEN:
        raise InvalidStateError("transicao_invalida")
    row.status = OCCURRENCE_RESOLVED
    session.add(
        ProductionOccurrenceEvent(
            organization_id=organization_id,
            occurrence_id=row.id,
            event_type="resolved",
            actor_user_id=principal.user_id,
            occurred_at=now(),
            notes=notes.strip(),
        )
    )
    order = session.get(ProductionOrder, row.production_order_id)
    assert order is not None
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_OCCURRENCE_RESOLVED,
        command=COMMAND_RESOLVE_OCCURRENCE,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"occurrence_id": str(row.id)},
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=row.production_batch_id,
    )
    return row


def open_blocking_occurrences(session: Session, order_id: UUID) -> list[ProductionOccurrence]:
    return list(
        session.scalars(
            select(ProductionOccurrence).where(
                ProductionOccurrence.production_order_id == order_id,
                ProductionOccurrence.is_blocking.is_(True),
                ProductionOccurrence.status == OCCURRENCE_OPEN,
            )
        )
    )
