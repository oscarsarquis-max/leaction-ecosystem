"""Projeção do quadro. Sem tabela paralela e sem custos."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import TechnicalProduct
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_BOARD_READ,
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT,
    PERMISSION_PRODUCTION_ORDER_RELEASE,
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    Principal,
    require_permission,
)
from app.modules.production_execution.constants import OCCURRENCE_OPEN, STEP_IN_PROGRESS
from app.modules.production_execution.guards import has_execution_facts
from app.modules.production_execution.models import (
    ProductionExecutionPolicy,
    ProductionOccurrence,
    ProductionStepExecution,
)
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.serialize import batch_out, decimal_str, iso
from app.modules.production_planning.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_READY,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SCHEDULED,
    ORDER_STATUS_SHORT_CLOSED,
)
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionOrder,
    ProductionOrderDependency,
    ProductionOrderStep,
    ProductionPlan,
)

_TERMINAL = {
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_SHORT_CLOSED,
    ORDER_STATUS_CANCELLED,
}
_MAX_RANGE_DAYS = 7


def _next_action(order: ProductionOrder, principal: Principal, policy_missing: bool) -> str | None:
    perms = principal.permissions
    if order.status == ORDER_STATUS_DRAFT and PERMISSION_PRODUCTION_ORDER_MANAGE in perms:
        return "schedule_order"
    if order.status == ORDER_STATUS_SCHEDULED and PERMISSION_PRODUCTION_ORDER_RELEASE in perms:
        return "release_order"
    if (
        order.status in {ORDER_STATUS_RELEASED, ORDER_STATUS_ON_HOLD}
        and policy_missing
        and PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT in perms
    ):
        return "adopt_execution_policy"
    if order.status == ORDER_STATUS_RELEASED and PERMISSION_PRODUCTION_WEIGHING_RECORD in perms:
        return "open_weighing_session"
    if order.status == ORDER_STATUS_IN_WEIGHING and PERMISSION_PRODUCTION_WEIGHING_RECORD in perms:
        return "record_weighing"
    if order.status == ORDER_STATUS_READY and PERMISSION_PRODUCTION_STEP_EXECUTE in perms:
        return "start_step"
    if order.status == ORDER_STATUS_IN_PROGRESS and PERMISSION_PRODUCTION_STEP_EXECUTE in perms:
        return "complete_step"
    if order.status == ORDER_STATUS_ON_HOLD and PERMISSION_PRODUCTION_ORDER_MANAGE in perms:
        return "resume_order"
    return None


def project_board(
    session: Session,
    principal: Principal,
    organization_id: UUID,
    *,
    operational_date=None,
    date_from=None,
    date_to=None,
    establishment_id: UUID | None = None,
    shift: str | None = None,
    area: str | None = None,
    product_id: UUID | None = None,
    status: str | None = None,
    priority: int | None = None,
    q: str | None = None,
) -> list[dict]:
    try:
        require_permission(principal, PERMISSION_PRODUCTION_BOARD_READ)
    except Exception as exc:
        raise_domain(exc)
    if q is not None and len(q) > 64:
        raise_domain(ValidationError("contrato_invalido"))
    if date_from and date_to and (date_to - date_from).days > _MAX_RANGE_DAYS:
        raise_domain(ValidationError("intervalo de datas excede 7 dias"))
    query = (
        select(ProductionOrder, ProductionPlan, TechnicalProduct)
        .outerjoin(ProductionPlan, ProductionPlan.id == ProductionOrder.plan_id)
        .join(TechnicalProduct, TechnicalProduct.id == ProductionOrder.technical_product_id)
        .where(ProductionOrder.organization_id == organization_id)
    )
    if establishment_id is not None:
        query = query.where(ProductionOrder.establishment_id == establishment_id)
    if operational_date is not None:
        query = query.where(ProductionPlan.operational_date == operational_date)
    if date_from is not None:
        query = query.where(ProductionPlan.operational_date >= date_from)
    if date_to is not None:
        query = query.where(ProductionPlan.operational_date <= date_to)
    if shift is not None:
        query = query.where(ProductionPlan.shift == shift)
    if product_id is not None:
        query = query.where(ProductionOrder.technical_product_id == product_id)
    if status is not None:
        query = query.where(ProductionOrder.status == status)
    if priority is not None:
        query = query.where(ProductionOrder.priority == priority)
    if q:
        like = f"%{q}%"
        query = query.where(ProductionOrder.public_code.ilike(like))
    if area:
        query = query.where(ProductionOrder.public_code.ilike(f"%{area}%"))
    rows = list(session.execute(query).all())
    now = datetime.now(UTC)
    cards = []
    for order, plan, product in rows:
        batches = list(
            session.scalars(
                select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
            )
        )
        deps = list(
            session.scalars(
                select(ProductionOrderDependency).where(
                    ProductionOrderDependency.dependent_order_id == order.id
                )
            )
        )
        open_occ = list(
            session.scalars(
                select(ProductionOccurrence).where(
                    ProductionOccurrence.production_order_id == order.id,
                    ProductionOccurrence.status == OCCURRENCE_OPEN,
                )
            )
        )
        current_step = session.scalar(
            select(ProductionStepExecution)
            .where(
                ProductionStepExecution.production_order_id == order.id,
                ProductionStepExecution.status == STEP_IN_PROGRESS,
            )
            .limit(1)
        )
        if current_step is None:
            planned_step = session.scalar(
                select(ProductionOrderStep)
                .where(ProductionOrderStep.production_order_id == order.id)
                .order_by(ProductionOrderStep.sequence)
                .limit(1)
            )
            current_title = planned_step.title if planned_step is not None else None
        else:
            planned = session.get(ProductionOrderStep, current_step.production_order_step_id)
            current_title = planned.title if planned is not None else None
        policy = session.scalar(
            select(ProductionExecutionPolicy).where(
                ProductionExecutionPolicy.production_order_id == order.id
            )
        )
        policy_missing = policy is None or policy.frozen_at is None or not policy.policy_hash
        delayed = (
            order.planned_end_at is not None
            and order.planned_end_at < now
            and order.status not in _TERMINAL
        )
        blocked = any(item.is_blocking for item in open_occ)
        cards.append(
            {
                "order": {
                    "id": str(order.id),
                    "public_code": order.public_code,
                    "status": order.status,
                    "priority": order.priority,
                    "row_version": order.row_version,
                },
                "batches": [batch_out(batch) for batch in batches],
                "product": {
                    "id": str(product.id),
                    "code": product.code,
                    "display_name": product.display_name,
                },
                "quantity": decimal_str(order.target_quantity),
                "target_mode": order.target_mode,
                "planned_start_at": iso(order.planned_start_at),
                "planned_end_at": iso(order.planned_end_at),
                "operational_date": None if plan is None else plan.operational_date.isoformat(),
                "shift": None if plan is None else plan.shift,
                "current_step": current_title,
                "dependencies": [
                    {
                        "id": str(dep.id),
                        "predecessor_order_id": str(dep.predecessor_order_id),
                        "dependency_type": dep.dependency_type,
                    }
                    for dep in deps
                ],
                "blocked": blocked,
                "open_occurrences": len(open_occ),
                "delayed": delayed,
                "next_action": _next_action(order, principal, policy_missing),
                "has_execution_facts": has_execution_facts(session, order),
            }
        )
    return cards
