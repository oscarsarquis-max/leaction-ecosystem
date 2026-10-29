from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_percent, quantize_quantity
from app.modules.production_execution.constants import (
    CONSUMPTION_CONSUME,
    CONSUMPTION_CORRECTION,
    CONSUMPTION_RETURN,
    CONSUMPTION_WASTE,
    ENTRY_CORRECTION,
    ENTRY_RECORD,
    ENTRY_REVERSAL,
    VERIFY_ACCEPTED,
    YIELD_ALGORITHM,
    YIELD_ALGORITHM_VERSION,
    YIELD_GOOD_UNITS,
    YIELD_LEFTOVER,
    YIELD_POST_BAKE_MASS,
    YIELD_PRE_BAKE_MASS,
    YIELD_REJECTED_UNITS,
    YIELD_SCRAP,
)
from app.modules.production_execution.models import (
    ProductionMaterialConsumption,
    ProductionWeighingEntry,
    ProductionWeighingVerification,
    ProductionYieldMeasurement,
)
from app.modules.production_execution.units import canonical_amount
from app.modules.production_planning.constants import TARGET_MODE_MASS, TARGET_MODE_UNITS
from app.modules.production_planning.models import ProductionBatch
from app.modules.production_planning.support import digest


def effective_weighed_quantity(
    session: Session, batch_material_id: UUID
) -> Decimal:
    entries = list(
        session.scalars(
            select(ProductionWeighingEntry).where(
                ProductionWeighingEntry.production_batch_material_id == batch_material_id
            )
        )
    )
    voided = {
        row.original_entry_id
        for row in entries
        if row.entry_type in {ENTRY_REVERSAL, ENTRY_CORRECTION} and row.original_entry_id
    }
    total = Decimal("0")
    for row in entries:
        if row.id in voided:
            continue
        if row.entry_type in {ENTRY_RECORD, ENTRY_CORRECTION}:
            total += canonical_amount(row)
    return quantize_quantity(total)


def latest_verification(
    session: Session, entry_id: UUID
) -> ProductionWeighingVerification | None:
    rows = list(
        session.scalars(
            select(ProductionWeighingVerification)
            .where(ProductionWeighingVerification.entry_id == entry_id)
            .order_by(ProductionWeighingVerification.occurred_at.desc())
        )
    )
    return rows[0] if rows else None


def current_weighing_entries(
    session: Session, batch_material_id: UUID
) -> list[ProductionWeighingEntry]:
    entries = list(
        session.scalars(
            select(ProductionWeighingEntry).where(
                ProductionWeighingEntry.production_batch_material_id == batch_material_id
            )
        )
    )
    voided = {
        row.original_entry_id
        for row in entries
        if row.entry_type in {ENTRY_REVERSAL, ENTRY_CORRECTION} and row.original_entry_id
    }
    return [
        row
        for row in entries
        if row.id not in voided and row.entry_type in {ENTRY_RECORD, ENTRY_CORRECTION}
    ]


def material_accepted(session: Session, batch_material_id: UUID) -> bool:
    current = current_weighing_entries(session, batch_material_id)
    if not current:
        return False
    for entry in current:
        verification = latest_verification(session, entry.id)
        if verification is None or verification.decision != VERIFY_ACCEPTED:
            return False
    return True


def project_consumption(session: Session, batch_material_id: UUID) -> dict[str, Decimal]:
    rows = list(
        session.scalars(
            select(ProductionMaterialConsumption).where(
                ProductionMaterialConsumption.production_batch_material_id == batch_material_id
            )
        )
    )
    voided = {row.corrects_id for row in rows if row.corrects_id}
    consumed = Decimal("0")
    returned = Decimal("0")
    wasted = Decimal("0")
    for row in rows:
        if row.id in voided:
            continue
        if row.consumption_type == CONSUMPTION_CONSUME:
            consumed += canonical_amount(row)
        elif row.consumption_type == CONSUMPTION_RETURN:
            returned += canonical_amount(row)
        elif row.consumption_type == CONSUMPTION_WASTE:
            wasted += canonical_amount(row)
        elif row.consumption_type == CONSUMPTION_CORRECTION:
            consumed += canonical_amount(row)
    return {
        "consume": quantize_quantity(consumed),
        "return": quantize_quantity(returned),
        "waste": quantize_quantity(wasted),
        "net": quantize_quantity(consumed - returned),
    }


@dataclass(frozen=True)
class YieldProjection:
    final_mass: Decimal | None
    sellable_units: Decimal | None
    rejected_units: Decimal | None
    leftover: Decimal | None
    scrap: Decimal | None
    loss_absolute: Decimal | None
    loss_percent: Decimal | None
    target_deviation: Decimal | None
    completeness: str
    algorithm_code: str
    algorithm_version: str

    def digest(self) -> str:
        return digest(
            {
                "final_mass": None if self.final_mass is None else format(self.final_mass, "f"),
                "sellable_units": (
                    None if self.sellable_units is None else format(self.sellable_units, "f")
                ),
                "loss_absolute": (
                    None if self.loss_absolute is None else format(self.loss_absolute, "f")
                ),
                "loss_percent": (
                    None if self.loss_percent is None else format(self.loss_percent, "f")
                ),
                "target_deviation": (
                    None if self.target_deviation is None else format(self.target_deviation, "f")
                ),
                "completeness": self.completeness,
                "algorithm_code": self.algorithm_code,
                "algorithm_version": self.algorithm_version,
            }
        )


def _net_yield(session: Session, batch_id: UUID, measurement_type: str) -> Decimal:
    rows = list(
        session.scalars(
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.production_batch_id == batch_id,
                ProductionYieldMeasurement.measurement_type == measurement_type,
            )
        )
    )
    voided = {row.reverses_id for row in rows if row.reverses_id}
    total = Decimal("0")
    for row in rows:
        if row.id in voided or row.reverses_id is not None:
            continue
        total += row.quantity
    return quantize_quantity(total)


def project_yield(session: Session, batch: ProductionBatch) -> YieldProjection:
    pre = _net_yield(session, batch.id, YIELD_PRE_BAKE_MASS)
    post = _net_yield(session, batch.id, YIELD_POST_BAKE_MASS)
    good = _net_yield(session, batch.id, YIELD_GOOD_UNITS)
    rejected = _net_yield(session, batch.id, YIELD_REJECTED_UNITS)
    leftover = _net_yield(session, batch.id, YIELD_LEFTOVER)
    scrap = _net_yield(session, batch.id, YIELD_SCRAP)
    final_mass = post if post > 0 else (pre if pre > 0 else None)
    sellable = good if good > 0 else None
    loss_abs = None
    loss_pct = None
    if pre > 0 and post > 0:
        loss_abs = quantize_quantity(pre - post)
        loss_pct = quantize_percent((loss_abs / pre) * Decimal("100"))
    actual = None
    if batch.target_mode == TARGET_MODE_MASS:
        actual = final_mass
        complete = final_mass is not None
    elif batch.target_mode == TARGET_MODE_UNITS:
        actual = sellable
        complete = sellable is not None
    else:
        complete = False
    deviation = None
    if actual is not None:
        deviation = quantize_quantity(actual - batch.target_quantity)
    return YieldProjection(
        final_mass=final_mass,
        sellable_units=sellable,
        rejected_units=rejected if rejected > 0 else None,
        leftover=leftover if leftover > 0 else None,
        scrap=scrap if scrap > 0 else None,
        loss_absolute=loss_abs,
        loss_percent=loss_pct,
        target_deviation=deviation,
        completeness="complete" if complete else "incomplete",
        algorithm_code=YIELD_ALGORITHM,
        algorithm_version=YIELD_ALGORITHM_VERSION,
    )


def within_completion_tolerance(
    projection: YieldProjection, target: Decimal, tolerance_percent: Decimal
) -> bool:
    if projection.completeness != "complete" or projection.target_deviation is None:
        return False
    if target <= 0:
        return False
    deviation_pct = quantize_percent(
        (abs(projection.target_deviation) / target) * Decimal("100")
    )
    return deviation_pct <= tolerance_percent
