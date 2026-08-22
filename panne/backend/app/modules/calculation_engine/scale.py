"""Motor determinístico de escala. Fora da camada HTTP. Sem IA."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import (
    DEFAULT_PRESENTATION_PLACES,
    ROUNDING_MODE_NAME,
    quantize_factor,
    quantize_percent,
    quantize_quantity,
)
from app.modules.formula_lab.models import (
    FormulationItem,
    FormulationVersion,
    ScaleCalculation,
    ScaleCalculationItem,
)
from app.modules.formula_lab.rules import bakers_percentages, derived_gross_quantity

ALGORITHM_CODE = "deterministic_scale"
ALGORITHM_VERSION = "1"
MODE_TOTAL_DOUGH_MASS = "total_dough_mass"
MODE_FINAL_UNITS = "final_units"


class ScaleError(ValueError):
    """Entrada inválida para escala."""


@dataclass(frozen=True)
class ScaleItemResult:
    formulation_item_id: UUID
    ingredient_version_id: UUID
    sequence: int
    measurement_unit_id: UUID
    base_net_quantity: Decimal
    base_correction_factor: Decimal
    scaled_net_quantity: Decimal
    scaled_gross_quantity: Decimal
    bakers_percentage: Decimal | None


@dataclass(frozen=True)
class ScaleResult:
    calculation_mode: str
    input_target_total_dough_mass: Decimal | None
    input_unit_count: int | None
    input_final_unit_weight_g: Decimal | None
    input_bake_loss_rate: Decimal | None
    base_total_net_mass: Decimal
    scale_factor: Decimal
    required_pre_bake_mass: Decimal
    items: tuple[ScaleItemResult, ...]


def _as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise ScaleError("float binário rejeitado")
    return Decimal(value)


def _require_positive_mass(value: Decimal, label: str) -> Decimal:
    amount = _as_decimal(value)
    if amount <= 0:
        raise ScaleError(f"{label} deve ser positivo")
    return amount


def _require_loss_rate(value: Decimal) -> Decimal:
    rate = _as_decimal(value)
    if rate < 0 or rate >= 1:
        raise ScaleError("taxa de perda deve estar entre 0 e menor que 1")
    return rate


def base_total_net_mass(items: Sequence[FormulationItem]) -> Decimal:
    if not items:
        raise ScaleError("formulação sem itens não pode ser escalada")
    total = sum((item.net_quantity for item in items), Decimal("0"))
    if total <= 0:
        raise ScaleError("massa-base líquida deve ser positiva")
    return total


def scale_factor_for_total_mass(target_total_dough_mass: Decimal, base_mass: Decimal) -> Decimal:
    target = _require_positive_mass(target_total_dough_mass, "massa total")
    if base_mass <= 0:
        raise ScaleError("divisão por zero impossível: massa-base inválida")
    return target / base_mass


def required_pre_bake_mass(
    unit_count: int,
    final_unit_weight: Decimal,
    bake_loss_rate: Decimal,
) -> Decimal:
    if not isinstance(unit_count, int) or isinstance(unit_count, bool) or unit_count <= 0:
        raise ScaleError("quantidade de unidades deve ser inteira e positiva")
    weight = _require_positive_mass(final_unit_weight, "peso final unitário")
    rate = _require_loss_rate(bake_loss_rate)
    denominator = Decimal("1") - rate
    if denominator <= 0:
        raise ScaleError("divisão por zero impossível: perda inválida")
    return (_as_decimal(unit_count) * weight) / denominator


def scale_items(
    items: Sequence[FormulationItem],
    factor: Decimal,
) -> tuple[ScaleItemResult, ...]:
    if factor <= 0:
        raise ScaleError("fator de escala deve ser positivo")
    percents = bakers_percentages(items)
    scaled: list[ScaleItemResult] = []
    for item in sorted(items, key=lambda row: row.sequence):
        net = item.net_quantity * factor
        gross = derived_gross_quantity(net, item.correction_factor)
        percent = percents[item.id] if percents is not None else None
        scaled.append(
            ScaleItemResult(
                formulation_item_id=item.id,
                ingredient_version_id=item.ingredient_version_id,
                sequence=item.sequence,
                measurement_unit_id=item.measurement_unit_id,
                base_net_quantity=item.net_quantity,
                base_correction_factor=item.correction_factor,
                scaled_net_quantity=quantize_quantity(net),
                scaled_gross_quantity=gross,
                bakers_percentage=quantize_percent(percent) if percent is not None else None,
            )
        )
    return tuple(scaled)


def calculate_total_dough_mass(
    items: Sequence[FormulationItem],
    target_total_dough_mass: Decimal,
) -> ScaleResult:
    base = base_total_net_mass(items)
    target = _require_positive_mass(target_total_dough_mass, "massa total")
    factor = scale_factor_for_total_mass(target, base)
    return ScaleResult(
        calculation_mode=MODE_TOTAL_DOUGH_MASS,
        input_target_total_dough_mass=target,
        input_unit_count=None,
        input_final_unit_weight_g=None,
        input_bake_loss_rate=None,
        base_total_net_mass=quantize_quantity(base),
        scale_factor=quantize_factor(factor),
        required_pre_bake_mass=quantize_quantity(target),
        items=scale_items(items, factor),
    )


def calculate_final_units(
    items: Sequence[FormulationItem],
    unit_count: int,
    final_unit_weight: Decimal,
    bake_loss_rate: Decimal,
) -> ScaleResult:
    base = base_total_net_mass(items)
    pre_bake = required_pre_bake_mass(unit_count, final_unit_weight, bake_loss_rate)
    factor = pre_bake / base
    return ScaleResult(
        calculation_mode=MODE_FINAL_UNITS,
        input_target_total_dough_mass=None,
        input_unit_count=unit_count,
        input_final_unit_weight_g=_as_decimal(final_unit_weight),
        input_bake_loss_rate=_as_decimal(bake_loss_rate),
        base_total_net_mass=quantize_quantity(base),
        scale_factor=quantize_factor(factor),
        required_pre_bake_mass=quantize_quantity(pre_bake),
        items=scale_items(items, factor),
    )


def persist_scale_calculation(
    session: Session,
    version: FormulationVersion,
    result: ScaleResult,
    created_by_user_id: UUID | None = None,
    presentation_decimal_places: int = DEFAULT_PRESENTATION_PLACES,
) -> ScaleCalculation:
    if presentation_decimal_places < 0:
        raise ScaleError("casas decimais de apresentação inválidas")
    row = ScaleCalculation(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        calculation_mode=result.calculation_mode,
        input_target_total_dough_mass=result.input_target_total_dough_mass,
        input_unit_count=result.input_unit_count,
        input_final_unit_weight_g=result.input_final_unit_weight_g,
        input_bake_loss_rate=result.input_bake_loss_rate,
        base_total_net_mass=result.base_total_net_mass,
        scale_factor=result.scale_factor,
        required_pre_bake_mass=result.required_pre_bake_mass,
        algorithm_code=ALGORITHM_CODE,
        algorithm_version=ALGORITHM_VERSION,
        rounding_mode=ROUNDING_MODE_NAME,
        presentation_decimal_places=presentation_decimal_places,
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    session.flush()
    for item in result.items:
        session.add(
            ScaleCalculationItem(
                organization_id=version.organization_id,
                scale_calculation_id=row.id,
                formulation_item_id=item.formulation_item_id,
                ingredient_version_id=item.ingredient_version_id,
                sequence=item.sequence,
                scaled_net_quantity=item.scaled_net_quantity,
                scaled_gross_quantity=item.scaled_gross_quantity,
                bakers_percentage=item.bakers_percentage,
                measurement_unit_id=item.measurement_unit_id,
                base_net_quantity=item.base_net_quantity,
                base_correction_factor=item.base_correction_factor,
            )
        )
    session.flush()
    return row


def load_version_items(session: Session, version_id: UUID) -> list[FormulationItem]:
    return list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == version_id)
            .order_by(FormulationItem.sequence)
        )
    )
