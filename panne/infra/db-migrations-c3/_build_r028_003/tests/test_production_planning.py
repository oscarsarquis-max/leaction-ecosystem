from datetime import date
from decimal import Decimal
from threading import Thread
from uuid import uuid4

import pytest
from app.modules.calculation_engine.scale import (
    calculate_total_dough_mass,
    persist_scale_calculation,
)
from app.modules.formula_lab.models import FormulationItem
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_ORDER_RELEASE,
    permissions_for_role,
)
from app.modules.production_execution.policy import set_execution_policy
from app.modules.production_planning.commands import (
    add_dependency,
    cancel_order,
    create_order,
    create_plan,
    create_substitute_order,
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
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_RELEASED,
    TARGET_MODE_MASS,
    TARGET_MODE_UNITS,
)
from app.modules.production_planning.errors import (
    CycleError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.production_planning.events import append_event
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionEvent,
    ProductionOrderMaterial,
    ProductionOrderStep,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests import helpers


def _context(session: Session, slug: str, role: str = "production_manager"):
    organization = helpers.org(session, slug)
    establishment = helpers.establishment(session, organization, "E1")
    actor = helpers.user(session, f"{slug}@example.com")
    helpers.membership(session, organization, actor, role)
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, f"P-{slug[-6:]}")
    recipe = helpers.formulation(session, product, f"F-{slug[-6:]}")
    version = helpers.formulation_version(session, recipe)
    flour = helpers.published_ingredient(session, organization, unit, f"FAR-{slug[-6:]}")
    water = helpers.published_ingredient(session, organization, unit, f"AGU-{slug[-6:]}")
    helpers.formulation_item(session, version, flour, unit, 1, Decimal("1000"), is_flour_basis=True)
    helpers.formulation_item(session, version, water, unit, 2, Decimal("650"))
    helpers.process_step(session, version, 1)
    helpers.approve_version(session, version, actor)
    from app.modules.formula_lab.rules import publish_formulation_version

    publish_formulation_version(session, version)
    loaded = list(
        session.scalars(
            select(FormulationItem).where(FormulationItem.formulation_version_id == version.id)
        )
    )
    scale = persist_scale_calculation(
        session, version, calculate_total_dough_mass(loaded, Decimal("3300")), actor.id
    )
    principal = helpers.principal_for(actor, organization, role)
    return {
        "organization": organization,
        "establishment": establishment,
        "actor": actor,
        "product": product,
        "version": version,
        "scale": scale,
        "principal": principal,
        "unit": unit,
    }


def _plan_and_order(session: Session, ctx, *, batches: int = 2):
    plan = create_plan(
        session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        operational_date=date(2026, 8, 22),
        idempotency_key=uuid4(),
        shift="morning",
    )
    item = upsert_plan_item(
        session,
        ctx["principal"],
        plan_id=plan.id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("3300"),
        sort_order=1,
        idempotency_key=uuid4(),
    )
    schedule_plan(session, ctx["principal"], plan_id=plan.id, idempotency_key=uuid4())
    order = create_order(
        session,
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
    schedule_order(session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    split_batches(
        session, ctx["principal"], order_id=order.id, count=batches, idempotency_key=uuid4()
    )
    set_execution_policy(
        session,
        ctx["principal"],
        order_id=order.id,
        weighing_policy="optional",
        verification_policy="none",
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        absolute_tolerance=Decimal("50"),
        idempotency_key=uuid4(),
    )
    return plan, item, order


def test_release_creates_immutable_snapshots(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-rel")
    _, _, order = _plan_and_order(db_session, ctx)
    released = release_order(
        db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4()
    )
    assert released.status == ORDER_STATUS_RELEASED
    assert released.materials_hash and released.steps_hash and released.snapshot_hash
    materials = list(
        db_session.scalars(
            select(ProductionOrderMaterial).where(
                ProductionOrderMaterial.production_order_id == order.id
            )
        )
    )
    steps = list(
        db_session.scalars(
            select(ProductionOrderStep).where(ProductionOrderStep.production_order_id == order.id)
        )
    )
    assert len(materials) == 2
    assert len(steps) == 1
    assert materials[0].operational_name
    assert materials[0].unit_code == "g"
    allocations = list(db_session.scalars(select(ProductionBatchMaterial)))
    assert allocations
    net = sum(
        (
            row.planned_net_quantity
            for row in allocations
            if row.production_order_material_id == materials[0].id
        ),
        Decimal("0"),
    )
    assert net == materials[0].net_quantity
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE production_order_material SET operational_name = 'x' WHERE id = :id"),
            {"id": materials[0].id},
        )
    db_session.rollback()


def test_release_rejects_unapproved_formulation(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-unap")
    helpers.approve_version(db_session, ctx["version"], ctx["actor"], decision="rejected")
    _, _, order = _plan_and_order(db_session, ctx)
    with pytest.raises(ValidationError, match="aprovacao"):
        release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())


def test_incompatible_product_formulation_scale(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-inc")
    other = helpers.technical_product(db_session, ctx["organization"], "OUTRO")
    other_recipe = helpers.formulation(db_session, other, "F-OUTRO")
    other_version = helpers.formulation_version(db_session, other_recipe)
    helpers.approve_version(db_session, other_version, ctx["actor"])
    from app.modules.formula_lab.rules import publish_formulation_version

    publish_formulation_version(db_session, other_version)
    order = create_order(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        technical_product_id=other.id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("3300"),
        formulation_version_id=ctx["version"].id,
        scale_calculation_id=ctx["scale"].id,
        idempotency_key=uuid4(),
    )
    schedule_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    split_batches(db_session, ctx["principal"], order_id=order.id, count=1, idempotency_key=uuid4())
    with pytest.raises(ValidationError, match="incompat"):
        release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())


def test_dependency_rejects_cross_org_self_and_cycle(db_session: Session) -> None:
    ctx_a = _context(db_session, "org-dep-a")
    ctx_b = _context(db_session, "org-dep-b")
    _, _, first = _plan_and_order(db_session, ctx_a, batches=1)
    _, _, second = _plan_and_order(db_session, ctx_a, batches=1)
    _, _, foreign = _plan_and_order(db_session, ctx_b, batches=1)
    with pytest.raises(ValidationError, match="organizacoes"):
        add_dependency(
            db_session,
            ctx_a["principal"],
            dependent_order_id=first.id,
            predecessor_order_id=foreign.id,
            dependency_type=DEPENDENCY_PREFERMENT,
            idempotency_key=uuid4(),
        )
    with pytest.raises(ValidationError, match="autorreferencia"):
        add_dependency(
            db_session,
            ctx_a["principal"],
            dependent_order_id=first.id,
            predecessor_order_id=first.id,
            dependency_type=DEPENDENCY_PREFERMENT,
            idempotency_key=uuid4(),
        )
    add_dependency(
        db_session,
        ctx_a["principal"],
        dependent_order_id=second.id,
        predecessor_order_id=first.id,
        dependency_type=DEPENDENCY_PREFERMENT,
        idempotency_key=uuid4(),
    )
    with pytest.raises(CycleError):
        add_dependency(
            db_session,
            ctx_a["principal"],
            dependent_order_id=first.id,
            predecessor_order_id=second.id,
            dependency_type=DEPENDENCY_PREFERMENT,
            idempotency_key=uuid4(),
        )


def test_batch_split_is_deterministic_and_exact(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-bat")
    _, _, order = _plan_and_order(db_session, ctx, batches=3)
    batches = list(
        db_session.scalars(
            select(ProductionBatch)
            .where(ProductionBatch.production_order_id == order.id)
            .order_by(ProductionBatch.sequence)
        )
    )
    assert len(batches) == 3
    assert sum((row.target_quantity for row in batches), Decimal("0")) == Decimal("3300")
    again = split_batches(
        db_session, ctx["principal"], order_id=order.id, count=3, idempotency_key=uuid4()
    )
    assert [row.target_quantity for row in again] == [row.target_quantity for row in batches]


def test_release_idempotent_and_conflict(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-idm")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    key = uuid4()
    first = release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=key)
    second = release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=key)
    assert first.snapshot_hash == second.snapshot_hash
    events = list(
        db_session.scalars(
            select(ProductionEvent).where(
                ProductionEvent.order_id == order.id,
                ProductionEvent.event_type == EVENT_ORDER_RELEASED,
            )
        )
    )
    assert len(events) == 1
    with pytest.raises(IdempotencyConflictError):
        hold_order(
            db_session,
            ctx["principal"],
            order_id=order.id,
            reason="pausa",
            idempotency_key=key,
        )


def test_snapshot_survives_catalog_change(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-snap")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    material = db_session.scalars(select(ProductionOrderMaterial)).first()
    assert material is not None
    original = material.operational_name
    db_session.execute(
        text("UPDATE ingredient SET display_name = 'farinha nova' WHERE organization_id = :org"),
        {"org": ctx["organization"].id},
    )
    db_session.flush()
    db_session.refresh(material)
    assert material.operational_name == original


def test_immutability_cancel_and_substitute(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-sub")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    with pytest.raises(ImmutableError):
        split_batches(
            db_session, ctx["principal"], order_id=order.id, count=2, idempotency_key=uuid4()
        )
    cancelled = cancel_order(
        db_session,
        ctx["principal"],
        order_id=order.id,
        reason="farinha errada",
        idempotency_key=uuid4(),
    )
    assert cancelled.status == ORDER_STATUS_CANCELLED
    assert cancelled.cancel_reason == "farinha errada"
    assert cancelled.materials_hash
    substitute = create_substitute_order(
        db_session,
        ctx["principal"],
        cancelled_order_id=order.id,
        idempotency_key=uuid4(),
    )
    db_session.refresh(order)
    assert order.successor_order_id == substitute.id
    assert substitute.superseded_order_id == order.id
    assert substitute.status == "draft"


def test_hold_and_invalid_transition(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-hold")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    with pytest.raises(InvalidStateError):
        hold_order(
            db_session,
            ctx["principal"],
            order_id=order.id,
            reason="cedo",
            idempotency_key=uuid4(),
        )
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    held = hold_order(
        db_session,
        ctx["principal"],
        order_id=order.id,
        reason="falta fermento",
        idempotency_key=uuid4(),
    )
    assert held.status == ORDER_STATUS_ON_HOLD


def test_event_rejects_unknown_type_and_extra_fields(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-evt")
    plan, _, order = _plan_and_order(db_session, ctx, batches=1)
    with pytest.raises(ValidationError, match="desconhecido"):
        append_event(
            db_session,
            organization_id=ctx["organization"].id,
            establishment_id=ctx["establishment"].id,
            event_type="cost.calculated",
            command="create_plan",
            actor_user_id=ctx["actor"].id,
            idempotency_key=uuid4(),
            payload={},
            plan_id=plan.id,
        )
    with pytest.raises(ValidationError, match="extra"):
        append_event(
            db_session,
            organization_id=ctx["organization"].id,
            establishment_id=ctx["establishment"].id,
            event_type=EVENT_ORDER_RELEASED,
            command="release_order",
            actor_user_id=ctx["actor"].id,
            idempotency_key=uuid4(),
            payload={
                "public_code": order.public_code,
                "materials_hash": "a",
                "steps_hash": "b",
                "snapshot_hash": "c",
                "policy_hash": "d",
                "margin": "10",
            },
            order_id=order.id,
        )


def test_event_is_append_only(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-apo")
    create_plan(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        operational_date=date(2026, 8, 22),
        idempotency_key=uuid4(),
    )
    event = db_session.scalars(select(ProductionEvent)).first()
    assert event is not None
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE production_event SET payload = '{}'::jsonb WHERE id = :id"),
            {"id": event.id},
        )
    db_session.rollback()
    with pytest.raises(Exception):
        db_session.execute(text("DELETE FROM production_event WHERE id = :id"), {"id": event.id})
    db_session.rollback()


def test_permissions_baker_cannot_manage(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-bak", role="baker_operator")
    with pytest.raises(PermissionDeniedError):
        create_plan(
            db_session,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            operational_date=date(2026, 8, 22),
            idempotency_key=uuid4(),
        )
    assert PERMISSION_PRODUCTION_ORDER_RELEASE not in permissions_for_role("baker_operator")
    assert PERMISSION_PRODUCTION_ORDER_RELEASE in permissions_for_role("production_manager")
    assert PERMISSION_PRODUCTION_ORDER_RELEASE not in permissions_for_role("technical_responsible")
    assert "costing.read" in permissions_for_role("owner")
    assert "costing.read" not in permissions_for_role("baker_operator")


def test_editable_states_and_units_require_weight(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-edit")
    with pytest.raises(ValidationError, match="peso unitário"):
        create_order(
            db_session,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            technical_product_id=ctx["product"].id,
            target_mode=TARGET_MODE_UNITS,
            target_quantity=Decimal("10"),
            idempotency_key=uuid4(),
        )
    create_order(
        db_session,
        ctx["principal"],
        establishment_id=ctx["establishment"].id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_UNITS,
        target_quantity=Decimal("10"),
        unit_weight_g=Decimal("100"),
        idempotency_key=uuid4(),
    )


def test_rls_production_isolation(engine) -> None:
    from sqlalchemy.orm import sessionmaker
    from tests.rls_support import runtime_engine as build_runtime

    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    ctx_a = _context(session, f"org-prod-rls-a-{uuid4().hex[:8]}")
    ctx_b = _context(session, f"org-prod-rls-b-{uuid4().hex[:8]}")
    plan_a, _, _ = _plan_and_order(session, ctx_a, batches=1)
    _plan_and_order(session, ctx_b, batches=1)
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
            seen = connection.execute(text("SELECT id FROM production_plan")).scalars().all()
            assert plan_a.id in seen
            assert len(seen) == 1
            with pytest.raises(Exception):
                connection.execute(
                    text("UPDATE production_plan SET organization_id = :other WHERE id = :id"),
                    {"other": ctx_b["organization"].id, "id": plan_a.id},
                )
            trans.rollback()
            trans = connection.begin()
            rows = connection.execute(text("SELECT id FROM production_plan")).fetchall()
            assert rows == []
            trans.rollback()
    finally:
        runtime.dispose()


def test_concurrent_release_does_not_duplicate_snapshots(engine) -> None:
    session = Session(bind=engine, future=True)
    ctx = _context(session, f"org-prod-con-{uuid4().hex[:8]}")
    _, _, order = _plan_and_order(session, ctx, batches=1)
    session.commit()
    order_id = order.id
    principal = ctx["principal"]
    errors: list[str] = []

    def worker() -> None:
        local = Session(bind=engine, future=True)
        try:
            release_order(local, principal, order_id=order_id, idempotency_key=uuid4())
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
    materials = check.scalars(
        select(ProductionOrderMaterial).where(
            ProductionOrderMaterial.production_order_id == order_id
        )
    ).all()
    events = check.scalars(
        select(ProductionEvent).where(
            ProductionEvent.order_id == order_id, ProductionEvent.event_type == EVENT_ORDER_RELEASED
        )
    ).all()
    check.close()
    session.close()
    assert len(materials) == 2
    assert len(events) == 1
    assert errors


def test_existing_http_and_scale_untouched() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert "production" not in {getattr(route, "path", "") for route in app.routes}


def test_float_rejected(db_session: Session) -> None:
    ctx = _context(db_session, "org-prod-flt")
    with pytest.raises(ValidationError, match="float"):
        create_order(
            db_session,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            technical_product_id=ctx["product"].id,
            target_mode=TARGET_MODE_MASS,
            target_quantity=1.5,  # type: ignore[arg-type]
            idempotency_key=uuid4(),
        )
