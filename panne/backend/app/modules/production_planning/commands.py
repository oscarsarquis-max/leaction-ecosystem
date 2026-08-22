from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.scale import MODE_FINAL_UNITS, MODE_TOTAL_DOUGH_MASS
from app.modules.formula_lab.models import Formulation, FormulationVersion, ScaleCalculation
from app.modules.formula_lab.rules import has_valid_approval
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_BATCH_MANAGE,
    PERMISSION_PRODUCTION_ORDER_CANCEL,
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_ORDER_RELEASE,
    PERMISSION_PRODUCTION_PLAN_MANAGE,
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import Establishment
from app.modules.production_planning.batches import split_memory, split_target
from app.modules.production_planning.codes import next_public_code
from app.modules.production_planning.constants import (
    BATCH_STATUS_PENDING,
    CODE_KIND_ORDER,
    CODE_KIND_PLAN,
    COMMAND_ADD_DEPENDENCY,
    COMMAND_CANCEL_ORDER,
    COMMAND_CREATE_ORDER,
    COMMAND_CREATE_PLAN,
    COMMAND_CREATE_SUBSTITUTE,
    COMMAND_HOLD_ORDER,
    COMMAND_RELEASE_ORDER,
    COMMAND_REMOVE_PLAN_ITEM,
    COMMAND_SCHEDULE_ORDER,
    COMMAND_SCHEDULE_PLAN,
    COMMAND_SPLIT_BATCHES,
    COMMAND_UPSERT_PLAN_ITEM,
    DEPENDENCY_TYPES,
    EVENT_BATCH_SPLIT,
    EVENT_DEPENDENCY_ADDED,
    EVENT_ORDER_CANCELLED,
    EVENT_ORDER_CREATED,
    EVENT_ORDER_HELD,
    EVENT_ORDER_RELEASED,
    EVENT_ORDER_SCHEDULED,
    EVENT_ORDER_SUBSTITUTED,
    EVENT_PLAN_CREATED,
    EVENT_PLAN_ITEM_REMOVED,
    EVENT_PLAN_ITEM_UPSERTED,
    EVENT_PLAN_SCHEDULED,
    ORDER_EDITABLE,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_READY,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SCHEDULED,
    PLAN_STATUS_DRAFT,
    PLAN_STATUS_SCHEDULED,
    SHIFTS,
    SPLIT_METHOD,
    TARGET_MODE_MASS,
    TARGET_MODE_UNITS,
    TARGET_MODES,
)
from app.modules.production_planning.dependencies import assert_acyclic, assert_same_org_pair
from app.modules.production_planning.errors import (
    ConcurrencyError,
    ImmutableError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionOrder,
    ProductionOrderDependency,
    ProductionPlan,
    ProductionPlanItem,
)
from app.modules.production_planning.snapshots import build_release_snapshots
from app.modules.production_planning.support import as_decimal, require_positive


def _permit(principal: Principal, code: str) -> None:
    try:
        require_permission(principal, code)
    except AuthorizationError as exc:
        raise PermissionDeniedError("permissao_negada") from exc


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise PermissionDeniedError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _now() -> datetime:
    return datetime.now(UTC)


def _bump(row: ProductionPlan | ProductionOrder | ProductionBatch) -> None:
    row.row_version += 1
    row.updated_at = _now()


def _target(
    mode: str,
    quantity: Decimal | int | str,
    unit_weight: Decimal | int | str | None,
) -> tuple[str, Decimal, Decimal | None]:
    if mode not in TARGET_MODES:
        raise ValidationError("modo de alvo inválido")
    amount = require_positive(as_decimal(quantity, "alvo"), "alvo")
    weight = None
    if unit_weight is not None:
        weight = require_positive(as_decimal(unit_weight, "peso unitário"), "peso unitário")
    if mode == TARGET_MODE_UNITS and amount != amount.to_integral_value():
        raise ValidationError("unidades devem ser inteiras")
    if mode == TARGET_MODE_UNITS and weight is None:
        raise ValidationError("peso unitário obrigatório para unidades")
    return mode, amount, weight


def create_plan(
    session: Session,
    principal: Principal,
    *,
    establishment_id: UUID,
    operational_date: date,
    idempotency_key: UUID,
    shift: str | None = None,
    notes: str | None = None,
) -> ProductionPlan:
    _permit(principal, PERMISSION_PRODUCTION_PLAN_MANAGE)
    organization_id = _org(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_CREATE_PLAN
    )
    if replay is not None and replay.plan_id is not None:
        plan = session.get(ProductionPlan, replay.plan_id)
        if plan is not None:
            return plan
    establishment = session.get(Establishment, establishment_id)
    if establishment is None or establishment.organization_id != organization_id:
        raise ValidationError("estabelecimento inválido")
    if shift is not None and shift not in SHIFTS:
        raise ValidationError("turno inválido")
    code = next_public_code(session, organization_id, CODE_KIND_PLAN, operational_date)
    plan = ProductionPlan(
        organization_id=organization_id,
        establishment_id=establishment_id,
        public_code=code,
        operational_date=operational_date,
        shift=shift,
        status=PLAN_STATUS_DRAFT,
        notes=notes,
        created_by_user_id=principal.user_id,
    )
    session.add(plan)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=establishment_id,
        event_type=EVENT_PLAN_CREATED,
        command=COMMAND_CREATE_PLAN,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "public_code": code,
            "operational_date": operational_date.isoformat(),
            "shift": shift,
        },
        plan_id=plan.id,
    )
    return plan


def upsert_plan_item(
    session: Session,
    principal: Principal,
    *,
    plan_id: UUID,
    technical_product_id: UUID,
    target_mode: str,
    target_quantity: Decimal | int | str,
    sort_order: int,
    idempotency_key: UUID,
    unit_weight_g: Decimal | int | str | None = None,
    priority: int = 50,
    notes: str | None = None,
    item_id: UUID | None = None,
) -> ProductionPlanItem:
    _permit(principal, PERMISSION_PRODUCTION_PLAN_MANAGE)
    organization_id = _org(principal)
    plan = session.get(ProductionPlan, plan_id)
    if plan is None or plan.organization_id != organization_id:
        raise ValidationError("plano inválido")
    if plan.status not in {PLAN_STATUS_DRAFT, PLAN_STATUS_SCHEDULED}:
        raise InvalidStateError("plano não editável")
    if _plan_item_has_released_order(session, item_id):
        raise ImmutableError("item com ordem liberada")
    mode, amount, weight = _target(target_mode, target_quantity, unit_weight_g)
    if not (1 <= priority <= 99):
        raise ValidationError("prioridade inválida")
    item = session.get(ProductionPlanItem, item_id) if item_id is not None else None
    if item is None:
        item = ProductionPlanItem(
            organization_id=organization_id,
            production_plan_id=plan.id,
            technical_product_id=technical_product_id,
            target_mode=mode,
            target_quantity=amount,
            unit_weight_g=weight,
            priority=priority,
            sort_order=sort_order,
            notes=notes,
        )
        session.add(item)
    else:
        if item.organization_id != organization_id or item.production_plan_id != plan.id:
            raise ValidationError("item inválido")
        item.technical_product_id = technical_product_id
        item.target_mode = mode
        item.target_quantity = amount
        item.unit_weight_g = weight
        item.priority = priority
        item.sort_order = sort_order
        item.notes = notes
        item.updated_at = _now()
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=plan.establishment_id,
        event_type=EVENT_PLAN_ITEM_UPSERTED,
        command=COMMAND_UPSERT_PLAN_ITEM,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "plan_item_id": str(item.id),
            "technical_product_id": str(technical_product_id),
            "sort_order": sort_order,
        },
        plan_id=plan.id,
    )
    return item


def remove_plan_item(
    session: Session,
    principal: Principal,
    *,
    plan_id: UUID,
    item_id: UUID,
    idempotency_key: UUID,
) -> ProductionPlanItem | None:
    _permit(principal, PERMISSION_PRODUCTION_PLAN_MANAGE)
    organization_id = _org(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_REMOVE_PLAN_ITEM
    )
    if replay is not None:
        return session.get(ProductionPlanItem, item_id)
    plan = session.get(ProductionPlan, plan_id)
    if plan is None or plan.organization_id != organization_id:
        raise ValidationError("plano inválido")
    if plan.status not in {PLAN_STATUS_DRAFT, PLAN_STATUS_SCHEDULED}:
        raise InvalidStateError("plano não editável")
    item = session.get(ProductionPlanItem, item_id)
    if (
        item is None
        or item.organization_id != organization_id
        or item.production_plan_id != plan.id
    ):
        raise ValidationError("item inválido")
    if session.scalar(
        select(ProductionOrder.id).where(ProductionOrder.plan_item_id == item.id).limit(1)
    ):
        raise ImmutableError("item com ordem")
    payload = {
        "plan_item_id": str(item.id),
        "technical_product_id": str(item.technical_product_id),
        "sort_order": item.sort_order,
    }
    session.delete(item)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=plan.establishment_id,
        event_type=EVENT_PLAN_ITEM_REMOVED,
        command=COMMAND_REMOVE_PLAN_ITEM,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
        plan_id=plan.id,
    )
    return item


def schedule_plan(
    session: Session,
    principal: Principal,
    *,
    plan_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionPlan:
    _permit(principal, PERMISSION_PRODUCTION_PLAN_MANAGE)
    organization_id = _org(principal)
    plan = _lock_plan(session, plan_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session,
        organization_id,
        idempotency_key,
        COMMAND_SCHEDULE_PLAN,
        {"public_code": plan.public_code},
    )
    if replay is not None:
        return plan
    if plan.status != PLAN_STATUS_DRAFT:
        raise InvalidStateError("transicao_invalida")
    items = session.scalars(
        select(ProductionPlanItem).where(ProductionPlanItem.production_plan_id == plan.id)
    ).all()
    if not items:
        raise ValidationError("plano sem itens")
    plan.status = PLAN_STATUS_SCHEDULED
    plan.scheduled_at = _now()
    _bump(plan)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=plan.establishment_id,
        event_type=EVENT_PLAN_SCHEDULED,
        command=COMMAND_SCHEDULE_PLAN,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"public_code": plan.public_code},
        plan_id=plan.id,
    )
    return plan


def create_order(
    session: Session,
    principal: Principal,
    *,
    establishment_id: UUID,
    technical_product_id: UUID,
    target_mode: str,
    target_quantity: Decimal | int | str,
    idempotency_key: UUID,
    unit_weight_g: Decimal | int | str | None = None,
    plan_id: UUID | None = None,
    plan_item_id: UUID | None = None,
    formulation_version_id: UUID | None = None,
    scale_calculation_id: UUID | None = None,
    priority: int = 50,
    planned_start_at: datetime | None = None,
    planned_end_at: datetime | None = None,
    superseded_order_id: UUID | None = None,
    emit_event: bool = True,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = _org(principal)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_CREATE_ORDER
    ) if emit_event else None
    if replay is not None and replay.order_id is not None:
        found = session.get(ProductionOrder, replay.order_id)
        if found is not None:
            return found
    establishment = session.get(Establishment, establishment_id)
    if establishment is None or establishment.organization_id != organization_id:
        raise ValidationError("estabelecimento inválido")
    mode, amount, weight = _target(target_mode, target_quantity, unit_weight_g)
    plan = None
    if plan_id is not None:
        plan = session.get(ProductionPlan, plan_id)
        if plan is None or plan.organization_id != organization_id:
            raise ValidationError("plano inválido")
        if plan.establishment_id != establishment_id:
            raise ValidationError("plano de outro estabelecimento")
    if plan_item_id is not None:
        item = session.get(ProductionPlanItem, plan_item_id)
        if item is None or item.organization_id != organization_id:
            raise ValidationError("item de plano inválido")
        if plan is None or item.production_plan_id != plan.id:
            raise ValidationError("item não pertence ao plano")
        if item.technical_product_id != technical_product_id:
            raise ValidationError("produto diverge do item")
    day = planned_start_at.date() if planned_start_at is not None else date.today()
    if plan is not None:
        day = plan.operational_date
    code = next_public_code(session, organization_id, CODE_KIND_ORDER, day)
    order = ProductionOrder(
        organization_id=organization_id,
        establishment_id=establishment_id,
        public_code=code,
        plan_id=plan_id,
        plan_item_id=plan_item_id,
        technical_product_id=technical_product_id,
        formulation_version_id=formulation_version_id,
        scale_calculation_id=scale_calculation_id,
        target_mode=mode,
        target_quantity=amount,
        unit_weight_g=weight,
        priority=priority,
        planned_start_at=planned_start_at,
        planned_end_at=planned_end_at,
        status=ORDER_STATUS_DRAFT,
        created_by_user_id=principal.user_id,
        superseded_order_id=superseded_order_id,
    )
    session.add(order)
    session.flush()
    if emit_event:
        append_event(
            session,
            organization_id=organization_id,
            establishment_id=establishment_id,
            event_type=EVENT_ORDER_CREATED,
            command=COMMAND_CREATE_ORDER,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            payload={
                "public_code": code,
                "technical_product_id": str(technical_product_id),
                "target_mode": mode,
            },
            plan_id=plan_id,
            order_id=order.id,
        )
    return order


def schedule_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
    formulation_version_id: UUID | None = None,
    scale_calculation_id: UUID | None = None,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = _org(principal)
    order = _lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session,
        organization_id,
        idempotency_key,
        COMMAND_SCHEDULE_ORDER,
        {"public_code": order.public_code} if order.status == ORDER_STATUS_SCHEDULED else None,
    )
    if replay is not None:
        return order
    if order.status != ORDER_STATUS_DRAFT:
        raise InvalidStateError("transicao_invalida")
    if formulation_version_id is not None:
        order.formulation_version_id = formulation_version_id
    if scale_calculation_id is not None:
        order.scale_calculation_id = scale_calculation_id
    if order.formulation_version_id is None:
        raise ValidationError("formulação obrigatória para programar")
    order.status = ORDER_STATUS_SCHEDULED
    order.scheduled_at = _now()
    order.scheduled_by_user_id = principal.user_id
    _bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_SCHEDULED,
        command=COMMAND_SCHEDULE_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"public_code": order.public_code},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def add_dependency(
    session: Session,
    principal: Principal,
    *,
    dependent_order_id: UUID,
    predecessor_order_id: UUID,
    dependency_type: str,
    idempotency_key: UUID,
    relation_note: str | None = None,
    quantity: Decimal | int | str | None = None,
) -> ProductionOrderDependency:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = _org(principal)
    dependent = session.get(ProductionOrder, dependent_order_id)
    predecessor = session.get(ProductionOrder, predecessor_order_id)
    if dependent is None or predecessor is None:
        raise ValidationError("ordem inválida")
    if (
        dependent.organization_id != organization_id
        or predecessor.organization_id != organization_id
    ):
        raise ValidationError("dependencia_entre_organizacoes")
    if dependent.status not in ORDER_EDITABLE:
        raise ImmutableError("dependencia imutável após liberação")
    if dependency_type not in DEPENDENCY_TYPES:
        raise ValidationError("tipo de dependência inválido")
    assert_same_org_pair(dependent, predecessor)
    assert_acyclic(session, dependent.id, predecessor.id)
    amount = None
    if quantity is not None:
        amount = require_positive(as_decimal(quantity, "quantidade"), "quantidade")
    row = ProductionOrderDependency(
        organization_id=organization_id,
        dependent_order_id=dependent.id,
        predecessor_order_id=predecessor.id,
        dependency_type=dependency_type,
        relation_note=relation_note,
        quantity=amount,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=dependent.establishment_id,
        event_type=EVENT_DEPENDENCY_ADDED,
        command=COMMAND_ADD_DEPENDENCY,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "dependency_id": str(row.id),
            "predecessor_order_id": str(predecessor.id),
            "dependency_type": dependency_type,
        },
        order_id=dependent.id,
    )
    return row


def split_batches(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    count: int,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> list[ProductionBatch]:
    _permit(principal, PERMISSION_PRODUCTION_BATCH_MANAGE)
    organization_id = _org(principal)
    order = _lock_order(session, order_id, organization_id, expected_row_version)
    if order.status not in ORDER_EDITABLE:
        raise ImmutableError("bateladas imutáveis após liberação")
    existing = session.scalars(
        select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
    ).all()
    for row in existing:
        session.delete(row)
    session.flush()
    integer = order.target_mode == TARGET_MODE_UNITS
    parts = split_target(order.target_quantity, count, integer_units=integer)
    memory = split_memory(count, order.target_quantity, order.target_mode)
    created: list[ProductionBatch] = []
    for index, (quantity, factor, remainder) in enumerate(parts, start=1):
        batch = ProductionBatch(
            organization_id=organization_id,
            production_order_id=order.id,
            sequence=index,
            operational_code=f"{order.public_code}-B{index:02d}",
            target_mode=order.target_mode,
            target_quantity=quantity,
            split_factor=factor,
            remainder_applied=remainder,
            split_memory=memory,
            planned_start_at=order.planned_start_at,
            planned_end_at=order.planned_end_at,
            status=BATCH_STATUS_PENDING,
        )
        session.add(batch)
        created.append(batch)
    session.flush()
    if sum((batch.target_quantity for batch in created), Decimal("0")) != order.target_quantity:
        raise ValidationError("soma das bateladas diverge do alvo")
    _bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_BATCH_SPLIT,
        command=COMMAND_SPLIT_BATCHES,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"batch_count": count, "method": SPLIT_METHOD},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return created


def release_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_RELEASE)
    organization_id = _org(principal)
    order = _lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_RELEASE_ORDER
    )
    if replay is not None:
        return order
    if order.status == ORDER_STATUS_RELEASED:
        raise InvalidStateError("ordem já liberada")
    if order.status != ORDER_STATUS_SCHEDULED:
        raise InvalidStateError("transicao_invalida")
    _assert_release_ready(session, order)
    from app.modules.production_execution.policy import freeze_policy_for_release

    policy_hash = freeze_policy_for_release(session, order, principal)
    materials_hash, steps_hash, snapshot_hash = build_release_snapshots(session, order)
    order.status = ORDER_STATUS_RELEASED
    order.released_at = _now()
    order.released_by_user_id = principal.user_id
    order.materials_hash = materials_hash
    order.steps_hash = steps_hash
    order.snapshot_hash = snapshot_hash
    _bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_RELEASED,
        command=COMMAND_RELEASE_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "public_code": order.public_code,
            "materials_hash": materials_hash,
            "steps_hash": steps_hash,
            "snapshot_hash": snapshot_hash,
            "policy_hash": policy_hash,
        },
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def hold_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = _org(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    order = _lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_HOLD_ORDER, {"reason": reason.strip()}
    )
    if replay is not None:
        return order
    if order.status not in {
        ORDER_STATUS_RELEASED,
        ORDER_STATUS_IN_WEIGHING,
        ORDER_STATUS_READY,
        ORDER_STATUS_IN_PROGRESS,
    }:
        raise InvalidStateError("transicao_invalida")
    order.held_from_status = order.status
    order.status = ORDER_STATUS_ON_HOLD
    order.held_at = _now()
    order.hold_reason = reason.strip()
    _bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_HELD,
        command=COMMAND_HOLD_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"reason": reason.strip()},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def cancel_order(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    reason: str,
    idempotency_key: UUID,
    expected_row_version: int | None = None,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_CANCEL)
    organization_id = _org(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    order = _lock_order(session, order_id, organization_id, expected_row_version)
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_CANCEL_ORDER, {"reason": reason.strip()}
    )
    if replay is not None:
        return order
    if order.status not in {
        ORDER_STATUS_DRAFT,
        ORDER_STATUS_SCHEDULED,
        ORDER_STATUS_RELEASED,
        ORDER_STATUS_ON_HOLD,
    }:
        raise InvalidStateError("transicao_invalida")
    from app.modules.production_execution.guards import assert_cancel_allowed

    assert_cancel_allowed(session, order)
    order.status = ORDER_STATUS_CANCELLED
    order.cancelled_at = _now()
    order.cancelled_by_user_id = principal.user_id
    order.cancel_reason = reason.strip()
    _bump(order)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_ORDER_CANCELLED,
        command=COMMAND_CANCEL_ORDER,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"reason": reason.strip()},
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return order


def create_substitute_order(
    session: Session,
    principal: Principal,
    *,
    cancelled_order_id: UUID,
    idempotency_key: UUID,
) -> ProductionOrder:
    _permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = _org(principal)
    original = session.get(ProductionOrder, cancelled_order_id)
    if original is None or original.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if original.status != ORDER_STATUS_CANCELLED:
        raise InvalidStateError("substituta exige ordem cancelada")
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_CREATE_SUBSTITUTE
    )
    if replay is not None and original.successor_order_id is not None:
        found = session.get(ProductionOrder, original.successor_order_id)
        if found is not None:
            return found
    substitute = create_order(
        session,
        principal,
        establishment_id=original.establishment_id,
        technical_product_id=original.technical_product_id,
        target_mode=original.target_mode,
        target_quantity=original.target_quantity,
        unit_weight_g=original.unit_weight_g,
        plan_id=original.plan_id,
        plan_item_id=None,
        formulation_version_id=original.formulation_version_id,
        scale_calculation_id=original.scale_calculation_id,
        priority=original.priority,
        planned_start_at=original.planned_start_at,
        planned_end_at=original.planned_end_at,
        superseded_order_id=original.id,
        idempotency_key=idempotency_key,
        emit_event=False,
    )
    original.successor_order_id = substitute.id
    _bump(original)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=original.establishment_id,
        event_type=EVENT_ORDER_SUBSTITUTED,
        command=COMMAND_CREATE_SUBSTITUTE,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={"substitute_order_id": str(substitute.id), "public_code": substitute.public_code},
        plan_id=original.plan_id,
        order_id=original.id,
    )
    return substitute


def _lock_plan(
    session: Session, plan_id: UUID, organization_id: UUID, expected_row_version: int | None
) -> ProductionPlan:
    plan = session.scalar(
        select(ProductionPlan).where(ProductionPlan.id == plan_id).with_for_update()
    )
    if plan is None or plan.organization_id != organization_id:
        raise ValidationError("plano inválido")
    if expected_row_version is not None and plan.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    return plan


def _lock_order(
    session: Session, order_id: UUID, organization_id: UUID, expected_row_version: int | None
) -> ProductionOrder:
    order = session.scalar(
        select(ProductionOrder).where(ProductionOrder.id == order_id).with_for_update()
    )
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if expected_row_version is not None and order.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    return order


def _plan_item_has_released_order(session: Session, item_id: UUID | None) -> bool:
    if item_id is None:
        return False
    return (
        session.scalar(
            select(ProductionOrder.id).where(
                ProductionOrder.plan_item_id == item_id,
                ProductionOrder.status == ORDER_STATUS_RELEASED,
            )
        )
        is not None
    )


def _assert_release_ready(session: Session, order: ProductionOrder) -> None:
    if order.formulation_version_id is None or order.scale_calculation_id is None:
        raise ValidationError("formulação e escala obrigatórias")
    version = session.get(FormulationVersion, order.formulation_version_id)
    scale = session.get(ScaleCalculation, order.scale_calculation_id)
    if version is None or scale is None:
        raise ValidationError("formulação ou escala inexistente")
    if (
        version.organization_id != order.organization_id
        or scale.organization_id != order.organization_id
    ):
        raise ValidationError("formulação ou escala de outra organização")
    formulation = session.get(Formulation, version.formulation_id)
    if formulation is None or formulation.technical_product_id != order.technical_product_id:
        raise ValidationError("produto, formulação e escala incompatíveis")
    if scale.formulation_version_id != version.id:
        raise ValidationError("produto, formulação e escala incompatíveis")
    if not has_valid_approval(session, version.id):
        raise ValidationError("formulacao_sem_aprovacao")
    if order.target_mode == TARGET_MODE_MASS:
        if scale.calculation_mode != MODE_TOTAL_DOUGH_MASS:
            raise ValidationError("produto, formulação e escala incompatíveis")
        if scale.input_target_total_dough_mass != order.target_quantity:
            raise ValidationError("produto, formulação e escala incompatíveis")
    elif order.target_mode == TARGET_MODE_UNITS:
        if scale.calculation_mode != MODE_FINAL_UNITS:
            raise ValidationError("produto, formulação e escala incompatíveis")
        if scale.input_unit_count != int(order.target_quantity):
            raise ValidationError("produto, formulação e escala incompatíveis")
    batches = session.scalars(
        select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
    ).all()
    if not batches:
        raise ValidationError("ordem sem batelada")
    if sum((batch.target_quantity for batch in batches), Decimal("0")) != order.target_quantity:
        raise ValidationError("soma das bateladas diverge do alvo")
    deps = session.scalars(
        select(ProductionOrderDependency).where(
            ProductionOrderDependency.dependent_order_id == order.id
        )
    )
    for dep in deps:
        assert_acyclic(session, dep.dependent_order_id, dep.predecessor_order_id)
