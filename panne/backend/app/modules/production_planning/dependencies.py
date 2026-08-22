from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production_planning.errors import CycleError, ValidationError
from app.modules.production_planning.models import ProductionOrder, ProductionOrderDependency


def assert_same_org_pair(dependent: ProductionOrder, predecessor: ProductionOrder) -> None:
    if dependent.organization_id != predecessor.organization_id:
        raise ValidationError("dependencia_entre_organizacoes")
    if dependent.id == predecessor.id:
        raise ValidationError("dependencia_autorreferencia")


def would_cycle(session: Session, dependent_id: UUID, predecessor_id: UUID) -> bool:
    seen: set[UUID] = set()
    stack = [predecessor_id]
    while stack:
        current = stack.pop()
        if current == dependent_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        parents = session.scalars(
            select(ProductionOrderDependency.predecessor_order_id).where(
                ProductionOrderDependency.dependent_order_id == current
            )
        )
        stack.extend(parents)
    return False


def assert_acyclic(session: Session, dependent_id: UUID, predecessor_id: UUID) -> None:
    if would_cycle(session, dependent_id, predecessor_id):
        raise CycleError("dependencia_ciclica")
