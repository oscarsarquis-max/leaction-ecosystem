from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production_planning.constants import (
    CODE_KIND_ORDER,
    CODE_KIND_PLAN,
    CODE_KIND_SHEET,
)
from app.modules.production_planning.models import ProductionCodeCounter


def next_public_code(session: Session, organization_id: UUID, kind: str, day: date) -> str:
    if kind not in {CODE_KIND_PLAN, CODE_KIND_ORDER, CODE_KIND_SHEET}:
        raise ValueError("tipo de código inválido")
    period = day.strftime("%Y%m%d")
    prefix = {"plan": "PLN", "order": "ORD", "sheet": "FCH"}[kind]
    counter = session.scalar(
        select(ProductionCodeCounter)
        .where(
            ProductionCodeCounter.organization_id == organization_id,
            ProductionCodeCounter.kind == kind,
            ProductionCodeCounter.period == period,
        )
        .with_for_update()
    )
    if counter is None:
        counter = ProductionCodeCounter(
            organization_id=organization_id,
            kind=kind,
            period=period,
            last_value=0,
        )
        session.add(counter)
        session.flush()
        counter = session.scalar(
            select(ProductionCodeCounter)
            .where(ProductionCodeCounter.id == counter.id)
            .with_for_update()
        )
        assert counter is not None
    counter.last_value += 1
    session.flush()
    return f"{prefix}-{period}-{counter.last_value:04d}"
