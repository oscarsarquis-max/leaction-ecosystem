from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_CONSUMPTION_RECORD,
    Principal,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_RECORD_CONSUMPTION,
    CONSUMPTION_CORRECTION,
    CONSUMPTION_TYPES,
    EVENT_CONSUMPTION_RECORDED,
)
from app.modules.production_execution.models import ProductionMaterialConsumption
from app.modules.production_execution.units import convert_to_canonical_mass
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import ProductionBatch, ProductionBatchMaterial


def record_consumption(
    session: Session,
    principal: Principal,
    *,
    batch_id: UUID,
    batch_material_id: UUID,
    consumption_type: str,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
    weighing_entry_id: UUID | None = None,
    lot_code: str | None = None,
    reason: str | None = None,
    corrects_id: UUID | None = None,
) -> ProductionMaterialConsumption:
    permit(principal, PERMISSION_PRODUCTION_CONSUMPTION_RECORD)
    organization_id = org_id(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_RECORD_CONSUMPTION
    )
    if replay is not None:
        found = session.scalar(
            select(ProductionMaterialConsumption).where(
                ProductionMaterialConsumption.organization_id == organization_id,
                ProductionMaterialConsumption.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    if consumption_type not in CONSUMPTION_TYPES:
        raise ValidationError("tipo de consumo inválido")
    batch = session.get(ProductionBatch, batch_id)
    if batch is None or batch.organization_id != organization_id:
        raise ValidationError("batelada inválida")
    material = session.get(ProductionBatchMaterial, batch_material_id)
    if material is None or material.organization_id != organization_id:
        raise ValidationError("material inválido")
    if material.production_batch_id != batch.id:
        raise ValidationError("material inválido")
    unit = session.get(MeasurementUnit, measurement_unit_id)
    if unit is None:
        raise ValidationError("unidade incompatível")
    conversion = convert_to_canonical_mass(session, quantity, unit.id)
    amount = conversion.entered_quantity
    if consumption_type == CONSUMPTION_CORRECTION and corrects_id is None:
        raise ValidationError("registro corrigido obrigatório")
    if corrects_id is not None:
        original = session.get(ProductionMaterialConsumption, corrects_id)
        if original is None or original.organization_id != organization_id:
            raise ValidationError("registro corrigido inválido")
    row = ProductionMaterialConsumption(
        organization_id=organization_id,
        production_order_id=batch.production_order_id,
        production_batch_id=batch.id,
        production_batch_material_id=material.id,
        consumption_type=consumption_type,
        quantity=amount,
        measurement_unit_id=conversion.entered_unit_id,
        unit_code=conversion.entered_unit_code,
        canonical_quantity=conversion.canonical_quantity,
        canonical_unit_id=conversion.canonical_unit_id,
        canonical_unit_code=conversion.canonical_unit_code,
        conversion_factor=conversion.factor,
        conversion_source=conversion.source,
        conversion_version=conversion.version,
        weighing_entry_id=weighing_entry_id,
        lot_code=lot_code.strip() if lot_code else None,
        actor_user_id=principal.user_id,
        occurred_at=now(),
        reason=reason.strip() if reason else None,
        corrects_id=corrects_id,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    from app.modules.production_planning.models import ProductionOrder

    production_order = session.get(ProductionOrder, batch.production_order_id)
    assert production_order is not None
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=production_order.establishment_id,
        event_type=EVENT_CONSUMPTION_RECORDED,
        command=COMMAND_RECORD_CONSUMPTION,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"consumption_id": str(row.id), "consumption_type": consumption_type},
        plan_id=production_order.plan_id,
        order_id=production_order.id,
        batch_id=batch.id,
    )
    return row
