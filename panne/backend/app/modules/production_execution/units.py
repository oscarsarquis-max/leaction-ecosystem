"""Conversão reproduzível de massa. Sem float. Massa↔volume é proibida."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_factor, quantize_quantity
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.support import as_decimal, require_positive

CANONICAL_MASS_CODE = "g"
CONVERSION_SOURCE_SI = "measurement_unit.si_factor"
CONVERSION_SOURCE_LEGACY = "legacy_identity"
CONVERSION_VERSION = "1"


@dataclass(frozen=True)
class MassConversion:
    entered_quantity: Decimal
    entered_unit_id: UUID
    entered_unit_code: str
    canonical_quantity: Decimal
    canonical_unit_id: UUID
    canonical_unit_code: str
    factor: Decimal
    source: str
    version: str


def canonical_mass_unit(session: Session) -> MeasurementUnit:
    unit = session.scalar(
        select(MeasurementUnit).where(MeasurementUnit.code == CANONICAL_MASS_CODE)
    )
    if unit is None:
        raise ValidationError("unidade canônica ausente")
    return unit


def convert_to_canonical_mass(
    session: Session,
    quantity: Decimal | int | str,
    measurement_unit_id: UUID,
) -> MassConversion:
    unit = session.get(MeasurementUnit, measurement_unit_id)
    if unit is None:
        raise ValidationError("unidade incompatível")
    if unit.dimension != "mass":
        raise ValidationError("conversao_massa_volume_proibida")
    canonical = canonical_mass_unit(session)
    entered = require_positive(quantize_quantity(as_decimal(quantity, "quantidade")), "quantidade")
    from_si = Decimal(unit.si_factor)
    to_si = Decimal(canonical.si_factor)
    if from_si <= 0 or to_si <= 0:
        raise ValidationError("fator de conversão inválido")
    factor = quantize_factor(from_si / to_si)
    canonical_quantity = quantize_quantity(entered * factor)
    return MassConversion(
        entered_quantity=entered,
        entered_unit_id=unit.id,
        entered_unit_code=unit.code,
        canonical_quantity=canonical_quantity,
        canonical_unit_id=canonical.id,
        canonical_unit_code=canonical.code,
        factor=factor,
        source=CONVERSION_SOURCE_SI,
        version=CONVERSION_VERSION,
    )


def canonical_amount(row) -> Decimal:
    value = getattr(row, "canonical_quantity", None)
    return value if value is not None else row.quantity
