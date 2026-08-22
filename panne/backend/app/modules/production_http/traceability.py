"""Rastreabilidade consolidada. Sem nova fonte de verdade e sem custos."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_TRACEABILITY_READ,
    Principal,
    require_permission,
)
from app.modules.production_execution.models import (
    ProductionDependencyOverride,
    ProductionExecutionPolicy,
    ProductionMaterialConsumption,
    ProductionOccurrence,
    ProductionSheetIssue,
    ProductionStepExecution,
    ProductionWeighingEntry,
    ProductionWeighingVerification,
    ProductionYieldMeasurement,
)
from app.modules.production_execution.projections import (
    effective_weighed_quantity,
    project_consumption,
)
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.serialize import conversion_out, decimal_str, iso
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionEvent,
    ProductionOrder,
    ProductionOrderDependency,
    ProductionOrderMaterial,
    ProductionOrderStep,
)


def build_traceability(
    session: Session, principal: Principal, organization_id: UUID, order_id: UUID
) -> dict:
    try:
        require_permission(principal, PERMISSION_PRODUCTION_TRACEABILITY_READ)
    except Exception as exc:
        raise_domain(exc)
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise_domain(ValidationError("ordem inválida"))
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    materials = list(
        session.scalars(
            select(ProductionOrderMaterial).where(
                ProductionOrderMaterial.production_order_id == order.id
            )
        )
    )
    steps = list(
        session.scalars(
            select(ProductionOrderStep).where(ProductionOrderStep.production_order_id == order.id)
        )
    )
    events = list(
        session.scalars(
            select(ProductionEvent)
            .where(ProductionEvent.order_id == order.id)
            .order_by(ProductionEvent.sequence_no)
        )
    )
    weighings = list(
        session.scalars(
            select(ProductionWeighingEntry).where(
                ProductionWeighingEntry.organization_id == organization_id
            )
        )
    )
    batch_ids = {batch.id for batch in batches}
    material_ids = {
        row.id
        for row in session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_batch_id.in_(batch_ids or {order.id})
            )
        )
    }
    weighings = [row for row in weighings if row.production_batch_material_id in material_ids]
    consumptions = list(
        session.scalars(
            select(ProductionMaterialConsumption).where(
                ProductionMaterialConsumption.production_order_id == order.id
            )
        )
    )
    executions = list(
        session.scalars(
            select(ProductionStepExecution).where(
                ProductionStepExecution.production_order_id == order.id
            )
        )
    )
    yields = list(
        session.scalars(
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.production_order_id == order.id
            )
        )
    )
    occurrences = list(
        session.scalars(
            select(ProductionOccurrence).where(ProductionOccurrence.production_order_id == order.id)
        )
    )
    deps = list(
        session.scalars(
            select(ProductionOrderDependency).where(
                ProductionOrderDependency.dependent_order_id == order.id
            )
        )
    )
    overrides = list(
        session.scalars(
            select(ProductionDependencyOverride).where(
                ProductionDependencyOverride.organization_id == organization_id
            )
        )
    )
    override_ids = {row.id for row in deps}
    overrides = [row for row in overrides if row.dependency_id in override_ids]
    issues = list(
        session.scalars(
            select(ProductionSheetIssue).where(ProductionSheetIssue.production_order_id == order.id)
        )
    )
    policy = session.scalar(
        select(ProductionExecutionPolicy).where(
            ProductionExecutionPolicy.production_order_id == order.id
        )
    )
    batch_materials = []
    if batch_ids:
        batch_materials = list(
            session.scalars(
                select(ProductionBatchMaterial).where(
                    ProductionBatchMaterial.production_batch_id.in_(batch_ids)
                )
            )
        )
    actual_materials = [
        {
            "batch_material_id": str(material.id),
            "planned_gross": decimal_str(material.planned_gross_quantity),
            "weighed_canonical": decimal_str(effective_weighed_quantity(session, material.id)),
            "consumption": {
                key: decimal_str(value)
                for key, value in project_consumption(session, material.id).items()
            },
        }
        for material in batch_materials
    ]
    return {
        "order": {
            "id": str(order.id),
            "public_code": order.public_code,
            "status": order.status,
            "formulation_version_id": (
                None if order.formulation_version_id is None else str(order.formulation_version_id)
            ),
            "scale_calculation_id": (
                None if order.scale_calculation_id is None else str(order.scale_calculation_id)
            ),
            "materials_hash": order.materials_hash,
            "steps_hash": order.steps_hash,
            "snapshot_hash": order.snapshot_hash,
            "policy_hash": None if policy is None else policy.policy_hash,
        },
        "batches": [
            {
                "id": str(batch.id),
                "operational_code": batch.operational_code,
                "status": batch.status,
            }
            for batch in batches
        ],
        "planned_materials": [
            {
                "id": str(row.id),
                "name": row.operational_name,
                "gross": decimal_str(row.gross_quantity),
                "unit": row.unit_code,
            }
            for row in materials
        ],
        "planned_steps": [{"id": str(row.id), "title": row.title} for row in steps],
        "actual_materials": actual_materials,
        "weighings": [
            {
                "id": str(row.id),
                "lot_code": row.lot_code,
                "operator_user_id": str(row.operator_user_id),
                **conversion_out(row),
            }
            for row in weighings
        ],
        "verifications": [
            {
                "id": str(row.id),
                "entry_id": str(row.entry_id),
                "decision": row.decision,
                "verifier_user_id": str(row.verifier_user_id),
            }
            for row in session.scalars(
                select(ProductionWeighingVerification).where(
                    ProductionWeighingVerification.entry_id.in_(
                        [item.id for item in weighings] or [order.id]
                    )
                )
            )
        ],
        "consumptions": [
            {"id": str(row.id), "type": row.consumption_type, **conversion_out(row)}
            for row in consumptions
        ],
        "step_runs": [
            {
                "id": str(row.id),
                "status": row.status,
                "operator_user_id": None
                if row.operator_user_id is None
                else str(row.operator_user_id),
            }
            for row in executions
        ],
        "yields": [
            {"id": str(row.id), "type": row.measurement_type, "quantity": decimal_str(row.quantity)}
            for row in yields
        ],
        "occurrences": [
            {"id": str(row.id), "category": row.category, "status": row.status}
            for row in occurrences
        ],
        "dependencies": [
            {
                "id": str(row.id),
                "predecessor_order_id": str(row.predecessor_order_id),
                "type": row.dependency_type,
            }
            for row in deps
        ],
        "overrides": [{"id": str(row.id), "reason": row.reason} for row in overrides],
        "sheet_issues": [
            {
                "id": str(row.id),
                "issue_number": row.issue_number,
                "payload_sha256": row.payload_sha256,
            }
            for row in issues
        ],
        "events": [
            {
                "id": str(row.id),
                "type": row.event_type,
                "command": row.command,
                "occurred_at": iso(row.occurred_at),
            }
            for row in events
        ],
    }
