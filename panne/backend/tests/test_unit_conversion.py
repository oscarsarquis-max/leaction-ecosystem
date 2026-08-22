from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.modules.production_execution.policy import adopt_execution_policy
from app.modules.production_execution.projections import effective_weighed_quantity
from app.modules.production_execution.units import convert_to_canonical_mass
from app.modules.production_execution.weighing import open_weighing_session, record_weighing
from app.modules.production_planning.commands import (
    create_order,
    create_plan,
    release_order,
    schedule_order,
    schedule_plan,
    split_batches,
    upsert_plan_item,
)
from app.modules.production_planning.constants import (
    BATCH_STATUS_SCRAPPED,
    ORDER_STATUS_RELEASED,
    TARGET_MODE_MASS,
)
from app.modules.production_planning.errors import (
    ImmutableError,
    InvalidStateError,
    ValidationError,
)
from app.modules.production_planning.models import ProductionBatch, ProductionBatchMaterial
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_production_planning import _context, _plan_and_order


def test_g_to_kg_and_kg_to_g(db_session: Session) -> None:
    ctx = _context(db_session, f"unit-gkg-{uuid4().hex[:6]}")
    gram = ctx["unit"]
    kg = helpers_kilogram(db_session)
    g_to_kg = convert_to_canonical_mass(db_session, Decimal("1000"), gram.id)
    assert g_to_kg.entered_quantity == Decimal("1000.000000")
    assert g_to_kg.entered_unit_code == "g"
    assert g_to_kg.canonical_unit_code == "g"
    assert g_to_kg.canonical_quantity == Decimal("1000.000000")
    kg_to_g = convert_to_canonical_mass(db_session, Decimal("1"), kg.id)
    assert kg_to_g.entered_quantity == Decimal("1.000000")
    assert kg_to_g.entered_unit_code == "kg"
    assert kg_to_g.canonical_unit_code == "g"
    assert kg_to_g.canonical_quantity == Decimal("1000.000000")
    assert kg_to_g.factor == Decimal("1000.0000000000")
    assert kg_to_g.source == "measurement_unit.si_factor"
    ml = helpers_ml(db_session)
    with pytest.raises(ValidationError, match="conversao_massa_volume_proibida"):
        convert_to_canonical_mass(db_session, Decimal("10"), ml.id)


def helpers_kilogram(session):
    from tests import helpers

    return helpers.kilogram(session)


def helpers_ml(session):
    from tests import helpers

    return helpers.milliliter(session)


def test_weighing_keeps_original_and_canonical(db_session: Session) -> None:
    ctx = _context(db_session, f"unit-w-{uuid4().hex[:6]}")
    _, _, order = _plan_and_order(db_session, ctx)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    batch = db_session.scalar(
        select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
    )
    material = db_session.scalar(
        select(ProductionBatchMaterial).where(
            ProductionBatchMaterial.production_batch_id == batch.id
        )
    )
    weigh = open_weighing_session(
        db_session, ctx["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    kg = helpers_kilogram(db_session)
    planned = material.planned_gross_quantity
    entered = (planned / Decimal("1000")).quantize(Decimal("0.000001"))
    entry = record_weighing(
        db_session,
        ctx["principal"],
        session_id=weigh.id,
        batch_material_id=material.id,
        quantity=entered,
        measurement_unit_id=kg.id,
        idempotency_key=uuid4(),
        justification="conversao",
    )
    assert entry.quantity == entered
    assert entry.unit_code == "kg"
    assert entry.canonical_unit_code == "g"
    assert entry.canonical_quantity != entered
    assert effective_weighed_quantity(db_session, material.id) == entry.canonical_quantity


def test_adopt_policy_without_facts_and_reject_after_facts(db_session: Session) -> None:
    ctx = _context(db_session, f"unit-ad-{uuid4().hex[:6]}")
    _, _, order = _plan_and_order(db_session, ctx)
    order.status = ORDER_STATUS_RELEASED
    db_session.flush()
    key = uuid4()
    adopted = adopt_execution_policy(
        db_session,
        ctx["principal"],
        order_id=order.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        reason="ordem antiga sem politica",
        idempotency_key=key,
    )
    assert adopted.policy_hash
    assert adopted.frozen_at is not None
    replay = adopt_execution_policy(
        db_session,
        ctx["principal"],
        order_id=order.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        reason="ordem antiga sem politica",
        idempotency_key=key,
    )
    assert replay.id == adopted.id
    with pytest.raises(ImmutableError):
        adopt_execution_policy(
            db_session,
            ctx["principal"],
            order_id=order.id,
            weighing_policy="optional",
            verification_policy="none",
            completion_tolerance=Decimal("10"),
            allow_short_close=True,
            reason="segunda tentativa",
            idempotency_key=uuid4(),
        )
    ctx2 = _context(db_session, f"unit-af-{uuid4().hex[:6]}")
    _, _, order2 = _plan_and_order(db_session, ctx2)
    release_order(db_session, ctx2["principal"], order_id=order2.id, idempotency_key=uuid4())
    batch = db_session.scalar(
        select(ProductionBatch).where(ProductionBatch.production_order_id == order2.id)
    )
    material = db_session.scalar(
        select(ProductionBatchMaterial).where(
            ProductionBatchMaterial.production_batch_id == batch.id
        )
    )
    weigh = open_weighing_session(
        db_session, ctx2["principal"], batch_id=batch.id, idempotency_key=uuid4()
    )
    record_weighing(
        db_session,
        ctx2["principal"],
        session_id=weigh.id,
        batch_material_id=material.id,
        quantity=material.planned_gross_quantity,
        measurement_unit_id=ctx2["unit"].id,
        idempotency_key=uuid4(),
    )
    # recreate old-style missing policy is impossible after facts; reject adopt
    with pytest.raises(InvalidStateError):
        adopt_execution_policy(
            db_session,
            ctx2["principal"],
            order_id=order2.id,
            weighing_policy="optional",
            verification_policy="none",
            completion_tolerance=Decimal("10"),
            allow_short_close=True,
            reason="depois dos fatos",
            idempotency_key=uuid4(),
        )


def test_adopt_creates_policy_when_row_missing(db_session: Session) -> None:
    ctx = _context(db_session, f"unit-np-{uuid4().hex[:6]}")
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
    order.status = ORDER_STATUS_RELEASED
    db_session.flush()
    adopted = adopt_execution_policy(
        db_session,
        ctx["principal"],
        order_id=order.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        reason="liberada sem politica",
        idempotency_key=uuid4(),
    )
    assert adopted.policy_hash
    assert adopted.frozen_at is not None


def test_scrapped_is_catalog_only() -> None:
    from app.modules.production_execution import constants
    from app.modules.production_planning import constants as planning

    assert BATCH_STATUS_SCRAPPED == "scrapped"
    assert not hasattr(constants, "COMMAND_SCRAP")
    assert not hasattr(planning, "COMMAND_SCRAP")
