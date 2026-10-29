from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production_execution.models import (
    ProductionMaterialConsumption,
    ProductionOccurrence,
    ProductionStepExecution,
    ProductionWeighingEntry,
    ProductionWeighingSession,
    ProductionYieldMeasurement,
)
from app.modules.production_planning.errors import InvalidStateError
from app.modules.production_planning.models import ProductionOrder


def has_execution_facts(session: Session, order: ProductionOrder) -> bool:
    if session.scalar(
        select(ProductionWeighingEntry.id)
        .join(
            ProductionWeighingSession,
            ProductionWeighingEntry.session_id == ProductionWeighingSession.id,
        )
        .where(ProductionWeighingSession.production_order_id == order.id)
        .limit(1)
    ):
        return True
    if session.scalar(
        select(ProductionMaterialConsumption.id)
        .where(ProductionMaterialConsumption.production_order_id == order.id)
        .limit(1)
    ):
        return True
    if session.scalar(
        select(ProductionYieldMeasurement.id)
        .where(ProductionYieldMeasurement.production_order_id == order.id)
        .limit(1)
    ):
        return True
    if session.scalar(
        select(ProductionStepExecution.id)
        .where(ProductionStepExecution.production_order_id == order.id)
        .limit(1)
    ):
        return True
    if session.scalar(
        select(ProductionOccurrence.id)
        .where(ProductionOccurrence.production_order_id == order.id)
        .limit(1)
    ):
        return True
    return False


def assert_cancel_allowed(session: Session, order: ProductionOrder) -> None:
    if has_execution_facts(session, order):
        raise InvalidStateError("cancelamento_incompativel")
