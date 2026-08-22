from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production_execution.constants import EVENT_PAYLOADS as EXECUTION_EVENT_PAYLOADS
from app.modules.production_planning.constants import (
    EVENT_PAYLOADS as PLANNING_EVENT_PAYLOADS,
)
from app.modules.production_planning.constants import SNAPSHOT_SCHEMA_VERSION
from app.modules.production_planning.errors import IdempotencyConflictError, ValidationError
from app.modules.production_planning.models import ProductionEvent
from app.modules.production_planning.support import digest

EVENT_PAYLOADS = {**PLANNING_EVENT_PAYLOADS, **EXECUTION_EVENT_PAYLOADS}


def validate_payload(event_type: str, payload: dict) -> dict:
    allowed = EVENT_PAYLOADS.get(event_type)
    if allowed is None:
        raise ValidationError("tipo de evento desconhecido")
    extra = set(payload) - allowed
    if extra:
        raise ValidationError("campo extra no evento")
    missing = allowed - set(payload)
    if missing:
        raise ValidationError("payload incompleto")
    return payload


def lookup_idempotent(
    session: Session, organization_id: UUID, idempotency_key: UUID
) -> ProductionEvent | None:
    return session.scalar(
        select(ProductionEvent).where(
            ProductionEvent.organization_id == organization_id,
            ProductionEvent.idempotency_key == idempotency_key,
        )
    )


def existing_idempotent(
    session: Session,
    organization_id: UUID,
    idempotency_key: UUID,
    command: str,
    payload: dict | None = None,
) -> ProductionEvent | None:
    row = lookup_idempotent(session, organization_id, idempotency_key)
    if row is None:
        return None
    if row.command != command:
        raise IdempotencyConflictError("idempotencia_conflito")
    if payload is not None and row.payload_digest != digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def append_event(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID,
    event_type: str,
    command: str,
    actor_user_id: UUID,
    idempotency_key: UUID,
    payload: dict,
    plan_id: UUID | None = None,
    order_id: UUID | None = None,
    batch_id: UUID | None = None,
    correlation_id: UUID | None = None,
    causation_event_id: UUID | None = None,
) -> ProductionEvent:
    clean = validate_payload(event_type, payload)
    replay = existing_idempotent(session, organization_id, idempotency_key, command, clean)
    if replay is not None:
        return replay
    row = ProductionEvent(
        organization_id=organization_id,
        establishment_id=establishment_id,
        plan_id=plan_id,
        order_id=order_id,
        batch_id=batch_id,
        event_type=event_type,
        command=command,
        actor_user_id=actor_user_id,
        correlation_id=correlation_id,
        causation_event_id=causation_event_id,
        idempotency_key=idempotency_key,
        payload=clean,
        payload_digest=digest(clean),
        schema_version=SNAPSHOT_SCHEMA_VERSION,
    )
    session.add(row)
    session.flush()
    return row
