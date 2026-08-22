from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE,
    Principal,
)
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_OVERRIDE_DEPENDENCY,
    EVENT_DEPENDENCY_OVERRIDDEN,
)
from app.modules.production_execution.models import ProductionDependencyOverride
from app.modules.production_planning.constants import (
    DEPENDENCY_INTERMEDIATE,
    DEPENDENCY_PREFERMENT,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_SHORT_CLOSED,
)
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import ProductionOrder, ProductionOrderDependency


def _override_for(session: Session, dependency_id: UUID) -> ProductionDependencyOverride | None:
    return session.scalar(
        select(ProductionDependencyOverride).where(
            ProductionDependencyOverride.dependency_id == dependency_id
        )
    )


def assert_execution_dependencies(session: Session, order: ProductionOrder) -> None:
    deps = list(
        session.scalars(
            select(ProductionOrderDependency).where(
                ProductionOrderDependency.dependent_order_id == order.id
            )
        )
    )
    for dep in deps:
        if dep.dependency_type not in {DEPENDENCY_PREFERMENT, DEPENDENCY_INTERMEDIATE}:
            predecessor = session.get(ProductionOrder, dep.predecessor_order_id)
            if predecessor is not None and predecessor.status == ORDER_STATUS_CANCELLED:
                raise InvalidStateError("dependencia_cancelada")
            continue
        predecessor = session.get(ProductionOrder, dep.predecessor_order_id)
        if predecessor is None:
            raise ValidationError("predecessor inválido")
        if predecessor.status == ORDER_STATUS_CANCELLED:
            raise InvalidStateError("dependencia_cancelada")
        if predecessor.status == ORDER_STATUS_COMPLETED:
            continue
        if predecessor.status == ORDER_STATUS_SHORT_CLOSED:
            if _override_for(session, dep.id) is None:
                raise InvalidStateError("dependencia_encerrada")
            continue
        raise InvalidStateError("dependencia_pendente")


def override_dependency(
    session: Session,
    principal: Principal,
    *,
    dependency_id: UUID,
    reason: str,
    idempotency_key: UUID,
) -> ProductionDependencyOverride:
    permit(principal, PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE)
    organization_id = org_id(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_OVERRIDE_DEPENDENCY
    )
    if replay is not None:
        found = session.scalar(
            select(ProductionDependencyOverride).where(
                ProductionDependencyOverride.organization_id == organization_id,
                ProductionDependencyOverride.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    dep = session.get(ProductionOrderDependency, dependency_id)
    if dep is None or dep.organization_id != organization_id:
        raise ValidationError("dependência inválida")
    predecessor = session.get(ProductionOrder, dep.predecessor_order_id)
    if predecessor is None:
        raise ValidationError("predecessor inválido")
    if predecessor.status != ORDER_STATUS_SHORT_CLOSED:
        raise InvalidStateError("override exige predecessor encerrado")
    dependent = session.get(ProductionOrder, dep.dependent_order_id)
    assert dependent is not None
    row = ProductionDependencyOverride(
        organization_id=organization_id,
        dependency_id=dep.id,
        predecessor_status=predecessor.status,
        reason=reason.strip(),
        actor_user_id=principal.user_id,
        occurred_at=now(),
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=dependent.establishment_id,
        event_type=EVENT_DEPENDENCY_OVERRIDDEN,
        command=COMMAND_OVERRIDE_DEPENDENCY,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "dependency_id": str(dep.id),
            "predecessor_status": predecessor.status,
            "reason": reason.strip(),
        },
        plan_id=dependent.plan_id,
        order_id=dependent.id,
    )
    return row
