"""Motor determinístico de custo. Não altera snapshots operacionais."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    ZERO,
)
from app.modules.costing_pricing.formulas import quantize_money
from app.modules.costing_pricing.models import (
    CostingAssumption,
    CostingCalculation,
    CostingComponent,
    CostingEvidence,
    CostingGap,
    CostingPolicyVersion,
)
from app.modules.costing_pricing.valuation import cost_for_quantity, select_price
from app.modules.formula_lab.models import (
    Formulation,
    FormulationItem,
    FormulationVersion,
    ScaleCalculationItem,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_execution.units import canonical_mass_unit
from app.modules.production_execution.projections import project_consumption, project_yield
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionOrder,
    ProductionOrderMaterial,
)


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _enabled(policy: CostingPolicyVersion, category: str) -> bool:
    enabled = policy.enabled_categories or []
    return category in enabled


def _assumptions(session: Session, policy: CostingPolicyVersion, at: datetime) -> list[CostingAssumption]:
    rows = list(
        session.scalars(
            select(CostingAssumption).where(
                CostingAssumption.costing_policy_version_id == policy.id
            )
        )
    )
    return [
        row
        for row in rows
        if row.effective_from <= at and (row.effective_to is None or row.effective_to >= at)
    ]


def _add_component(session, calc, *, category, origin_type, origin_id, nature, behavior, quantity, unit_code, rate, amount, quality, evidence, allocation_rule=None):
    existing = session.scalar(
        select(CostingComponent).where(
            CostingComponent.costing_calculation_id == calc.id,
            CostingComponent.origin_type == origin_type,
            CostingComponent.origin_id == origin_id,
        )
    )
    if existing is not None:
        raise ValidationError("dupla_contagem")
    row = CostingComponent(
        id=uuid4(),
        organization_id=calc.organization_id,
        costing_calculation_id=calc.id,
        category=category,
        origin_type=origin_type,
        origin_id=origin_id,
        nature=nature,
        behavior=behavior,
        quantity=quantity,
        unit_code=unit_code,
        rate=rate,
        amount=amount,
        quality=quality,
        allocation_rule=allocation_rule,
    )
    session.add(row)
    session.add(
        CostingEvidence(
            organization_id=calc.organization_id,
            costing_component_id=row.id,
            payload=evidence,
        )
    )
    return row


def _add_gap(session, calc, code: str, message: str) -> None:
    session.add(
        CostingGap(
            organization_id=calc.organization_id,
            costing_calculation_id=calc.id,
            code=code,
            message=message,
        )
    )


def _apply_assumptions(session, calc, policy, at: datetime, seen: set[str]) -> Decimal:
    total = ZERO
    for row in _assumptions(session, policy, at):
        if not _enabled(policy, row.category):
            continue
        key = f"assumption:{row.id}"
        if key in seen:
            raise ValidationError("dupla_contagem")
        seen.add(key)
        _add_component(
            session,
            calc,
            category=row.category,
            origin_type="assumption",
            origin_id=str(row.id),
            nature=row.nature,
            behavior=row.behavior,
            quantity=Decimal("1"),
            unit_code=row.unit_code,
            rate=row.amount,
            amount=row.amount,
            quality=row.quality,
            evidence={
                "code": row.code,
                "reason": row.reason,
                "author": str(row.created_by_user_id),
                "manual": True,
            },
            allocation_rule="manual_assumption",
        )
        total += row.amount
    return total


def _planned_lines(session: Session, formulation_version_id, scale_id, use_gross: bool):
    items = list(
        session.scalars(
            select(FormulationItem).where(
                FormulationItem.formulation_version_id == formulation_version_id
            )
        )
    )
    scaled = {}
    if scale_id is not None:
        for row in session.scalars(
            select(ScaleCalculationItem).where(ScaleCalculationItem.scale_calculation_id == scale_id)
        ):
            scaled[row.formulation_item_id] = row
    lines = []
    for item in items:
        scale_item = scaled.get(item.id)
        if scale_item is not None:
            qty = scale_item.scaled_gross_quantity if use_gross else scale_item.scaled_net_quantity
        else:
            qty = item.net_quantity * item.correction_factor if use_gross else item.net_quantity
        category = "packaging" if item.role == "packaging" else "ingredient"
        lines.append((item, qty, category))
    return lines


def calculate(
    session: Session,
    *,
    policy: CostingPolicyVersion,
    kind: str,
    actor_user_id,
    valuation_at: datetime,
    formulation_version_id=None,
    scale_calculation_id=None,
    production_order_id=None,
    production_batch_id=None,
    explicit_item_id=None,
    planned_batches: int | None = None,
) -> CostingCalculation:
    if policy.status != "published":
        raise ValidationError("transicao_invalida")
    formulation_version = None
    formulation = None
    order = None
    if formulation_version_id:
        formulation_version = session.get(FormulationVersion, formulation_version_id)
        if formulation_version is None:
            raise ValidationError("recurso_nao_encontrado")
        formulation = session.get(Formulation, formulation_version.formulation_id)
    if production_order_id:
        order = session.get(ProductionOrder, production_order_id)
        if order is None:
            raise ValidationError("recurso_nao_encontrado")
        formulation_version_id = order.formulation_version_id
        scale_calculation_id = order.scale_calculation_id
        formulation_version = session.get(FormulationVersion, formulation_version_id)
        formulation = session.get(Formulation, formulation_version.formulation_id)
    calc = CostingCalculation(
        id=uuid4(),
        organization_id=policy.organization_id,
        costing_policy_version_id=policy.id,
        kind=kind,
        completeness="partial",
        technical_product_id=None if formulation is None else formulation.technical_product_id,
        formulation_id=None if formulation is None else formulation.id,
        formulation_version_id=formulation_version_id,
        scale_calculation_id=scale_calculation_id,
        production_order_id=production_order_id,
        production_batch_id=production_batch_id,
        valuation_at=valuation_at,
        currency=policy.currency,
        snapshot={},
        content_hash="pending",
        algorithm_name=ALGORITHM_NAME,
        algorithm_version=ALGORITHM_VERSION,
        created_by_user_id=actor_user_id,
    )

    total = ZERO
    missing = 0
    seen: set[str] = set()
    previous_autoflush = session.autoflush
    session.autoflush = False
    if kind in {"planned", "standard"} and formulation_version_id:
        for item, qty, category in _planned_lines(
            session, formulation_version_id, scale_calculation_id, policy.use_gross_quantity
        ):
            if not _enabled(policy, category):
                continue
            origin = f"formulation_item:{item.id}"
            if origin in seen:
                raise ValidationError("dupla_contagem")
            seen.add(origin)
            snapshot = select_price(
                session,
                ingredient_version_id=item.ingredient_version_id,
                valuation_at=valuation_at,
                currency=policy.currency,
                criterion=policy.price_criterion,
                explicit_item_id=explicit_item_id,
            )
            unit = session.get(MeasurementUnit, item.measurement_unit_id)
            if snapshot is None:
                missing += 1
                _add_gap(
                    session,
                    calc,
                    "preco_ausente",
                    "Não há preço vigente para o ingrediente. Ausência não é zero.",
                )
                _add_component(
                    session,
                    calc,
                    category=category,
                    origin_type="formulation_item",
                    origin_id=str(item.id),
                    nature="direct",
                    behavior="variable",
                    quantity=qty,
                    unit_code=None if unit is None else unit.code,
                    rate=None,
                    amount=None,
                    quality="missing",
                    evidence={"ingredient_version_id": str(item.ingredient_version_id)},
                )
                continue
            amount, evidence = cost_for_quantity(session, snapshot, qty, item.measurement_unit_id)
            if planned_batches and planned_batches > 1:
                amount = amount * Decimal(planned_batches)
                evidence["planned_batches"] = planned_batches
            _add_component(
                session,
                calc,
                category=category,
                origin_type="formulation_item",
                origin_id=str(item.id),
                nature="direct",
                behavior="variable",
                quantity=qty,
                unit_code=None if unit is None else unit.code,
                rate=None if amount is None else (amount / qty if qty else None),
                amount=amount,
                quality="standard_cost" if kind == "standard" else "current_price",
                evidence=evidence,
                allocation_rule="ingredient_quantity",
            )
            if amount is not None:
                total += amount
    elif kind == "actual":
        if production_order_id is None:
            raise ValidationError("contrato_invalido")
        materials = list(
            session.scalars(
                select(ProductionOrderMaterial).where(
                    ProductionOrderMaterial.production_order_id == production_order_id
                )
            )
        )
        batches = list(
            session.scalars(
                select(ProductionBatch).where(ProductionBatch.production_order_id == production_order_id)
            )
        )
        if production_batch_id:
            batches = [row for row in batches if row.id == production_batch_id]
        batch_ids = [row.id for row in batches]
        batch_materials = list(
            session.scalars(
                select(ProductionBatchMaterial).where(
                    ProductionBatchMaterial.production_batch_id.in_(batch_ids or [UUID(int=0)])
                )
            )
        )
        for material in materials:
            category = "ingredient"
            if not _enabled(policy, category):
                continue
            qty = material.gross_quantity if policy.use_gross_quantity else material.net_quantity
            related = [row for row in batch_materials if row.production_order_material_id == material.id]
            consume = ZERO
            returned = ZERO
            waste = ZERO
            for batch_material in related:
                projected = project_consumption(session, batch_material.id)
                consume += projected["consume"]
                returned += projected["return"]
                waste += projected["waste"]
            net = consume - returned if policy.include_return else consume
            origin = f"order_material:{material.id}"
            if origin in seen:
                raise ValidationError("dupla_contagem")
            seen.add(origin)
            snapshot = select_price(
                session,
                ingredient_version_id=material.ingredient_version_id,
                valuation_at=valuation_at,
                currency=policy.currency,
                criterion=policy.price_criterion,
                explicit_item_id=explicit_item_id,
            )
            if snapshot is None:
                missing += 1
                _add_gap(
                    session,
                    calc,
                    "preco_ausente",
                    "Não há preço vigente para o consumo. Ausência não é zero.",
                )
                _add_component(
                    session,
                    calc,
                    category=category,
                    origin_type="order_material",
                    origin_id=str(material.id),
                    nature="direct",
                    behavior="variable",
                    quantity=net,
                    unit_code=None,
                    rate=None,
                    amount=None,
                    quality="missing",
                    evidence={"weighed_is_not_consumed": True, "planned_quantity": format(qty, "f")},
                )
                continue
            mass_unit = canonical_mass_unit(session)
            amount, evidence = cost_for_quantity(session, snapshot, net, mass_unit.id)
            evidence["consume"] = format(consume, "f")
            evidence["return"] = format(returned, "f")
            evidence["waste"] = format(waste, "f")
            evidence["weighed_is_not_consumed"] = True
            _add_component(
                session,
                calc,
                category=category,
                origin_type="order_material",
                origin_id=str(material.id),
                nature="direct",
                behavior="variable",
                quantity=net,
                unit_code=None,
                rate=None,
                amount=amount,
                quality="operational_fact",
                evidence=evidence,
                allocation_rule="net_consumption",
            )
            if amount is not None:
                total += amount
            if policy.include_waste and waste > ZERO and _enabled(policy, "waste"):
                waste_amount, waste_ev = cost_for_quantity(
                    session, snapshot, waste, mass_unit.id
                )
                _add_component(
                    session,
                    calc,
                    category="waste",
                    origin_type="waste",
                    origin_id=str(material.id),
                    nature="direct",
                    behavior="variable",
                    quantity=waste,
                    unit_code=None,
                    rate=None,
                    amount=waste_amount,
                    quality="operational_fact",
                    evidence=waste_ev,
                    allocation_rule="waste_distinct_from_return",
                )
                if waste_amount is not None:
                    total += waste_amount
        sellable = None
        produced = None
        for batch in batches:
            projected = project_yield(session, batch)
            if projected.sellable_units is not None:
                sellable = (sellable or ZERO) + projected.sellable_units
            if projected.final_mass is not None:
                produced = (produced or ZERO) + projected.final_mass
        calc.sellable_quantity = sellable
        calc.produced_quantity = produced
        leftover_total = ZERO
        scrap_total = ZERO
        for batch in batches:
            projected = project_yield(session, batch)
            if projected.leftover is not None:
                leftover_total += projected.leftover
            if projected.scrap is not None:
                scrap_total += projected.scrap
        if leftover_total > ZERO:
            _add_component(
                session,
                calc,
                category="other",
                origin_type="leftover",
                origin_id=str(production_order_id),
                nature="direct",
                behavior="variable",
                quantity=leftover_total,
                unit_code=None,
                rate=None,
                amount=None,
                quality="operational_fact",
                evidence={
                    "leftover_is_not_waste": True,
                    "valued": False,
                    "include_leftover": policy.include_leftover,
                },
                allocation_rule="leftover_distinct",
            )
        if scrap_total > ZERO:
            _add_component(
                session,
                calc,
                category="waste",
                origin_type="scrap",
                origin_id=str(production_order_id),
                nature="direct",
                behavior="variable",
                quantity=scrap_total,
                unit_code=None,
                rate=None,
                amount=None,
                quality="operational_fact",
                evidence={"scrap_is_not_return": True, "valued": False},
                allocation_rule="scrap_distinct",
            )
        if policy.use_sellable_yield and (sellable is None or sellable <= ZERO):
            _add_gap(
                session,
                calc,
                "rendimento_ausente",
                "Sem rendimento vendável confiável o custo por unidade vendável permanece ausente.",
            )
            missing += 1
    else:
        raise ValidationError("contrato_invalido")

    total += _apply_assumptions(session, calc, policy, valuation_at, seen)
    calc.total_amount = None if missing and total == ZERO else quantize_money(total) if total else (None if missing else ZERO)
    if calc.total_amount is not None:
        if planned_batches and planned_batches > 0:
            calc.batch_amount = quantize_money(calc.total_amount / Decimal(planned_batches))
        if calc.produced_quantity and calc.produced_quantity > ZERO:
            calc.produced_unit_amount = quantize_money(calc.total_amount / calc.produced_quantity)
            calc.mass_amount = calc.produced_unit_amount
        if calc.sellable_quantity and calc.sellable_quantity > ZERO:
            calc.sellable_unit_amount = quantize_money(calc.total_amount / calc.sellable_quantity)
        elif kind == "actual":
            calc.sellable_unit_amount = None
    calc.completeness = (
        "insufficient_data" if missing and calc.total_amount is None else "partial" if missing else "complete"
    )
    snapshot = {
        "policy_version_id": str(policy.id),
        "kind": kind,
        "valuation_at": valuation_at.isoformat(),
        "algorithm": ALGORITHM_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "planned_batches": planned_batches,
        "gaps": missing,
        "scale_calculation_id": None if scale_calculation_id is None else str(scale_calculation_id),
        "leftover_distinct_from_waste": True,
        "return_distinct_from_waste": True,
        "weighed_is_not_consumed": True,
    }
    calc.snapshot = snapshot
    calc.content_hash = _digest(snapshot | {"total": None if calc.total_amount is None else format(calc.total_amount, "f")})
    session.autoflush = previous_autoflush
    session.add(calc)
    session.flush()
    return calc
