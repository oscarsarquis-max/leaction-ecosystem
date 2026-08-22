"""Cálculo nutricional técnico bruto. Fora da API. Sem LLM e sem rótulo."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_quantity
from app.modules.formula_lab.models import FormulationItem, FormulationVersion
from app.modules.ingredient_catalog.models import (
    Ingredient,
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
)
from app.modules.knowledge_grounding.models import (
    NutritionExpectationProfile,
    NutritionExpectationProfileItem,
)
from app.modules.nutrition_calculation.models import (
    CalculationEvidence,
    NutritionCalculation,
    NutritionCalculationItem,
)

ALGORITHM_NAME = "technical_nutrition_raw"
ALGORITHM_VERSION = "1"
ROUNDING_POLICY = "technical_quantize_14_6_half_up_no_regulatory"
BASIS_WHOLE = "whole_formula"
BASIS_PER_100G = "per_100g"
BASIS_PORTION = "technical_portion"
SOURCE_BASIS = "per_100g"

TECHNICAL_DISCLAIMER = (
    "Prévia técnica bruta, não validada regulatoriamente; não é rótulo nem documento conforme."
)
YIELD_ASSUMPTION = (
    "Perda de massa não implica perda automática proporcional de nutrientes; "
    "os totais são preservados e só a concentração muda com a massa final. "
    "Nenhum fator de retenção foi inventado."
)
NO_DERIVED_NUTRIENTS = (
    "Não houve derivação automática de energia, açúcares, gorduras, "
    "carboidratos, sódio, lactose ou glúten."
)


class NutritionError(ValueError):
    """Entrada inválida para o cálculo nutricional técnico."""


@dataclass(frozen=True)
class EvidenceDraft:
    evidence_type: str
    message: str
    status: str
    formulation_item_id: UUID | None = None
    ingredient_version_id: UUID | None = None
    ingredient_nutrient_id: UUID | None = None
    data_source_id: UUID | None = None
    nutrient_definition_id: UUID | None = None
    ingredient_quantity_g: Decimal | None = None
    source_nutrient_value: Decimal | None = None
    source_basis: str | None = None
    contribution_amount: Decimal | None = None


@dataclass
class NutrientAccumulator:
    nutrient: NutrientDefinition
    known_total: Decimal = Decimal("0")
    missing: bool = False
    below_loq: bool = False
    seen: bool = False
    contributions: list[EvidenceDraft] = field(default_factory=list)


@dataclass(frozen=True)
class NutritionResult:
    calculation_basis: str
    formulation_version_status: str
    is_simulation: bool
    formula_net_mass_g: Decimal
    expected_final_mass_g: Decimal | None
    portion_mass_g: Decimal | None
    status: str
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    items: tuple[tuple[NutrientDefinition, Decimal, Decimal | None, Decimal | None, str], ...]
    evidence: tuple[EvidenceDraft, ...]
    expectation_profile_id: UUID | None = None


def _as_decimal(value: Decimal | int | str, label: str) -> Decimal:
    if isinstance(value, float):
        raise NutritionError(f"{label}: float binário rejeitado")
    return Decimal(value)


def _require_mass_unit(unit: MeasurementUnit) -> None:
    if unit.dimension != "mass":
        raise NutritionError("unidade incompatível com massa")


def mass_to_grams(quantity: Decimal, unit: MeasurementUnit) -> Decimal:
    _require_mass_unit(unit)
    if unit.si_factor <= 0:
        raise NutritionError("fator SI inválido")
    kilograms = quantity * unit.si_factor
    return kilograms / Decimal("0.001")


def require_compatible_conversion(from_unit: MeasurementUnit, to_unit: MeasurementUnit) -> None:
    if from_unit.dimension != to_unit.dimension:
        raise NutritionError("unidade incompatível")
    if from_unit.dimension not in {"mass", "energy"}:
        raise NutritionError("conversão não declarada para esta dimensão")


def _loss_rate(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    rate = _as_decimal(value, "taxa de perda")
    if rate < 0 or rate >= 1:
        raise NutritionError("taxa de perda deve estar entre 0 e menor que 1")
    return rate


def resolve_final_mass(
    formula_net_mass_g: Decimal,
    *,
    expected_final_mass_g: Decimal | None,
    bake_loss_rate: Decimal | None,
) -> tuple[Decimal | None, list[str], list[EvidenceDraft]]:
    assumptions: list[str] = []
    evidence: list[EvidenceDraft] = []
    if expected_final_mass_g is not None:
        mass = _as_decimal(expected_final_mass_g, "massa final")
        if mass <= 0:
            raise NutritionError("massa final deve ser positiva")
        assumptions.append("Massa final explícita informada no parâmetro técnico.")
        evidence.append(
            EvidenceDraft(
                evidence_type="yield_assumption",
                status="recorded",
                message=(
                    "Massa final explícita; totais nutricionais não foram reduzidos pela perda."
                ),
            )
        )
        return mass, assumptions, evidence
    rate = _loss_rate(bake_loss_rate)
    if rate is None:
        assumptions.append(
            "Massa final ausente: totais da fórmula existem; "
            "valores por 100 g do produto final incompletos."
        )
        evidence.append(
            EvidenceDraft(
                evidence_type="yield_assumption",
                status="recorded",
                message="Sem massa final válida; prévia por 100 g do produto final não calculada.",
            )
        )
        return None, assumptions, evidence
    final_mass = formula_net_mass_g * (Decimal("1") - rate)
    if final_mass <= 0:
        raise NutritionError("massa final deve ser positiva")
    assumptions.append(YIELD_ASSUMPTION)
    evidence.append(
        EvidenceDraft(
            evidence_type="yield_assumption",
            status="recorded",
            message=YIELD_ASSUMPTION,
            contribution_amount=quantize_quantity(final_mass),
        )
    )
    return quantize_quantity(final_mass), assumptions, evidence


def _load_items(session: Session, version: FormulationVersion) -> list[FormulationItem]:
    items = list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == version.id)
            .order_by(FormulationItem.sequence)
        )
    )
    if not items:
        raise NutritionError("formulação sem itens")
    for item in items:
        if item.organization_id != version.organization_id:
            raise NutritionError("item de outra organização")
    return items


def _completeness(accumulator: NutrientAccumulator) -> str:
    if accumulator.missing:
        return "missing_data"
    if accumulator.below_loq:
        return "below_quantification_limit"
    return "complete"


def _apply_source_value(
    *,
    source: IngredientNutrient,
    accumulator: NutrientAccumulator,
    item_id: UUID,
    version_row: IngredientVersion,
    mass_g: Decimal,
    ingredient_code: str,
) -> tuple[bool, list[EvidenceDraft]]:
    evidence: list[EvidenceDraft] = []
    status = source.value_status or "measured"
    if status == "measured":
        if source.value is None:
            raise NutritionError("valor medido ausente")
        contribution = mass_g * source.value / Decimal("100")
        accumulator.known_total += contribution
        accumulator.seen = True
        evidence.append(
            EvidenceDraft(
                evidence_type="source_value",
                status="recorded",
                formulation_item_id=item_id,
                ingredient_version_id=version_row.id,
                ingredient_nutrient_id=source.id,
                nutrient_definition_id=accumulator.nutrient.id,
                data_source_id=version_row.data_source_id,
                ingredient_quantity_g=quantize_quantity(mass_g),
                source_nutrient_value=source.value,
                source_basis=SOURCE_BASIS,
                contribution_amount=quantize_quantity(contribution),
                message=(
                    "Valor de origem per_100g da IngredientVersion, sem derivação automática."
                ),
            )
        )
        evidence.append(
            EvidenceDraft(
                evidence_type="calculated_contribution",
                status="recorded",
                formulation_item_id=item_id,
                ingredient_version_id=version_row.id,
                ingredient_nutrient_id=source.id,
                nutrient_definition_id=accumulator.nutrient.id,
                data_source_id=version_row.data_source_id,
                ingredient_quantity_g=quantize_quantity(mass_g),
                source_nutrient_value=source.value,
                source_basis=SOURCE_BASIS,
                contribution_amount=quantize_quantity(contribution),
                message="Contribuição = massa líquida (g) × valor per_100g ÷ 100.",
            )
        )
        return False, evidence
    if status == "known_zero":
        accumulator.seen = True
        evidence.append(
            EvidenceDraft(
                evidence_type="source_value",
                status="recorded",
                formulation_item_id=item_id,
                ingredient_version_id=version_row.id,
                ingredient_nutrient_id=source.id,
                nutrient_definition_id=accumulator.nutrient.id,
                data_source_id=version_row.data_source_id,
                ingredient_quantity_g=quantize_quantity(mass_g),
                source_nutrient_value=Decimal("0"),
                source_basis=SOURCE_BASIS,
                contribution_amount=Decimal("0"),
                message="Zero conhecido no dossiê; não é ausência nem limite de quantificação.",
            )
        )
        evidence.append(
            EvidenceDraft(
                evidence_type="calculated_contribution",
                status="recorded",
                formulation_item_id=item_id,
                ingredient_version_id=version_row.id,
                ingredient_nutrient_id=source.id,
                nutrient_definition_id=accumulator.nutrient.id,
                data_source_id=version_row.data_source_id,
                ingredient_quantity_g=quantize_quantity(mass_g),
                source_nutrient_value=Decimal("0"),
                source_basis=SOURCE_BASIS,
                contribution_amount=Decimal("0"),
                message="Contribuição = massa líquida (g) × valor per_100g ÷ 100.",
            )
        )
        return False, evidence
    if status == "below_loq":
        accumulator.seen = True
        accumulator.below_loq = True
        evidence.append(
            EvidenceDraft(
                evidence_type="quantification_limit",
                status="missing",
                formulation_item_id=item_id,
                ingredient_version_id=version_row.id,
                ingredient_nutrient_id=source.id,
                nutrient_definition_id=accumulator.nutrient.id,
                data_source_id=version_row.data_source_id,
                ingredient_quantity_g=quantize_quantity(mass_g),
                source_basis=SOURCE_BASIS,
                message=(
                    f"Nutriente {accumulator.nutrient.code} abaixo do limite de quantificação "
                    f"em {ingredient_code} v{version_row.version_number}; "
                    "LOQ não foi convertido em zero."
                ),
            )
        )
        return True, evidence
    accumulator.seen = True
    accumulator.missing = True
    label = "não detectado" if status == "not_detected" else "desconhecido"
    evidence.append(
        EvidenceDraft(
            evidence_type="missing_value",
            status="missing",
            formulation_item_id=item_id,
            ingredient_version_id=version_row.id,
            ingredient_nutrient_id=source.id,
            nutrient_definition_id=accumulator.nutrient.id,
            data_source_id=version_row.data_source_id,
            ingredient_quantity_g=quantize_quantity(mass_g),
            source_basis=SOURCE_BASIS,
            message=(
                f"Nutriente {accumulator.nutrient.code} {label} em {ingredient_code} "
                f"v{version_row.version_number}; ausência ≠ zero."
            ),
        )
    )
    return True, evidence


def calculate_nutrition(
    session: Session,
    version: FormulationVersion,
    *,
    requested_basis: str = BASIS_WHOLE,
    portion_mass_g: Decimal | None = None,
    expected_final_mass_g: Decimal | None = None,
    bake_loss_rate: Decimal | None = None,
    expectation_profile: NutritionExpectationProfile | None = None,
) -> NutritionResult:
    if requested_basis not in {BASIS_WHOLE, BASIS_PER_100G, BASIS_PORTION}:
        raise NutritionError("base de cálculo inválida")
    items = _load_items(session, version)
    units = {unit.id: unit for unit in session.scalars(select(MeasurementUnit))}
    ingredients = {
        row.id: row
        for row in session.scalars(
            select(Ingredient).where(
                Ingredient.id.in_(
                    select(IngredientVersion.ingredient_id).where(
                        IngredientVersion.id.in_([item.ingredient_version_id for item in items])
                    )
                )
            )
        )
    }
    versions = {
        row.id: row
        for row in session.scalars(
            select(IngredientVersion).where(
                IngredientVersion.id.in_([item.ingredient_version_id for item in items])
            )
        )
    }
    nutrients_by_version: dict[UUID, list[IngredientNutrient]] = {}
    nutrient_ids: set[UUID] = set()
    for row in session.scalars(
        select(IngredientNutrient).where(
            IngredientNutrient.ingredient_version_id.in_(
                [item.ingredient_version_id for item in items]
            )
        )
    ):
        nutrients_by_version.setdefault(row.ingredient_version_id, []).append(row)
        nutrient_ids.add(row.nutrient_id)
    profile_nutrient_ids: list[UUID] = []
    if expectation_profile is not None:
        if (
            expectation_profile.organization_id is not None
            and expectation_profile.organization_id != version.organization_id
        ):
            raise NutritionError("perfil de outra organização")
        profile_nutrient_ids = list(
            session.scalars(
                select(NutritionExpectationProfileItem.nutrient_definition_id)
                .where(NutritionExpectationProfileItem.profile_id == expectation_profile.id)
                .order_by(NutritionExpectationProfileItem.sequence)
            )
        )
        nutrient_ids.update(profile_nutrient_ids)
    definitions = (
        {
            row.id: row
            for row in session.scalars(
                select(NutrientDefinition).where(NutrientDefinition.id.in_(nutrient_ids))
            )
        }
        if nutrient_ids
        else {}
    )

    warnings: list[str] = [TECHNICAL_DISCLAIMER]
    assumptions: list[str] = [NO_DERIVED_NUTRIENTS]
    evidence: list[EvidenceDraft] = []
    formula_net = Decimal("0")
    item_masses: dict[UUID, Decimal] = {}

    for item in items:
        unit = units[item.measurement_unit_id]
        mass_g = mass_to_grams(item.net_quantity, unit)
        item_masses[item.id] = mass_g
        formula_net += mass_g
        if unit.code != "g":
            evidence.append(
                EvidenceDraft(
                    evidence_type="unit_conversion",
                    status="recorded",
                    formulation_item_id=item.id,
                    ingredient_version_id=item.ingredient_version_id,
                    ingredient_quantity_g=quantize_quantity(mass_g),
                    message=(
                        f"Quantidade convertida para gramas via fator SI da unidade {unit.code}."
                    ),
                )
            )

    formula_net = quantize_quantity(formula_net)
    if formula_net <= 0:
        raise NutritionError("massa líquida da fórmula deve ser positiva")

    rate = bake_loss_rate if bake_loss_rate is not None else version.expected_bake_loss_rate
    final_mass, yield_assumptions, yield_evidence = resolve_final_mass(
        formula_net,
        expected_final_mass_g=expected_final_mass_g,
        bake_loss_rate=rate,
    )
    assumptions.extend(yield_assumptions)
    evidence.extend(yield_evidence)

    portion: Decimal | None = None
    if portion_mass_g is not None:
        portion = _as_decimal(portion_mass_g, "porção técnica")
        if portion <= 0:
            raise NutritionError("porção técnica deve ser positiva")
        assumptions.append("Porção técnica explícita; não é porção legal nem decisão regulatória.")
        evidence.append(
            EvidenceDraft(
                evidence_type="portion_assumption",
                status="recorded",
                message="Porção técnica informada; prévia bruta, sem valor diário.",
                contribution_amount=quantize_quantity(portion),
            )
        )

    accumulators: dict[UUID, NutrientAccumulator] = {}
    for nutrient_id in profile_nutrient_ids:
        definition = definitions.get(nutrient_id)
        if definition is not None:
            accumulators[nutrient_id] = NutrientAccumulator(nutrient=definition)
    for nutrient_id, definition in definitions.items():
        accumulators.setdefault(nutrient_id, NutrientAccumulator(nutrient=definition))

    incomplete = False
    for item in items:
        version_row = versions[item.ingredient_version_id]
        if version_row.organization_id != version.organization_id:
            raise NutritionError("ingrediente de outra organização")
        ingredient = ingredients[version_row.ingredient_id]
        published_rows = nutrients_by_version.get(item.ingredient_version_id, [])
        if not published_rows:
            incomplete = True
            warnings.append(
                f"Versão {version_row.version_number} de {ingredient.code} "
                "sem dossiê nutricional publicado."
            )
            evidence.append(
                EvidenceDraft(
                    evidence_type="missing_value",
                    status="missing",
                    formulation_item_id=item.id,
                    ingredient_version_id=item.ingredient_version_id,
                    data_source_id=version_row.data_source_id,
                    ingredient_quantity_g=quantize_quantity(item_masses[item.id]),
                    message=(
                        "Dado nutricional ausente na IngredientVersion referenciada; "
                        "não percorrido composto/preparação nem preenchido com zero."
                    ),
                )
            )
            for accumulator in accumulators.values():
                accumulator.missing = True
            continue
        present = {row.nutrient_id: row for row in published_rows}
        for nutrient_id, accumulator in accumulators.items():
            source = present.get(nutrient_id)
            if source is None:
                accumulator.missing = True
                incomplete = True
                evidence.append(
                    EvidenceDraft(
                        evidence_type="missing_value",
                        status="missing",
                        formulation_item_id=item.id,
                        ingredient_version_id=item.ingredient_version_id,
                        nutrient_definition_id=nutrient_id,
                        data_source_id=version_row.data_source_id,
                        ingredient_quantity_g=quantize_quantity(item_masses[item.id]),
                        source_basis=SOURCE_BASIS,
                        message=(
                            f"Nutriente {accumulator.nutrient.code} ausente na versão "
                            f"{ingredient.code} v{version_row.version_number}; ausência ≠ zero."
                        ),
                    )
                )
                continue
            source_incomplete, source_evidence = _apply_source_value(
                source=source,
                accumulator=accumulator,
                item_id=item.id,
                version_row=version_row,
                mass_g=item_masses[item.id],
                ingredient_code=ingredient.code,
            )
            evidence.extend(source_evidence)
            if source_incomplete:
                incomplete = True

    if profile_nutrient_ids:
        for nutrient_id in profile_nutrient_ids:
            accumulator = accumulators[nutrient_id]
            if not accumulator.seen:
                accumulator.missing = True
                incomplete = True
                evidence.append(
                    EvidenceDraft(
                        evidence_type="missing_value",
                        status="missing",
                        nutrient_definition_id=nutrient_id,
                        message=(
                            f"Nutriente {accumulator.nutrient.code} ausente em todos os "
                            "ingredientes do perfil; ausência ≠ zero."
                        ),
                    )
                )

    if not accumulators:
        incomplete = True
        warnings.append("Nenhum nutriente publicado nas versões referenciadas; prévia incompleta.")

    if requested_basis in {BASIS_PER_100G, BASIS_PORTION} and final_mass is None:
        incomplete = True
        warnings.append(
            "Base por 100 g ou porção técnica pedida sem massa final; resultado incompleto."
        )
    if requested_basis == BASIS_PORTION and portion is None:
        incomplete = True
        warnings.append("Porção técnica não informada; resultado por porção incompleto.")

    result_items: list[tuple[NutrientDefinition, Decimal, Decimal | None, Decimal | None, str]] = []
    for nutrient_id, accumulator in sorted(
        accumulators.items(), key=lambda pair: pair[1].nutrient.code
    ):
        total = quantize_quantity(accumulator.known_total)
        per_100g = None
        portion_amount = None
        if final_mass is not None:
            per_100g = quantize_quantity(total / final_mass * Decimal("100"))
            if portion is not None:
                portion_amount = quantize_quantity(per_100g * portion / Decimal("100"))
        completeness = _completeness(accumulator)
        result_items.append((accumulator.nutrient, total, per_100g, portion_amount, completeness))

    status = "incomplete" if incomplete else "complete"
    if version.status == "draft":
        warnings.append("Cálculo de versão em rascunho (simulação); não é cálculo aprovado.")

    return NutritionResult(
        calculation_basis=requested_basis,
        formulation_version_status=version.status,
        is_simulation=version.status != "published",
        formula_net_mass_g=formula_net,
        expected_final_mass_g=final_mass,
        portion_mass_g=quantize_quantity(portion) if portion is not None else None,
        status=status,
        warnings=tuple(warnings),
        assumptions=tuple(assumptions),
        items=tuple(result_items),
        evidence=tuple(evidence),
        expectation_profile_id=expectation_profile.id if expectation_profile else None,
    )


def persist_nutrition_calculation(
    session: Session,
    version: FormulationVersion,
    result: NutritionResult,
    calculated_by_user_id: UUID | None = None,
) -> NutritionCalculation:
    row = NutritionCalculation(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        status=result.status,
        calculation_basis=result.calculation_basis,
        formulation_version_status=result.formulation_version_status,
        is_simulation=result.is_simulation,
        formula_net_mass_g=result.formula_net_mass_g,
        expected_final_mass_g=result.expected_final_mass_g,
        portion_mass_g=result.portion_mass_g,
        algorithm_name=ALGORITHM_NAME,
        algorithm_version=ALGORITHM_VERSION,
        rounding_policy=ROUNDING_POLICY,
        calculated_by_user_id=calculated_by_user_id,
        warnings=list(result.warnings),
        assumptions=list(result.assumptions),
        expectation_profile_id=result.expectation_profile_id,
    )
    session.add(row)
    session.flush()
    item_ids: dict[UUID, UUID] = {}
    for nutrient, total, per_100g, portion_amount, completeness in result.items:
        item = NutritionCalculationItem(
            organization_id=version.organization_id,
            nutrition_calculation_id=row.id,
            nutrient_definition_id=nutrient.id,
            measurement_unit_id=nutrient.unit_id,
            whole_formula_amount=total,
            per_100g_amount=per_100g,
            technical_portion_amount=portion_amount,
            completeness_status=completeness,
        )
        session.add(item)
        session.flush()
        item_ids[nutrient.id] = item.id
    for draft in result.evidence:
        session.add(
            CalculationEvidence(
                organization_id=version.organization_id,
                nutrition_calculation_id=row.id,
                nutrition_calculation_item_id=(
                    item_ids.get(draft.nutrient_definition_id)
                    if draft.nutrient_definition_id
                    else None
                ),
                formulation_item_id=draft.formulation_item_id,
                ingredient_version_id=draft.ingredient_version_id,
                ingredient_nutrient_id=draft.ingredient_nutrient_id,
                data_source_id=draft.data_source_id,
                evidence_type=draft.evidence_type,
                ingredient_quantity_g=draft.ingredient_quantity_g,
                source_nutrient_value=draft.source_nutrient_value,
                source_basis=draft.source_basis,
                contribution_amount=draft.contribution_amount,
                status=draft.status,
                message=draft.message,
            )
        )
    session.flush()
    return row


def invalidate_nutrition_calculation(calculation: NutritionCalculation) -> None:
    if calculation.status == "invalidated":
        return
    calculation.status = "invalidated"


def reconstruct_whole_formula(
    evidence: Sequence[CalculationEvidence],
    nutrient_definition_id: UUID,
    item_id: UUID,
) -> Decimal:
    total = Decimal("0")
    for row in evidence:
        if row.nutrition_calculation_item_id != item_id:
            continue
        if row.evidence_type != "calculated_contribution":
            continue
        if row.contribution_amount is None:
            continue
        total += row.contribution_amount
    return quantize_quantity(total)
