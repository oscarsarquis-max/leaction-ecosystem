from datetime import date
from decimal import Decimal
from threading import Thread
from uuid import uuid4

import pytest
from app.modules.identity_organization.authorization import permissions_for_role
from app.modules.production_execution.constants import (
    CONSUMPTION_CONSUME,
    CONSUMPTION_RETURN,
    CONSUMPTION_WASTE,
    ENTRY_CORRECTION,
    ENTRY_REVERSAL,
    OCCURRENCE_QUALITY,
    POLICY_WEIGHING_REQUIRED,
    SEVERITY_HIGH,
    SHEET_OPERATIONAL,
    STEP_COMPLETED,
    STEP_IN_PROGRESS,
    VERIFICATION_SECOND_PERSON,
    VERIFY_ACCEPTED,
    VERIFY_REJECTED,
    YIELD_POST_BAKE_MASS,
)
from app.modules.production_execution.consumption import record_consumption
from app.modules.production_execution.dependencies import override_dependency
from app.modules.production_execution.lifecycle import (
    complete_order,
    mark_order_ready,
    resume_order,
    short_close_order,
)
from app.modules.production_execution.occurrences import record_occurrence, resolve_occurrence
from app.modules.production_execution.policy import set_execution_policy
from app.modules.production_execution.projections import (
    effective_weighed_quantity,
    project_consumption,
    project_yield,
)
from app.modules.production_execution.sheet import issue_sheet
from app.modules.production_execution.steps import (
    complete_step,
    hold_step,
    mark_step_ready,
    resume_step,
    start_step,
)
from app.modules.production_execution.weighing import (
    complete_weighing_session,
    correct_weighing,
    open_weighing_session,
    record_weighing,
    reverse_weighing,
    verify_weighing,
)
from app.modules.production_execution.yields import record_yield, reverse_yield
from app.modules.production_planning.commands import (
    add_dependency,
    cancel_order,
    create_order,
    create_plan,
    hold_order,
    release_order,
    schedule_order,
    schedule_plan,
    split_batches,
    upsert_plan_item,
)
from app.modules.production_planning.constants import (
    DEPENDENCY_PREFERMENT,
    EVENT_ORDER_RELEASED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_SHORT_CLOSED,
    TARGET_MODE_MASS,
)
from app.modules.production_planning.errors import (
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionEvent,
    ProductionOrderStep,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests import helpers
from tests.test_production_planning import _context, _plan_and_order


def _batches(session: Session, order_id):
    return list(
        session.scalars(
            select(ProductionBatch)
            .where(ProductionBatch.production_order_id == order_id)
            .order_by(ProductionBatch.sequence)
        )
    )


def _materials(session: Session, batch_id):
    return list(
        session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_batch_id == batch_id
            )
        )
    )


def _steps(session: Session, order_id):
    return list(
        session.scalars(
            select(ProductionOrderStep)
            .where(ProductionOrderStep.production_order_id == order_id)
            .order_by(ProductionOrderStep.sequence)
        )
    )


def _strict_policy(session, ctx, order_id, **overrides):
    payload = {
        "weighing_policy": POLICY_WEIGHING_REQUIRED,
        "verification_policy": VERIFICATION_SECOND_PERSON,
        "completion_tolerance": Decimal("10"),
        "allow_short_close": True,
        "absolute_tolerance": Decimal("50"),
        "percent_tolerance": Decimal("5"),
        "idempotency_key": uuid4(),
    }
    payload.update(overrides)
    return set_execution_policy(session, ctx["principal"], order_id=order_id, **payload)


def _verifier(session, ctx):
    user = helpers.user(session, f"conf-{uuid4().hex[:8]}@example.com")
    helpers.membership(session, ctx["organization"], user, "baker_operator")
    return helpers.principal_for(user, ctx["organization"], "baker_operator")


def _weigh_batch(session, ctx, batch, verifier=None):
    opened = open_weighing_session(
        session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    entries = []
    for material in _materials(session, batch.id):
        entry = record_weighing(
            session,
            ctx["principal"],
            session_id=opened.id,
            batch_material_id=material.id,
            quantity=material.planned_gross_quantity,
            measurement_unit_id=ctx["unit"].id,
            idempotency_key=uuid4(),
            lot_code="L1",
        )
        if verifier is not None:
            verify_weighing(
                session,
                verifier,
                entry_id=entry.id,
                decision=VERIFY_ACCEPTED,
                idempotency_key=uuid4(),
            )
        entries.append(entry)
    complete_weighing_session(
        session, ctx["principal"], session_id=opened.id, idempotency_key=uuid4()
    )
    return opened, entries


def _consume_and_yield(session, ctx, batch):
    for material in _materials(session, batch.id):
        record_consumption(
            session,
            ctx["principal"],
            batch_id=batch.id,
            batch_material_id=material.id,
            consumption_type=CONSUMPTION_CONSUME,
            quantity=material.planned_gross_quantity,
            measurement_unit_id=ctx["unit"].id,
            idempotency_key=uuid4(),
        )
    return record_yield(
        session,
        ctx["principal"],
        batch_id=batch.id,
        measurement_type=YIELD_POST_BAKE_MASS,
        quantity=batch.target_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )


def _run_steps(session, ctx, batch):
    for step in _steps(session, batch.production_order_id):
        run = mark_step_ready(
            session,
            ctx["principal"],
            batch_id=batch.id,
            order_step_id=step.id,
            idempotency_key=uuid4(),
        )
        start_step(
            session,
            ctx["principal"],
            batch_id=batch.id,
            order_step_id=step.id,
            idempotency_key=uuid4(),
            expected_row_version=run.row_version,
        )
        complete_step(
            session,
            ctx["principal"],
            batch_id=batch.id,
            order_step_id=step.id,
            idempotency_key=uuid4(),
        )


def test_release_requires_and_freezes_policy(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-pol")
    plan = create_plan(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        operational_date=date(2026, 8, 22),
        idempotency_key=uuid4(),
    )
    item = upsert_plan_item(
        db_session,
        ctx["principal"],
        plan_id=plan.id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("3300"),
        sort_order=1,
        idempotency_key=uuid4(),
    )
    schedule_plan(db_session, ctx["principal"], plan_id=plan.id, idempotency_key=uuid4())
    order = create_order(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("3300"),
        plan_id=plan.id,
        plan_item_id=item.id,
        formulation_version_id=ctx["version"].id,
        scale_calculation_id=ctx["scale"].id,
        idempotency_key=uuid4(),
    )
    schedule_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    split_batches(db_session, ctx["principal"], order_id=order.id, count=1, idempotency_key=uuid4())
    with pytest.raises(ValidationError, match="politica_execucao"):
        release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    policy = set_execution_policy(
        db_session,
        ctx["principal"],
        order_id=order.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("8"),
        allow_short_close=False,
        absolute_tolerance=Decimal("10"),
        idempotency_key=uuid4(),
    )
    released = release_order(
        db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4()
    )
    db_session.refresh(policy)
    assert policy.frozen_at is not None
    assert policy.policy_hash
    event = db_session.scalars(
        select(ProductionEvent).where(
            ProductionEvent.event_type == EVENT_ORDER_RELEASED,
            ProductionEvent.order_id == released.id,
        )
    ).first()
    assert event is not None
    assert event.payload["policy_hash"] == policy.policy_hash
    with pytest.raises(ImmutableError):
        set_execution_policy(
            db_session,
            ctx["principal"],
            order_id=released.id,
            weighing_policy="required",
            verification_policy="none",
            completion_tolerance=Decimal("1"),
            allow_short_close=True,
            idempotency_key=uuid4(),
        )


def test_one_open_session_and_ledger(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-wgh")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    first = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    with pytest.raises(InvalidStateError, match="sessao_aberta"):
        open_weighing_session(
            db_session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
        )
    material = _materials(db_session, batch.id)[0]
    recorded = record_weighing(
        db_session,
        ctx["principal"],
        session_id=first.id,
        batch_material_id=material.id,
        quantity=material.planned_gross_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    reversed_row = reverse_weighing(
        db_session,
        ctx["principal"],
        session_id=first.id,
        original_entry_id=recorded.id,
        idempotency_key=uuid4(),
        justification="erro de balança",
    )
    assert reversed_row.entry_type == ENTRY_REVERSAL
    assert effective_weighed_quantity(db_session, material.id) == Decimal("0")
    correction = correct_weighing(
        db_session,
        ctx["principal"],
        session_id=first.id,
        original_entry_id=recorded.id,
        quantity=material.planned_gross_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    assert correction.entry_type == ENTRY_CORRECTION
    assert effective_weighed_quantity(db_session, material.id) == material.planned_gross_quantity
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE production_weighing_entry SET quantity = 1 WHERE id = :id"),
            {"id": recorded.id},
        )
    db_session.rollback()


def test_incompatible_unit_and_decimal_tolerance(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-unt")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    opened = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    material = _materials(db_session, batch.id)[0]
    volume = helpers.milliliter(db_session)
    with pytest.raises(ValidationError, match="incompatível"):
        record_weighing(
            db_session,
            ctx["principal"],
            session_id=opened.id,
            batch_material_id=material.id,
            quantity=Decimal("10"),
            measurement_unit_id=volume.id,
            idempotency_key=uuid4(),
        )
    off = record_weighing(
        db_session,
        ctx["principal"],
        session_id=opened.id,
        batch_material_id=material.id,
        quantity=material.planned_gross_quantity + Decimal("20"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
        justification="ajuste de umidade",
    )
    assert off.within_tolerance is True
    assert off.absolute_difference == Decimal("20.000000")
    far = record_weighing(
        db_session,
        ctx["principal"],
        session_id=opened.id,
        batch_material_id=material.id,
        quantity=material.planned_gross_quantity + Decimal("80"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
        justification="erro operacional",
    )
    assert far.within_tolerance is False
    with pytest.raises(ValidationError, match="justificativa"):
        record_weighing(
            db_session,
            ctx["principal"],
            session_id=opened.id,
            batch_material_id=material.id,
            quantity=material.planned_gross_quantity + Decimal("90"),
            measurement_unit_id=ctx["unit"].id,
            idempotency_key=uuid4(),
        )


def test_no_self_verify_and_reject_requires_correction(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-ver")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    _strict_policy(db_session, ctx, order.id)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    opened = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    material = _materials(db_session, batch.id)[0]
    entry = record_weighing(
        db_session,
        ctx["principal"],
        session_id=opened.id,
        batch_material_id=material.id,
        quantity=material.planned_gross_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    with pytest.raises(ValidationError, match="autoconferencia"):
        verify_weighing(
            db_session,
            ctx["principal"],
            entry_id=entry.id,
            decision=VERIFY_ACCEPTED,
            idempotency_key=uuid4(),
        )
    verifier = _verifier(db_session, ctx)
    verify_weighing(
        db_session,
        verifier,
        entry_id=entry.id,
        decision=VERIFY_REJECTED,
        justification="lote ilegível",
        idempotency_key=uuid4(),
    )
    correction = correct_weighing(
        db_session,
        ctx["principal"],
        session_id=opened.id,
        original_entry_id=entry.id,
        quantity=material.planned_gross_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
        lot_code="L2",
    )
    verify_weighing(
        db_session,
        verifier,
        entry_id=correction.id,
        decision=VERIFY_ACCEPTED,
        idempotency_key=uuid4(),
    )
    assert entry.id != correction.id


def test_weighed_is_not_consumed(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-div")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    _weigh_batch(db_session, ctx, batch)
    material = _materials(db_session, batch.id)[0]
    weighed = effective_weighed_quantity(db_session, material.id)
    consumed = project_consumption(db_session, material.id)
    assert weighed > 0
    assert consumed["consume"] == Decimal("0")
    record_consumption(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        batch_material_id=material.id,
        consumption_type=CONSUMPTION_CONSUME,
        quantity=weighed,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    record_consumption(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        batch_material_id=material.id,
        consumption_type=CONSUMPTION_RETURN,
        quantity=Decimal("10"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
        reason="sobra",
    )
    record_consumption(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        batch_material_id=material.id,
        consumption_type=CONSUMPTION_WASTE,
        quantity=Decimal("5"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
        reason="queda",
    )
    projected = project_consumption(db_session, material.id)
    assert projected["return"] == Decimal("10.000000")
    assert projected["waste"] == Decimal("5.000000")
    assert projected["net"] == weighed - Decimal("10")


def test_step_transitions_and_concurrency(engine) -> None:
    session = Session(bind=engine, future=True)
    ctx = _context(session, f"org-ex-stp-{uuid4().hex[:8]}")
    _, _, order = _plan_and_order(session, ctx, batches=1)
    release_order(session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    mark_order_ready(session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(session, order.id)[0]
    step = _steps(session, order.id)[0]
    run = mark_step_ready(
        session, ctx["principal"], batch_id=batch.id, order_step_id=step.id, idempotency_key=uuid4()
    )
    start_step(
        session,
        ctx["principal"],
        batch_id=batch.id,
        order_step_id=step.id,
        idempotency_key=uuid4(),
        expected_row_version=run.row_version,
    )
    hold_step(
        session,
        ctx["principal"],
        batch_id=batch.id,
        order_step_id=step.id,
        reason="espera forno",
        idempotency_key=uuid4(),
    )
    resume_step(
        session, ctx["principal"], batch_id=batch.id, order_step_id=step.id, idempotency_key=uuid4()
    )
    session.commit()
    errors: list[str] = []

    def worker() -> None:
        local = Session(bind=engine, future=True)
        try:
            complete_step(
                local,
                ctx["principal"],
                batch_id=batch.id,
                order_step_id=step.id,
                idempotency_key=uuid4(),
            )
            local.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(type(exc).__name__)
            local.rollback()
        finally:
            local.close()

    threads = [Thread(target=worker), Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    check = Session(bind=engine, future=True)
    from app.modules.production_execution.models import ProductionStepExecution

    runs = check.scalars(
        select(ProductionStepExecution).where(
            ProductionStepExecution.production_batch_id == batch.id
        )
    ).all()
    completed = [row for row in runs if row.status == STEP_COMPLETED]
    check.close()
    session.close()
    assert len(completed) == 1
    assert errors


def test_dependency_blocks_and_override(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-dep")
    _, _, pred = _plan_and_order(db_session, ctx, batches=1)
    dependent = create_order(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("3300"),
        formulation_version_id=ctx["version"].id,
        scale_calculation_id=ctx["scale"].id,
        idempotency_key=uuid4(),
    )
    schedule_order(db_session, ctx["principal"], order_id=dependent.id, idempotency_key=uuid4())
    split_batches(
        db_session, ctx["principal"], order_id=dependent.id, count=1, idempotency_key=uuid4()
    )
    set_execution_policy(
        db_session,
        ctx["principal"],
        order_id=dependent.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        idempotency_key=uuid4(),
    )
    dep = add_dependency(
        db_session,
        ctx["principal"],
        dependent_order_id=dependent.id,
        predecessor_order_id=pred.id,
        dependency_type=DEPENDENCY_PREFERMENT,
        idempotency_key=uuid4(),
    )
    release_order(db_session, ctx["principal"], order_id=dependent.id, idempotency_key=uuid4())
    mark_order_ready(db_session, ctx["principal"], order_id=dependent.id, idempotency_key=uuid4())
    batch = _batches(db_session, dependent.id)[0]
    step = _steps(db_session, dependent.id)[0]
    mark_step_ready(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        order_step_id=step.id,
        idempotency_key=uuid4(),
    )
    with pytest.raises(InvalidStateError, match="dependencia"):
        start_step(
            db_session,
            ctx["principal"],
            batch_id=batch.id,
            order_step_id=step.id,
            idempotency_key=uuid4(),
        )
    release_order(db_session, ctx["principal"], order_id=pred.id, idempotency_key=uuid4())
    short_close_order(
        db_session,
        ctx["principal"],
        order_id=pred.id,
        reason="pré-fermento insuficiente",
        idempotency_key=uuid4(),
    )
    with pytest.raises(InvalidStateError, match="encerrada"):
        start_step(
            db_session,
            ctx["principal"],
            batch_id=batch.id,
            order_step_id=step.id,
            idempotency_key=uuid4(),
        )
    override_dependency(
        db_session,
        ctx["principal"],
        dependency_id=dep.id,
        reason="gestor autoriza continuar",
        idempotency_key=uuid4(),
    )
    started = start_step(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        order_step_id=step.id,
        idempotency_key=uuid4(),
    )
    assert started.status == STEP_IN_PROGRESS


def test_yield_reconstructable_and_blocking_occurrence(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-yld")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    mark_order_ready(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    first = record_yield(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        measurement_type=YIELD_POST_BAKE_MASS,
        quantity=Decimal("1000"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    reverse_yield(db_session, ctx["principal"], measurement_id=first.id, idempotency_key=uuid4())
    record_yield(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        measurement_type=YIELD_POST_BAKE_MASS,
        quantity=batch.target_quantity,
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    projection = project_yield(db_session, batch)
    assert projection.final_mass == batch.target_quantity
    assert projection.completeness == "complete"
    _consume_and_yield(db_session, ctx, batch)
    _run_steps(db_session, ctx, batch)
    occ = record_occurrence(
        db_session,
        ctx["principal"],
        order_id=order.id,
        category=OCCURRENCE_QUALITY,
        severity=SEVERITY_HIGH,
        description="crosta queimada",
        is_blocking=True,
        batch_id=batch.id,
        idempotency_key=uuid4(),
        evidence_refs=["foto-1"],
    )
    with pytest.raises(InvalidStateError, match="ocorrencia_bloqueante"):
        complete_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    resolve_occurrence(
        db_session,
        ctx["principal"],
        occurrence_id=occ.id,
        notes="lote isolado e descartado",
        idempotency_key=uuid4(),
    )


def test_complete_and_short_close(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-cmp")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    mark_order_ready(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    _consume_and_yield(db_session, ctx, batch)
    _run_steps(db_session, ctx, batch)
    completed = complete_order(
        db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4()
    )
    assert completed.status == ORDER_STATUS_COMPLETED

    ctx2 = _context(db_session, "org-ex-shc")
    _, _, short = _plan_and_order(db_session, ctx2, batches=1)
    release_order(db_session, ctx2["principal"], order_id=short.id, idempotency_key=uuid4())
    mark_order_ready(db_session, ctx2["principal"], order_id=short.id, idempotency_key=uuid4())
    closed = short_close_order(
        db_session,
        ctx2["principal"],
        order_id=short.id,
        reason="forno interrompido",
        idempotency_key=uuid4(),
    )
    assert closed.status == ORDER_STATUS_SHORT_CLOSED
    assert closed.short_close_reason == "forno interrompido"


def test_hold_preserves_facts_and_cancel_blocked(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-hld")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    _weigh_batch(db_session, ctx, batch)
    held = hold_order(
        db_session,
        ctx["principal"],
        order_id=order.id,
        reason="falta energia",
        idempotency_key=uuid4(),
    )
    assert held.status == ORDER_STATUS_ON_HOLD
    with pytest.raises(InvalidStateError, match="cancelamento_incompativel"):
        cancel_order(
            db_session,
            ctx["principal"],
            order_id=order.id,
            reason="desistir",
            idempotency_key=uuid4(),
        )
    resumed = resume_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    material = _materials(db_session, batch.id)[0]
    assert effective_weighed_quantity(db_session, material.id) > 0
    assert resumed.status == ORDER_STATUS_IN_PROGRESS or resumed.status != ORDER_STATUS_ON_HOLD


def test_sheet_issue_reissue_and_cancel_block(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-sht")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    first = issue_sheet(
        db_session,
        ctx["principal"],
        order_id=order.id,
        purpose=SHEET_OPERATIONAL,
        idempotency_key=uuid4(),
    )
    second = issue_sheet(
        db_session,
        ctx["principal"],
        order_id=order.id,
        purpose=SHEET_OPERATIONAL,
        idempotency_key=uuid4(),
    )
    assert second.issue_number == first.issue_number + 1
    assert second.previous_issue_id == first.id
    assert first.canonical_payload["establishment"]["code"] == ctx["establishment"].code
    assert first.canonical_payload["issuer"]["user_id"] == str(ctx["actor"].id)
    assert "email" not in str(first.canonical_payload["issuer"])
    assert "cost" not in first.canonical_payload
    first_hash = first.payload_sha256
    db_session.refresh(first)
    assert first.payload_sha256 == first_hash
    cancel_order(
        db_session,
        ctx["principal"],
        order_id=order.id,
        reason="substituir",
        idempotency_key=uuid4(),
    )
    with pytest.raises(InvalidStateError, match="emissao_bloqueada"):
        issue_sheet(
            db_session,
            ctx["principal"],
            order_id=order.id,
            purpose=SHEET_OPERATIONAL,
            idempotency_key=uuid4(),
        )


def test_idempotency_events_permissions_endpoints(db_session: Session) -> None:
    ctx = _context(db_session, "org-ex-idm")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = _batches(db_session, order.id)[0]
    key = uuid4()
    first = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=key
    )
    second = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=key
    )
    assert first.id == second.id
    with pytest.raises(IdempotencyConflictError):
        mark_order_ready(db_session, ctx["principal"], order_id=order.id, idempotency_key=key)
    baker = permissions_for_role("baker_operator")
    manager = permissions_for_role("production_manager")
    technical = permissions_for_role("technical_responsible")
    assert "production.weighing.record" in baker
    assert "production.order.short_close" not in baker
    assert "production.order.complete" in manager
    assert "production.traceability.read" in technical
    assert "production.order.release" not in technical
    assert "costing.read" not in manager
    baker_user = helpers.user(db_session, "baker-ex@example.com")
    helpers.membership(db_session, ctx["organization"], baker_user, "baker_operator")
    baker_principal = helpers.principal_for(baker_user, ctx["organization"], "baker_operator")
    with pytest.raises(PermissionDeniedError):
        complete_order(db_session, baker_principal, order_id=order.id, idempotency_key=uuid4())
    events = list(
        db_session.scalars(select(ProductionEvent).where(ProductionEvent.order_id == order.id))
    )
    assert events
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE production_event SET payload = '{}'::jsonb WHERE id = :id"),
            {"id": events[0].id},
        )
    db_session.rollback()
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code in {200, 503}
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.startswith("/api/v1/production") for path in paths)


def test_rls_execution_isolation(engine) -> None:
    from sqlalchemy.orm import sessionmaker
    from tests.rls_support import runtime_engine as build_runtime

    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    ctx_a = _context(session, f"org-ex-rls-a-{uuid4().hex[:8]}")
    ctx_b = _context(session, f"org-ex-rls-b-{uuid4().hex[:8]}")
    _, _, order_a = _plan_and_order(session, ctx_a, batches=1)
    _plan_and_order(session, ctx_b, batches=1)
    release_order(session, ctx_a["principal"], order_id=order_a.id, idempotency_key=uuid4())
    session.commit()
    session.close()
    runtime = build_runtime(engine)
    try:
        with runtime.connect() as connection:
            trans = connection.begin()
            connection.execute(
                text("SELECT set_config('app.current_organization_id', :v, true)"),
                {"v": str(ctx_a["organization"].id)},
            )
            connection.execute(
                text("SELECT set_config('app.current_user_id', :v, true)"),
                {"v": str(ctx_a["actor"].id)},
            )
            seen = connection.execute(
                text("SELECT production_order_id FROM production_execution_policy")
            ).scalars().all()
            assert order_a.id in seen
            assert len(seen) == 1
            with pytest.raises(Exception):
                connection.execute(
                    text(
                        "UPDATE production_execution_policy SET organization_id = :other "
                        "WHERE production_order_id = :id"
                    ),
                    {"other": ctx_b["organization"].id, "id": order_a.id},
                )
            trans.rollback()
            trans = connection.begin()
            rows = connection.execute(text("SELECT id FROM production_execution_policy")).fetchall()
            assert rows == []
            trans.rollback()
    finally:
        runtime.dispose()


def test_no_external_calls_imported() -> None:
    import app.modules.production_execution as execution

    source = open(execution.__file__, encoding="utf-8").read()
    assert "bedrock" not in source.lower()
    assert "cognito" not in source.lower()
    assert "boto3" not in source


def test_sheet_payload_snapshots_and_stability(db_session: Session) -> None:
    from app.modules.production_execution.models import ProductionSheetIssue
    from app.modules.production_planning.support import digest

    ctx = _context(db_session, "org-ex-snp")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    first = issue_sheet(
        db_session,
        ctx["principal"],
        order_id=order.id,
        purpose=SHEET_OPERATIONAL,
        idempotency_key=uuid4(),
    )
    assert first.canonical_payload["establishment"]["display_name"] == ctx["establishment"].display_name
    assert first.canonical_payload["organization"]["slug"] == ctx["organization"].slug
    assert first.canonical_payload["issuer"]["display_name"] == ctx["actor"].display_name
    assert "production_responsible" not in first.canonical_payload
    original_hash = first.payload_sha256
    original_payload = dict(first.canonical_payload)
    ctx["establishment"].display_name = "Nome vivo alterado"
    ctx["actor"].display_name = "Outro nome"
    db_session.flush()
    db_session.refresh(first)
    assert first.canonical_payload["establishment"]["display_name"] == original_payload["establishment"][
        "display_name"
    ]
    assert first.canonical_payload["issuer"]["display_name"] == original_payload["issuer"]["display_name"]
    assert first.payload_sha256 == original_hash
    second = issue_sheet(
        db_session,
        ctx["principal"],
        order_id=order.id,
        purpose=SHEET_OPERATIONAL,
        idempotency_key=uuid4(),
    )
    assert second.canonical_payload["establishment"]["display_name"] == "Nome vivo alterado"
    assert second.payload_sha256 != original_hash
    old = ProductionSheetIssue(
        organization_id=order.organization_id,
        establishment_id=order.establishment_id,
        production_order_id=order.id,
        issue_number=90,
        template_version="1",
        canonical_payload={"schema_version": "1", "order": {"public_code": order.public_code}},
        payload_sha256=digest({"schema_version": "1"}),
        issued_by_user_id=ctx["actor"].id,
        purpose=SHEET_OPERATIONAL,
        order_status_at_issue=order.status,
        idempotency_key=uuid4(),
    )
    db_session.add(old)
    db_session.flush()
    db_session.refresh(old)
    assert "establishment" not in old.canonical_payload
    assert old.canonical_payload["order"]["public_code"] == order.public_code


def test_no_legacy_role_label_authorization() -> None:
    from pathlib import Path

    auth = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "modules"
        / "identity_organization"
        / "authorization.py"
    ).read_text(encoding="utf-8")
    http = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).resolve().parents[1] / "app" / "modules" / "production_http").glob(
            "*.py"
        )
    )
    assert "legacy_role_label" not in auth
    assert "legacy_role_label" not in http
