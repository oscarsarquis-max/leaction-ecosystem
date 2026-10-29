from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_percent, quantize_quantity
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    PERMISSION_PRODUCTION_WEIGHING_VERIFY,
    Principal,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_execution.access import (
    bump,
    lock_batch,
    lock_order,
    lock_session,
    now,
    org_id,
    permit,
)
from app.modules.production_execution.constants import (
    COMMAND_CANCEL_WEIGHING_SESSION,
    COMMAND_COMPLETE_WEIGHING_SESSION,
    COMMAND_CORRECT_WEIGHING,
    COMMAND_OPEN_WEIGHING_SESSION,
    COMMAND_RECORD_WEIGHING,
    COMMAND_REVERSE_WEIGHING,
    COMMAND_VERIFY_WEIGHING,
    ENTRY_CORRECTION,
    ENTRY_RECORD,
    ENTRY_REVERSAL,
    EVENT_WEIGHING_RECORDED,
    EVENT_WEIGHING_SESSION_CANCELLED,
    EVENT_WEIGHING_SESSION_COMPLETED,
    EVENT_WEIGHING_SESSION_OPENED,
    EVENT_WEIGHING_VERIFIED,
    SESSION_CANCELLED,
    SESSION_COMPLETED,
    SESSION_OPEN,
    VERIFY_DECISIONS,
    VERIFY_REJECTED,
)
from app.modules.production_execution.models import (
    ProductionWeighingEntry,
    ProductionWeighingSession,
    ProductionWeighingVerification,
)
from app.modules.production_execution.policy import require_policy
from app.modules.production_execution.units import convert_to_canonical_mass
from app.modules.production_planning.constants import (
    BATCH_STATUS_IN_WEIGHING,
    BATCH_STATUS_PENDING,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_RELEASED,
)
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import (
    ProductionBatchMaterial,
    ProductionOrderMaterial,
)
from app.modules.production_planning.support import as_decimal, require_positive


def _mass_unit(session: Session, unit_id: UUID) -> MeasurementUnit:
    unit = session.get(MeasurementUnit, unit_id)
    if unit is None or unit.dimension != "mass":
        raise ValidationError("unidade incompatível")
    return unit


def _tolerance(policy, planned: Decimal, weighed: Decimal) -> tuple[Decimal, Decimal, bool]:
    abs_diff = quantize_quantity(abs(weighed - planned))
    percent = (
        quantize_percent((abs_diff / planned) * Decimal("100"))
        if planned > 0
        else Decimal("0")
    )
    within = True
    if policy.absolute_tolerance is None and policy.percent_tolerance is None:
        within = abs_diff == Decimal("0")
    if policy.absolute_tolerance is not None and abs_diff > policy.absolute_tolerance:
        within = False
    if policy.percent_tolerance is not None and percent > policy.percent_tolerance:
        within = False
    return abs_diff, percent, within


def open_weighing_session(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionWeighingSession:
    permit(principal, PERMISSION_PRODUCTION_WEIGHING_RECORD)
    organization_id = org_id(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_OPEN_WEIGHING_SESSION
    )
    if replay is not None:
        found = session.scalar(
            select(ProductionWeighingSession).where(
                ProductionWeighingSession.organization_id == organization_id,
                ProductionWeighingSession.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    batch = lock_batch(session, batch_id, organization_id, expected_row_version)
    order = lock_order(session, batch.production_order_id, organization_id, None)
    if order.status not in {ORDER_STATUS_RELEASED, ORDER_STATUS_IN_WEIGHING}:
        raise InvalidStateError("transicao_invalida")
    if batch.status not in {BATCH_STATUS_PENDING, BATCH_STATUS_IN_WEIGHING}:
        raise InvalidStateError("transicao_invalida")
    open_existing = session.scalar(
        select(ProductionWeighingSession).where(
            ProductionWeighingSession.production_batch_id == batch.id,
            ProductionWeighingSession.status == SESSION_OPEN,
        )
    )
    if open_existing is not None:
        raise InvalidStateError("sessao_aberta_existente")
    row = ProductionWeighingSession(
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        production_order_id=order.id,
        production_batch_id=batch.id,
        status=SESSION_OPEN,
        opened_by_user_id=principal.user_id,
        opened_at=now(),
        idempotency_key=idempotency_key,
    )
    session.add(row)
    if order.status == ORDER_STATUS_RELEASED:
        order.status = ORDER_STATUS_IN_WEIGHING
        bump(order)
    if batch.status == BATCH_STATUS_PENDING:
        batch.status = BATCH_STATUS_IN_WEIGHING
        bump(batch)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_WEIGHING_SESSION_OPENED,
        command=COMMAND_OPEN_WEIGHING_SESSION,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"session_id": str(row.id), "batch_id": str(batch.id)},
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch.id,
    )
    return row


def complete_weighing_session(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionWeighingSession:
    permit(principal, PERMISSION_PRODUCTION_WEIGHING_RECORD)
    organization_id = org_id(principal)
    row = lock_session(session, session_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_COMPLETE_WEIGHING_SESSION
    )
    if replay is not None:
        return row
    if row.status != SESSION_OPEN:
        raise InvalidStateError("transicao_invalida")
    row.status = SESSION_COMPLETED
    row.completed_by_user_id = principal.user_id
    row.completed_at = now()
    bump(row)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=row.establishment_id,
        event_type=EVENT_WEIGHING_SESSION_COMPLETED,
        command=COMMAND_COMPLETE_WEIGHING_SESSION,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"session_id": str(row.id)},
        order_id=row.production_order_id,
        batch_id=row.production_batch_id,
    )
    return row


def cancel_weighing_session(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionWeighingSession:
    permit(principal, PERMISSION_PRODUCTION_WEIGHING_RECORD)
    organization_id = org_id(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    row = lock_session(session, session_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session,
        organization_id,
        idempotency_key,
        COMMAND_CANCEL_WEIGHING_SESSION,
        {"session_id": str(row.id), "reason": reason.strip()},
    )
    if replay is not None:
        return row
    if row.status != SESSION_OPEN:
        raise InvalidStateError("transicao_invalida")
    row.status = SESSION_CANCELLED
    row.cancelled_by_user_id = principal.user_id
    row.cancelled_at = now()
    row.cancel_reason = reason.strip()
    bump(row)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=row.establishment_id,
        event_type=EVENT_WEIGHING_SESSION_CANCELLED,
        command=COMMAND_CANCEL_WEIGHING_SESSION,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"session_id": str(row.id), "reason": reason.strip()},
        order_id=row.production_order_id,
        batch_id=row.production_batch_id,
    )
    return row


def _add_entry(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    batch_material_id: UUID,
    entry_type: str,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
    command: str,
    original_entry_id: UUID | None = None,
    lot_code: str | None = None,
    expires_on: date | None = None,
    scale_reference: str | None = None,
    justification: str | None = None,
) -> ProductionWeighingEntry:
    permit(principal, PERMISSION_PRODUCTION_WEIGHING_RECORD)
    organization_id = org_id(principal)
    replay = existing_idempotent(session, organization_id, idempotency_key, command)
    if replay is not None:
        found = session.scalar(
            select(ProductionWeighingEntry).where(
                ProductionWeighingEntry.organization_id == organization_id,
                ProductionWeighingEntry.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    weigh_session = lock_session(session, session_id, organization_id, None)
    if weigh_session.status != SESSION_OPEN:
        raise InvalidStateError("transicao_invalida")
    material = session.get(ProductionBatchMaterial, batch_material_id)
    if material is None or material.organization_id != organization_id:
        raise ValidationError("material inválido")
    if material.production_batch_id != weigh_session.production_batch_id:
        raise ValidationError("material inválido")
    unit = _mass_unit(session, measurement_unit_id)
    amount = require_positive(quantize_quantity(as_decimal(quantity, "quantidade")), "quantidade")
    policy = require_policy(session, weigh_session.production_order_id)
    if policy.require_manual_lot and not (lot_code and lot_code.strip()):
        raise ValidationError("lote obrigatório")
    original = None
    if entry_type in {ENTRY_REVERSAL, ENTRY_CORRECTION}:
        if original_entry_id is None:
            raise ValidationError("registro original obrigatório")
        original = session.get(ProductionWeighingEntry, original_entry_id)
        if original is None or original.organization_id != organization_id:
            raise ValidationError("registro original inválido")
        if original.entry_type == ENTRY_REVERSAL:
            raise ValidationError("registro original inválido")
        if entry_type == ENTRY_REVERSAL:
            amount = original.quantity
            unit = _mass_unit(session, original.measurement_unit_id)
    planned = material.planned_gross_quantity
    order_material = session.get(ProductionOrderMaterial, material.production_order_material_id)
    if order_material is None:
        raise ValidationError("material inválido")
    conversion = convert_to_canonical_mass(session, amount, unit.id)
    planned_conversion = convert_to_canonical_mass(
        session, planned, order_material.measurement_unit_id
    )
    abs_diff, percent, within = _tolerance(
        policy, planned_conversion.canonical_quantity, conversion.canonical_quantity
    )
    if not within and not (justification and justification.strip()):
        raise ValidationError("justificativa obrigatória fora da tolerância")
    row = ProductionWeighingEntry(
        organization_id=organization_id,
        session_id=weigh_session.id,
        production_batch_material_id=material.id,
        entry_type=entry_type,
        original_entry_id=original.id if original is not None else None,
        quantity=conversion.entered_quantity,
        measurement_unit_id=conversion.entered_unit_id,
        unit_code=conversion.entered_unit_code,
        canonical_quantity=conversion.canonical_quantity,
        canonical_unit_id=conversion.canonical_unit_id,
        canonical_unit_code=conversion.canonical_unit_code,
        conversion_factor=conversion.factor,
        conversion_source=conversion.source,
        conversion_version=conversion.version,
        planned_quantity=planned,
        absolute_difference=abs_diff,
        percent_difference=percent,
        within_tolerance=within,
        lot_code=lot_code.strip() if lot_code else None,
        expires_on=expires_on,
        scale_reference=scale_reference,
        operator_user_id=principal.user_id,
        occurred_at=now(),
        justification=justification.strip() if justification else None,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=weigh_session.establishment_id,
        event_type=EVENT_WEIGHING_RECORDED,
        command=command,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "entry_id": str(row.id),
            "session_id": str(weigh_session.id),
            "entry_type": entry_type,
        },
        order_id=weigh_session.production_order_id,
        batch_id=weigh_session.production_batch_id,
    )
    return row


def record_weighing(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    batch_material_id: UUID,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
    lot_code: str | None = None,
    expires_on: date | None = None,
    scale_reference: str | None = None,
    justification: str | None = None,
) -> ProductionWeighingEntry:
    return _add_entry(
        session,
        principal,
        session_id=session_id,
        batch_material_id=batch_material_id,
        entry_type=ENTRY_RECORD,
        quantity=quantity,
        measurement_unit_id=measurement_unit_id,
        idempotency_key=idempotency_key,
        command=COMMAND_RECORD_WEIGHING,
        lot_code=lot_code,
        expires_on=expires_on,
        scale_reference=scale_reference,
        justification=justification,
    )


def reverse_weighing(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    original_entry_id: UUID,
    idempotency_key: UUID,
    justification: str | None = None,
) -> ProductionWeighingEntry:
    original = session.get(ProductionWeighingEntry, original_entry_id)
    if original is None:
        raise ValidationError("registro original inválido")
    return _add_entry(
        session,
        principal,
        session_id=session_id,
        batch_material_id=original.production_batch_material_id,
        entry_type=ENTRY_REVERSAL,
        quantity=original.quantity,
        measurement_unit_id=original.measurement_unit_id,
        idempotency_key=idempotency_key,
        command=COMMAND_REVERSE_WEIGHING,
        original_entry_id=original_entry_id,
        justification=justification,
    )


def correct_weighing(
    session: Session,
    principal: Principal,
    *,
    session_id: UUID,
    original_entry_id: UUID,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
    lot_code: str | None = None,
    justification: str | None = None,
) -> ProductionWeighingEntry:
    original = session.get(ProductionWeighingEntry, original_entry_id)
    if original is None:
        raise ValidationError("registro original inválido")
    return _add_entry(
        session,
        principal,
        session_id=session_id,
        batch_material_id=original.production_batch_material_id,
        entry_type=ENTRY_CORRECTION,
        quantity=quantity,
        measurement_unit_id=measurement_unit_id,
        idempotency_key=idempotency_key,
        command=COMMAND_CORRECT_WEIGHING,
        original_entry_id=original_entry_id,
        lot_code=lot_code or original.lot_code,
        justification=justification,
    )


def verify_weighing(
    session: Session,
    principal: Principal,
    *,
    entry_id: UUID,
    decision: str,
    idempotency_key: UUID,
    justification: str | None = None,
) -> ProductionWeighingVerification:
    permit(principal, PERMISSION_PRODUCTION_WEIGHING_VERIFY)
    organization_id = org_id(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_VERIFY_WEIGHING
    )
    if replay is not None:
        found = session.scalar(
            select(ProductionWeighingVerification).where(
                ProductionWeighingVerification.organization_id == organization_id,
                ProductionWeighingVerification.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    if decision not in VERIFY_DECISIONS:
        raise ValidationError("decisão inválida")
    entry = session.get(ProductionWeighingEntry, entry_id)
    if entry is None or entry.organization_id != organization_id:
        raise ValidationError("entrada inválida")
    weigh_session = session.get(ProductionWeighingSession, entry.session_id)
    assert weigh_session is not None
    policy = require_policy(session, weigh_session.production_order_id)
    if (
        policy.verification_policy == "second_person"
        and entry.operator_user_id == principal.user_id
    ):
        raise ValidationError("autoconferencia_proibida")
    if decision == VERIFY_REJECTED and not (justification and justification.strip()):
        raise ValidationError("justificativa obrigatória")
    row = ProductionWeighingVerification(
        organization_id=organization_id,
        entry_id=entry.id,
        decision=decision,
        verifier_user_id=principal.user_id,
        occurred_at=now(),
        justification=justification.strip() if justification else None,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=weigh_session.establishment_id,
        event_type=EVENT_WEIGHING_VERIFIED,
        command=COMMAND_VERIFY_WEIGHING,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "verification_id": str(row.id),
            "entry_id": str(entry.id),
            "decision": decision,
        },
        order_id=weigh_session.production_order_id,
        batch_id=weigh_session.production_batch_id,
    )
    return row
