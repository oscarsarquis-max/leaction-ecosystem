from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.production_execution.consumption import record_consumption
from app.modules.production_execution.dependencies import override_dependency
from app.modules.production_execution.lifecycle import (
    complete_batch,
    complete_order,
    resume_order,
    short_close_order,
)
from app.modules.production_execution.occurrences import record_occurrence, resolve_occurrence
from app.modules.production_execution.policy import adopt_execution_policy, set_execution_policy
from app.modules.production_execution.sheet import issue_sheet
from app.modules.production_execution.steps import (
    cancel_step,
    complete_step,
    hold_step,
    mark_step_ready,
    resume_step,
    skip_step,
    start_step,
)
from app.modules.production_execution.weighing import (
    cancel_weighing_session,
    complete_weighing_session,
    correct_weighing,
    open_weighing_session,
    record_weighing,
    reverse_weighing,
    verify_weighing,
)
from app.modules.production_execution.yields import record_yield
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.schemas import (
    ConsumptionBody,
    DependencyCreate,
    OccurrenceBody,
    OrderCreate,
    PlanCreate,
    PlanItemWrite,
    PolicyBody,
    ReasonBody,
    ResolveOccurrenceBody,
    SheetIssueBody,
    SplitBatchesBody,
    VerifyBody,
    WeighingCorrectBody,
    WeighingRecordBody,
    YieldBody,
    envelope,
)
from app.modules.production_http.serialize import batch_out, order_out, plan_item_out, plan_out
from app.modules.production_planning.commands import (
    add_dependency,
    cancel_order,
    create_order,
    create_plan,
    create_substitute_order,
    hold_order,
    release_order,
    remove_plan_item,
    schedule_order,
    schedule_plan,
    split_batches,
    upsert_plan_item,
)
from app.modules.production_planning.errors import ValidationError

router = APIRouter()


def _keys(
    idempotency_key: str | None,
    x_correlation_id: str | None,
    if_match: str | None = None,
    *,
    require_match: bool = False,
):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key), parse_if_match(
        if_match, required=require_match
    )


def _run(action):
    try:
        return action()
    except HTTPException:
        raise
    except Exception as exc:
        raise_domain(exc)


@router.post("/plans")
def post_plan(
    organization_id: UUID,
    body: PlanCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_plan(
            session,
            principal,
            establishment_id=body.establishment_id,
            operational_date=body.operational_date,
            idempotency_key=key,
            shift=body.shift,
            notes=body.notes,
        )
    )
    return envelope(plan_out(row), row.row_version)


@router.post("/plans/{plan_id}/items")
def post_plan_item(
    organization_id: UUID,
    plan_id: UUID,
    body: PlanItemWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: upsert_plan_item(
            session,
            principal,
            plan_id=plan_id,
            technical_product_id=body.technical_product_id,
            target_mode=body.target_mode,
            target_quantity=body.target_quantity,
            sort_order=body.sort_order,
            idempotency_key=key,
            unit_weight_g=body.unit_weight_g,
            priority=body.priority,
            notes=body.notes,
        )
    )
    return envelope(plan_item_out(row))


@router.patch("/plans/{plan_id}/items/{item_id}")
def patch_plan_item(
    organization_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    body: PlanItemWrite,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: upsert_plan_item(
            session,
            principal,
            plan_id=plan_id,
            item_id=item_id,
            technical_product_id=body.technical_product_id,
            target_mode=body.target_mode,
            target_quantity=body.target_quantity,
            sort_order=body.sort_order,
            idempotency_key=key,
            unit_weight_g=body.unit_weight_g,
            priority=body.priority,
            notes=body.notes,
        )
    )
    return envelope(plan_item_out(row))


@router.delete("/plans/{plan_id}/items/{item_id}")
def delete_plan_item(
    organization_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    _run(
        lambda: remove_plan_item(
            session, principal, plan_id=plan_id, item_id=item_id, idempotency_key=key
        )
    )
    return envelope({"id": str(item_id), "removed": True})


@router.post("/plans/{plan_id}/schedule")
def post_schedule_plan(
    organization_id: UUID,
    plan_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: schedule_plan(
            session, principal, plan_id=plan_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(plan_out(row), row.row_version)


@router.post("/orders")
def post_order(
    organization_id: UUID,
    body: OrderCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_order(
            session,
            principal,
            establishment_id=body.establishment_id,
            technical_product_id=body.technical_product_id,
            target_mode=body.target_mode,
            target_quantity=body.target_quantity,
            idempotency_key=key,
            unit_weight_g=body.unit_weight_g,
            plan_id=body.plan_id,
            plan_item_id=body.plan_item_id,
            formulation_version_id=body.formulation_version_id,
            scale_calculation_id=body.scale_calculation_id,
            priority=body.priority,
            planned_start_at=body.planned_start_at,
            planned_end_at=body.planned_end_at,
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/schedule")
def post_schedule_order(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: schedule_order(
            session, principal, order_id=order_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/dependencies")
def post_dependency(
    organization_id: UUID,
    order_id: UUID,
    body: DependencyCreate,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: add_dependency(
            session,
            principal,
            dependent_order_id=order_id,
            predecessor_order_id=body.predecessor_order_id,
            dependency_type=body.dependency_type,
            idempotency_key=key,
            relation_note=body.relation_note,
            quantity=body.quantity,
        )
    )
    return envelope({"id": str(row.id)})


@router.post("/orders/{order_id}/batches")
def post_batches(
    organization_id: UUID,
    order_id: UUID,
    body: SplitBatchesBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    rows = _run(
        lambda: split_batches(
            session,
            principal,
            order_id=order_id,
            count=body.count,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope([batch_out(row) for row in rows])


@router.post("/orders/{order_id}/release")
def post_release(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: release_order(
            session, principal, order_id=order_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/hold")
def post_hold(
    organization_id: UUID,
    order_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: hold_order(
            session,
            principal,
            order_id=order_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/resume")
def post_resume(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: resume_order(
            session, principal, order_id=order_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/cancel")
def post_cancel(
    organization_id: UUID,
    order_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: cancel_order(
            session,
            principal,
            order_id=order_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/substitute")
def post_substitute(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: create_substitute_order(
            session, principal, cancelled_order_id=order_id, idempotency_key=key
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/policy")
def post_policy(
    organization_id: UUID,
    order_id: UUID,
    body: PolicyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: set_execution_policy(
            session,
            principal,
            order_id=order_id,
            weighing_policy=body.weighing_policy,
            verification_policy=body.verification_policy,
            completion_tolerance=body.completion_tolerance,
            allow_short_close=body.allow_short_close,
            require_manual_lot=body.require_manual_lot,
            absolute_tolerance=body.absolute_tolerance,
            percent_tolerance=body.percent_tolerance,
            idempotency_key=key,
        )
    )
    return envelope({"id": str(row.id), "policy_hash": row.policy_hash})


@router.post("/orders/{order_id}/policy/adopt")
def post_adopt_policy(
    organization_id: UUID,
    order_id: UUID,
    body: PolicyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    if not body.reason:
        raise_domain(ValidationError("motivo obrigatório"))
    row = _run(
        lambda: adopt_execution_policy(
            session,
            principal,
            order_id=order_id,
            weighing_policy=body.weighing_policy,
            verification_policy=body.verification_policy,
            completion_tolerance=body.completion_tolerance,
            allow_short_close=body.allow_short_close,
            reason=body.reason,
            idempotency_key=key,
            require_manual_lot=body.require_manual_lot,
            absolute_tolerance=body.absolute_tolerance,
            percent_tolerance=body.percent_tolerance,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "policy_hash": row.policy_hash})


@router.post("/batches/{batch_id}/weighing-sessions")
def post_open_weighing(
    organization_id: UUID,
    batch_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: open_weighing_session(
            session, principal, batch_id=batch_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/weighing-sessions/{session_id}/complete")
def post_complete_weighing_session(
    organization_id: UUID,
    session_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: complete_weighing_session(
            session,
            principal,
            session_id=session_id,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/weighing-sessions/{session_id}/cancel")
def post_cancel_weighing_session(
    organization_id: UUID,
    session_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: cancel_weighing_session(
            session,
            principal,
            session_id=session_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/weighing-sessions/{session_id}/entries")
def post_weighing_entry(
    organization_id: UUID,
    session_id: UUID,
    body: WeighingRecordBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_weighing(
            session,
            principal,
            session_id=session_id,
            batch_material_id=body.batch_material_id,
            quantity=body.quantity,
            measurement_unit_id=body.measurement_unit_id,
            idempotency_key=key,
            lot_code=body.lot_code,
            expires_on=body.expires_on,
            scale_reference=body.scale_reference,
            justification=body.justification,
        )
    )
    return envelope({"id": str(row.id), "quantity": str(row.quantity), "unit": row.unit_code})


@router.post("/weighing-entries/{entry_id}/reverse")
def post_reverse_weighing(
    organization_id: UUID,
    entry_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)

    def _do():
        from app.modules.production_execution.models import ProductionWeighingEntry

        row = session.get(ProductionWeighingEntry, entry_id)
        if row is None:
            raise ValidationError("registro original inválido")
        return reverse_weighing(
            session,
            principal,
            session_id=row.session_id,
            original_entry_id=entry_id,
            idempotency_key=key,
        )

    row = _run(_do)
    return envelope({"id": str(row.id)})


@router.post("/weighing-entries/{entry_id}/correct")
def post_correct_weighing(
    organization_id: UUID,
    entry_id: UUID,
    body: WeighingCorrectBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)

    def _do():
        from app.modules.production_execution.models import ProductionWeighingEntry

        original = session.get(ProductionWeighingEntry, entry_id)
        if original is None:
            raise ValidationError("registro original inválido")
        return correct_weighing(
            session,
            principal,
            session_id=original.session_id,
            original_entry_id=entry_id,
            quantity=body.quantity,
            measurement_unit_id=body.measurement_unit_id,
            idempotency_key=key,
            lot_code=body.lot_code,
            justification=body.justification,
        )

    row = _run(_do)
    return envelope({"id": str(row.id)})


@router.post("/weighing-entries/{entry_id}/verify")
def post_verify(
    organization_id: UUID,
    entry_id: UUID,
    body: VerifyBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: verify_weighing(
            session,
            principal,
            entry_id=entry_id,
            decision=body.decision,
            idempotency_key=key,
            justification=body.justification,
        )
    )
    return envelope({"id": str(row.id), "decision": row.decision})


@router.post("/batches/{batch_id}/consumptions")
def post_consumption(
    organization_id: UUID,
    batch_id: UUID,
    body: ConsumptionBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_consumption(
            session,
            principal,
            batch_id=batch_id,
            batch_material_id=body.batch_material_id,
            consumption_type=body.consumption_type,
            quantity=body.quantity,
            measurement_unit_id=body.measurement_unit_id,
            idempotency_key=key,
            weighing_entry_id=body.weighing_entry_id,
            lot_code=body.lot_code,
            reason=body.reason,
            corrects_id=body.corrects_id,
        )
    )
    return envelope({"id": str(row.id), "type": row.consumption_type})


def _step(action, batch_id, step_id, principal, session, key, version):
    return _run(
        lambda: action(
            session,
            principal,
            batch_id=batch_id,
            order_step_id=step_id,
            idempotency_key=key,
            expected_row_version=version,
        )
    )


@router.post("/batches/{batch_id}/steps/{step_id}/ready")
def post_step_ready(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _step(mark_step_ready, batch_id, step_id, principal, session, key, version)
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/start")
def post_step_start(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _step(start_step, batch_id, step_id, principal, session, key, version)
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/hold")
def post_step_hold(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: hold_step(
            session,
            principal,
            batch_id=batch_id,
            order_step_id=step_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/resume")
def post_step_resume(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _step(resume_step, batch_id, step_id, principal, session, key, version)
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/complete")
def post_step_complete(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _step(complete_step, batch_id, step_id, principal, session, key, version)
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/skip")
def post_step_skip(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: skip_step(
            session,
            principal,
            batch_id=batch_id,
            order_step_id=step_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/steps/{step_id}/cancel")
def post_step_cancel(
    organization_id: UUID,
    batch_id: UUID,
    step_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match)
    row = _run(
        lambda: cancel_step(
            session,
            principal,
            batch_id=batch_id,
            order_step_id=step_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope({"id": str(row.id), "status": row.status}, row.row_version)


@router.post("/batches/{batch_id}/yields")
def post_yield(
    organization_id: UUID,
    batch_id: UUID,
    body: YieldBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_yield(
            session,
            principal,
            batch_id=batch_id,
            measurement_type=body.measurement_type,
            quantity=body.quantity,
            measurement_unit_id=body.measurement_unit_id,
            idempotency_key=key,
            notes=body.notes,
        )
    )
    return envelope({"id": str(row.id)})


@router.post("/orders/{order_id}/occurrences")
def post_occurrence(
    organization_id: UUID,
    order_id: UUID,
    body: OccurrenceBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: record_occurrence(
            session,
            principal,
            order_id=order_id,
            category=body.category,
            severity=body.severity,
            description=body.description,
            idempotency_key=key,
            is_blocking=body.is_blocking,
            batch_id=body.batch_id,
            order_step_id=body.order_step_id,
        )
    )
    return envelope({"id": str(row.id)})


@router.post("/occurrences/{occurrence_id}/resolve")
def post_resolve_occurrence(
    organization_id: UUID,
    occurrence_id: UUID,
    body: ResolveOccurrenceBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: resolve_occurrence(
            session,
            principal,
            occurrence_id=occurrence_id,
            notes=body.notes,
            idempotency_key=key,
        )
    )
    return envelope({"id": str(row.id), "status": row.status})


@router.post("/dependencies/{dependency_id}/override")
def post_override(
    organization_id: UUID,
    dependency_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: override_dependency(
            session,
            principal,
            dependency_id=dependency_id,
            reason=body.reason,
            idempotency_key=key,
        )
    )
    return envelope({"id": str(row.id)})


@router.post("/batches/{batch_id}/complete")
def post_complete_batch(
    organization_id: UUID,
    batch_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: complete_batch(
            session, principal, batch_id=batch_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(batch_out(row), row.row_version)


@router.post("/orders/{order_id}/complete")
def post_complete_order(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: complete_order(
            session, principal, order_id=order_id, idempotency_key=key, expected_row_version=version
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/short-close")
def post_short_close(
    organization_id: UUID,
    order_id: UUID,
    body: ReasonBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    key, version = _keys(idempotency_key, x_correlation_id, if_match, require_match=True)
    row = _run(
        lambda: short_close_order(
            session,
            principal,
            order_id=order_id,
            reason=body.reason,
            idempotency_key=key,
            expected_row_version=version,
        )
    )
    return envelope(order_out(row), row.row_version)


@router.post("/orders/{order_id}/sheets")
def post_sheet(
    organization_id: UUID,
    order_id: UUID,
    body: SheetIssueBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    key, _ = _keys(idempotency_key, x_correlation_id)
    row = _run(
        lambda: issue_sheet(
            session,
            principal,
            order_id=order_id,
            purpose=body.purpose,
            idempotency_key=key,
            batch_id=body.batch_id,
        )
    )
    return envelope(
        {
            "id": str(row.id),
            "issue_number": row.issue_number,
            "payload_sha256": row.payload_sha256,
        }
    )
