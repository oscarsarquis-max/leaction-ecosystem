"""Projeção operacional da ordem. Sem custos e sem regras novas."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import TechnicalProduct
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_BATCH_COMPLETE,
    PERMISSION_PRODUCTION_CONSUMPTION_RECORD,
    PERMISSION_PRODUCTION_OCCURRENCE_RECORD,
    PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE,
    PERMISSION_PRODUCTION_ORDER_COMPLETE,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE,
    PERMISSION_PRODUCTION_SHEET_ISSUE,
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    PERMISSION_PRODUCTION_WEIGHING_VERIFY,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AppUser, Establishment
from app.modules.production_execution.constants import (
    OCCURRENCE_OPEN,
    SESSION_OPEN,
    VERIFY_ACCEPTED,
    VERIFY_REJECTED,
)
from app.modules.production_execution.dependencies import assert_execution_dependencies
from app.modules.production_execution.lifecycle import (
    _minimum_consumption,
    _steps_done,
    _weighing_satisfied,
)
from app.modules.production_execution.models import (
    ProductionOccurrence,
    ProductionSheetIssue,
    ProductionStepExecution,
    ProductionWeighingEntry,
    ProductionWeighingSession,
    ProductionYieldMeasurement,
)
from app.modules.production_execution.occurrences import open_blocking_occurrences
from app.modules.production_execution.policy import policy_canonical, require_policy
from app.modules.production_execution.projections import (
    current_weighing_entries,
    effective_weighed_quantity,
    latest_verification,
    material_accepted,
    project_consumption,
    project_yield,
    within_completion_tolerance,
)
from app.modules.production_http.board import _next_action
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.schemas import decimal_str
from app.modules.production_http.serialize import batch_out, conversion_out, iso, order_out
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionOrder,
    ProductionOrderDependency,
    ProductionOrderMaterial,
    ProductionOrderStep,
)


def _check(ok: bool, reason: str | None) -> dict:
    return {"ok": ok, "reason": None if ok else reason}


def _user_name(session: Session, user_id) -> str | None:
    if user_id is None:
        return None
    user = session.get(AppUser, user_id)
    return user.display_name if user else None


def _entry_out(session: Session, row: ProductionWeighingEntry) -> dict:
    verification = latest_verification(session, row.id)
    return {
        "id": str(row.id),
        "session_id": str(row.session_id),
        "batch_material_id": str(row.production_batch_material_id),
        "entry_type": row.entry_type,
        "measurement_unit_id": str(row.measurement_unit_id),
        "operator_user_id": str(row.operator_user_id),
        "operator_name": _user_name(session, row.operator_user_id),
        "lot_code": row.lot_code,
        "justification": row.justification,
        "planned_quantity": decimal_str(row.planned_quantity),
        "absolute_difference": decimal_str(row.absolute_difference),
        "percent_difference": decimal_str(row.percent_difference),
        "within_tolerance": row.within_tolerance,
        "verification": None
        if verification is None
        else {
            "id": str(verification.id),
            "decision": verification.decision,
            "verifier_user_id": str(verification.verifier_user_id),
            "verifier_name": _user_name(session, verification.verifier_user_id),
            "justification": verification.justification,
        },
        **conversion_out(row),
    }


def build_execution(
    session: Session, principal: Principal, organization_id: UUID, order_id: UUID
) -> dict:
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise_domain(ValidationError("recurso inválido"))
    policy = None
    try:
        policy = require_policy(session, order.id)
    except ValidationError:
        policy = None
    product = session.get(TechnicalProduct, order.technical_product_id)
    establishment = session.get(Establishment, order.establishment_id)
    batches = list(
        session.scalars(
            select(ProductionBatch)
            .where(ProductionBatch.production_order_id == order.id)
            .order_by(ProductionBatch.sequence)
        )
    )
    planned_materials = {
        row.id: row
        for row in session.scalars(
            select(ProductionOrderMaterial).where(
                ProductionOrderMaterial.production_order_id == order.id
            )
        )
    }
    planned_steps = list(
        session.scalars(
            select(ProductionOrderStep)
            .where(ProductionOrderStep.production_order_id == order.id)
            .order_by(ProductionOrderStep.sequence)
        )
    )
    batch_payloads = []
    for batch in batches:
        materials = list(
            session.scalars(
                select(ProductionBatchMaterial).where(
                    ProductionBatchMaterial.production_batch_id == batch.id
                )
            )
        )
        sessions = list(
            session.scalars(
                select(ProductionWeighingSession).where(
                    ProductionWeighingSession.production_batch_id == batch.id
                )
            )
        )
        entries = list(
            session.scalars(
                select(ProductionWeighingEntry).where(
                    ProductionWeighingEntry.production_batch_material_id.in_(
                        [row.id for row in materials] or [UUID(int=0)]
                    )
                )
            )
        ) if materials else []
        material_items = []
        for material in materials:
            planned = planned_materials.get(material.production_order_material_id)
            current = current_weighing_entries(session, material.id)
            latest = current[-1] if current else None
            verification = latest_verification(session, latest.id) if latest else None
            if not current:
                weigh_state = "pending"
            elif verification and verification.decision == VERIFY_REJECTED:
                weigh_state = "rejected"
            elif policy and policy.verification_policy == "second_person" and not material_accepted(
                session, material.id
            ):
                weigh_state = "awaiting_verification"
            elif latest:
                weigh_state = "accepted" if material_accepted(session, material.id) else "recorded"
            else:
                weigh_state = "recorded"
            consumption = project_consumption(session, material.id)
            material_items.append(
                {
                    "id": str(material.id),
                    "batch_id": str(batch.id),
                    "name": planned.operational_name if planned else "material",
                    "measurement_unit_id": str(planned.measurement_unit_id) if planned else None,
                    "unit": planned.unit_code if planned else None,
                    "planned_gross": decimal_str(material.planned_gross_quantity),
                    "weighed_canonical": decimal_str(
                        effective_weighed_quantity(session, material.id)
                    ),
                    "weigh_state": weigh_state,
                    "consumption": {key: decimal_str(value) for key, value in consumption.items()},
                }
            )
        step_items = []
        for planned in planned_steps:
            run = session.scalar(
                select(ProductionStepExecution).where(
                    ProductionStepExecution.production_batch_id == batch.id,
                    ProductionStepExecution.production_order_step_id == planned.id,
                )
            )
            step_items.append(
                {
                    "order_step_id": str(planned.id),
                    "batch_id": str(batch.id),
                    "title": planned.title,
                    "instructions": planned.instructions,
                    "sequence": planned.sequence,
                    "duration_seconds": planned.duration_seconds,
                    "temperature_value": decimal_str(planned.temperature_value),
                    "temperature_unit": planned.temperature_unit,
                    "execution_id": None if run is None else str(run.id),
                    "status": "pending" if run is None else run.status,
                    "row_version": None if run is None else run.row_version,
                    "operator_user_id": None if run is None else (
                        None if run.operator_user_id is None else str(run.operator_user_id)
                    ),
                    "operator_name": None if run is None else _user_name(session, run.operator_user_id),
                    "started_at": None if run is None else iso(run.started_at),
                    "ended_at": None if run is None else iso(run.ended_at),
                    "measured_duration_seconds": None if run is None else run.measured_duration_seconds,
                    "measured_temperature": None
                    if run is None
                    else decimal_str(run.measured_temperature),
                    "notes": None if run is None else run.notes,
                }
            )
        yields = list(
            session.scalars(
                select(ProductionYieldMeasurement).where(
                    ProductionYieldMeasurement.production_batch_id == batch.id
                )
            )
        )
        projection = project_yield(session, batch)
        batch_payloads.append(
            {
                **batch_out(batch),
                "materials": material_items,
                "sessions": [
                    {
                        "id": str(row.id),
                        "status": row.status,
                        "row_version": row.row_version,
                        "opened_by_user_id": str(row.opened_by_user_id),
                    }
                    for row in sessions
                ],
                "weighings": [_entry_out(session, row) for row in entries],
                "steps": step_items,
                "yields": [
                    {
                        "id": str(row.id),
                        "type": row.measurement_type,
                        "quantity": decimal_str(row.quantity),
                        "unit": row.unit_code,
                        "measurement_unit_id": str(row.measurement_unit_id),
                        "notes": row.notes,
                    }
                    for row in yields
                ],
                "yield_projection": {
                    "final_mass": decimal_str(projection.final_mass),
                    "sellable_units": decimal_str(projection.sellable_units),
                    "rejected_units": decimal_str(projection.rejected_units),
                    "leftover": decimal_str(projection.leftover),
                    "scrap": decimal_str(projection.scrap),
                    "loss_absolute": decimal_str(projection.loss_absolute),
                    "loss_percent": decimal_str(projection.loss_percent),
                    "target_deviation": decimal_str(projection.target_deviation),
                    "completeness": projection.completeness,
                    "within_tolerance": (
                        None
                        if policy is None
                        else within_completion_tolerance(
                            projection, batch.target_quantity, policy.completion_tolerance
                        )
                    ),
                },
            }
        )
    occurrences = list(
        session.scalars(
            select(ProductionOccurrence).where(ProductionOccurrence.production_order_id == order.id)
        )
    )
    dependencies = list(
        session.scalars(
            select(ProductionOrderDependency).where(
                ProductionOrderDependency.dependent_order_id == order.id
            )
        )
    )
    sheets = list(
        session.scalars(
            select(ProductionSheetIssue)
            .where(ProductionSheetIssue.production_order_id == order.id)
            .order_by(ProductionSheetIssue.issue_number)
        )
    )
    first_batch = batches[0] if batches else None
    weighing_ok = bool(first_batch) and all(
        _weighing_satisfied(session, order, batch) for batch in batches
    )
    steps_ok = bool(first_batch) and all(_steps_done(session, batch) for batch in batches)
    consumption_ok = bool(first_batch) and all(
        _minimum_consumption(session, batch) for batch in batches
    )
    yield_ok = bool(first_batch) and all(
        project_yield(session, batch).completeness == "complete" for batch in batches
    )
    blocking = open_blocking_occurrences(session, order.id)
    try:
        assert_execution_dependencies(session, order)
        deps_ok = True
        deps_reason = None
    except (ValidationError, InvalidStateError) as exc:
        deps_ok = False
        deps_reason = str(exc)
    verify_ok = True
    if policy and policy.verification_policy == "second_person":
        verify_ok = all(
            material_accepted(session, UUID(item["id"]))
            for batch in batch_payloads
            for item in batch["materials"]
            if item["weigh_state"] != "pending"
        ) and weighing_ok
    readiness = {
        "weighing": _check(weighing_ok, "pesagem incompleta"),
        "verifications": _check(verify_ok, "aguardando conferência por outro usuário"),
        "steps": _check(steps_ok, "etapas incompletas"),
        "consumptions": _check(consumption_ok, "consumo mínimo ausente"),
        "yields": _check(yield_ok, "rendimento incompleto"),
        "dependencies": _check(deps_ok, deps_reason or "dependência pendente"),
        "blocking_occurrences": _check(not blocking, "ocorrência bloqueante aberta"),
        "permissions": {
            "complete": PERMISSION_PRODUCTION_ORDER_COMPLETE in principal.permissions,
            "short_close": PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE in principal.permissions,
            "weighing_record": PERMISSION_PRODUCTION_WEIGHING_RECORD in principal.permissions,
            "weighing_verify": PERMISSION_PRODUCTION_WEIGHING_VERIFY in principal.permissions,
            "consumption": PERMISSION_PRODUCTION_CONSUMPTION_RECORD in principal.permissions,
            "step": PERMISSION_PRODUCTION_STEP_EXECUTE in principal.permissions,
            "occurrence_record": PERMISSION_PRODUCTION_OCCURRENCE_RECORD in principal.permissions,
            "occurrence_resolve": PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE in principal.permissions,
            "batch_complete": PERMISSION_PRODUCTION_BATCH_COMPLETE in principal.permissions,
            "sheet": PERMISSION_PRODUCTION_SHEET_ISSUE in principal.permissions,
        },
    }
    return {
        "viewer": {
            "user_id": str(principal.user_id),
            "display_name": principal.display_name,
            "permissions": sorted(principal.permissions),
        },
        "order": order_out(order),
        "product": None
        if product is None
        else {"id": str(product.id), "code": product.code, "display_name": product.display_name},
        "establishment": None
        if establishment is None
        else {
            "id": str(establishment.id),
            "code": establishment.code,
            "display_name": establishment.display_name,
        },
        "policy": None if policy is None else policy_canonical(policy),
        "batches": batch_payloads,
        "occurrences": [
            {
                "id": str(row.id),
                "category": row.category,
                "severity": row.severity,
                "status": row.status,
                "description": row.description,
                "is_blocking": row.is_blocking,
                "batch_id": None if row.production_batch_id is None else str(row.production_batch_id),
                "order_step_id": None
                if row.production_order_step_id is None
                else str(row.production_order_step_id),
            }
            for row in occurrences
        ],
        "dependencies": [
            {
                "id": str(row.id),
                "predecessor_order_id": str(row.predecessor_order_id),
                "dependency_type": row.dependency_type,
            }
            for row in dependencies
        ],
        "sheets": [
            {
                "id": str(row.id),
                "issue_number": row.issue_number,
                "payload_sha256": row.payload_sha256,
                "purpose": row.purpose,
                "previous_issue_id": None
                if row.previous_issue_id is None
                else str(row.previous_issue_id),
            }
            for row in sheets
        ],
        "blocked": any(row.status == OCCURRENCE_OPEN and row.is_blocking for row in occurrences),
        "open_session": any(
            session_row.status == SESSION_OPEN
            for batch in batch_payloads
            for session_row in batch["sessions"]
        ),
        "next_action": _next_action(order, principal, policy is None),
        "readiness": readiness,
        "updated_at": datetime.now(UTC).isoformat(),
    }
