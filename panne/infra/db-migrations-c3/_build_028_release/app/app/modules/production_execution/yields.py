from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_quantity
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    Principal,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_RECORD_YIELD,
    COMMAND_REVERSE_YIELD,
    EVENT_YIELD_RECORDED,
    YIELD_TYPES,
)
from app.modules.production_execution.models import ProductionYieldMeasurement
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import ProductionBatch, ProductionOrder
from app.modules.production_planning.support import as_decimal, require_positive


def record_yield(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    measurement_type: str,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
    notes: str | None = None,
) -> ProductionYieldMeasurement:
    permit(principal, PERMISSION_PRODUCTION_STEP_EXECUTE)
    organization_id = org_id(principal)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_RECORD_YIELD)
    if replay is not None:
        found = session.scalar(
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.organization_id == organization_id,
                ProductionYieldMeasurement.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    if measurement_type not in YIELD_TYPES:
        raise ValidationError("tipo de rendimento inválido")
    batch = session.get(ProductionBatch, batch_id)
    if batch is None or batch.organization_id != organization_id:
        raise ValidationError("batelada inválida")
    unit = session.get(MeasurementUnit, measurement_unit_id)
    if unit is None:
        raise ValidationError("unidade incompatível")
    if measurement_type.endswith("mass") or measurement_type in {"leftover", "scrap", "other"}:
        if unit.dimension != "mass":
            raise ValidationError("unidade incompatível")
    amount = require_positive(quantize_quantity(as_decimal(quantity, "quantidade")), "quantidade")
    order = session.get(ProductionOrder, batch.production_order_id)
    assert order is not None
    row = ProductionYieldMeasurement(
        organization_id=organization_id,
        production_order_id=order.id,
        production_batch_id=batch.id,
        measurement_type=measurement_type,
        quantity=amount,
        measurement_unit_id=unit.id,
        unit_code=unit.code,
        actor_user_id=principal.user_id,
        occurred_at=now(),
        notes=notes.strip() if notes else None,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_YIELD_RECORDED,
        command=COMMAND_RECORD_YIELD,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"measurement_id": str(row.id), "measurement_type": measurement_type},
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch.id,
    )
    return row


def reverse_yield(
    session: Session,
    principal: Principal,
    *,
    measurement_id: UUID,
    idempotency_key: UUID,
    notes: str | None = None,
) -> ProductionYieldMeasurement:
    permit(principal, PERMISSION_PRODUCTION_STEP_EXECUTE)
    organization_id = org_id(principal)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_REVERSE_YIELD)
    if replay is not None:
        found = session.scalar(
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.organization_id == organization_id,
                ProductionYieldMeasurement.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    original = session.get(ProductionYieldMeasurement, measurement_id)
    if original is None or original.organization_id != organization_id:
        raise ValidationError("medição inválida")
    if original.reverses_id is not None:
        raise ValidationError("medição inválida")
    order = session.get(ProductionOrder, original.production_order_id)
    assert order is not None
    row = ProductionYieldMeasurement(
        organization_id=organization_id,
        production_order_id=original.production_order_id,
        production_batch_id=original.production_batch_id,
        measurement_type=original.measurement_type,
        quantity=original.quantity,
        measurement_unit_id=original.measurement_unit_id,
        unit_code=original.unit_code,
        actor_user_id=principal.user_id,
        occurred_at=now(),
        notes=notes.strip() if notes else None,
        reverses_id=original.id,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_YIELD_RECORDED,
        command=COMMAND_REVERSE_YIELD,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"measurement_id": str(row.id), "measurement_type": original.measurement_type},
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=original.production_batch_id,
    )
    return row
