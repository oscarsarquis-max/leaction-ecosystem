"""Motor analítico. Consulta fatos canônicos sem copiá-los."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from json import dumps
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.models import CostingCalculation, PracticedPrice, PricingSimulation
from app.modules.identity_organization.authorization import (
    PERMISSION_REPORTING_COMPLIANCE_READ,
    PERMISSION_REPORTING_COSTING_READ,
    PERMISSION_REPORTING_INVENTORY_READ,
    PERMISSION_REPORTING_PRICING_READ,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import (
    Ingredient,
    IngredientNutrient,
    IngredientVersion,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryConsumptionPosting,
    InventoryItem,
    InventoryLot,
    InventoryMovement,
    InventoryReplenishmentItem,
    InventoryReplenishmentSuggestion,
    ProcurementOrder,
    ProcurementRequisition,
)
from app.modules.labeling_compliance.models import (
    LabelingAssessment,
    LabelingDossier,
    LabelingDossierVersion,
)
from app.modules.production_execution.constants import (
    CONSUMPTION_CONSUME,
    CONSUMPTION_CORRECTION,
    CONSUMPTION_RETURN,
    CONSUMPTION_WASTE,
    YIELD_GOOD_UNITS,
    YIELD_LEFTOVER,
    YIELD_POST_BAKE_MASS,
    YIELD_PRE_BAKE_MASS,
    YIELD_SCRAP,
)
from app.modules.production_execution.models import (
    ProductionMaterialConsumption,
    ProductionOccurrence,
    ProductionSheetIssue,
    ProductionStepExecution,
    ProductionYieldMeasurement,
)
from app.modules.production_planning.errors import ValidationError
from app.modules.production_planning.models import (
    ProductionEvent,
    ProductionOrder,
    ProductionOrderMaterial,
    ProductionPlan,
)
from app.modules.reporting_analytics.catalog import REPORTS
from app.modules.reporting_analytics.constants import (
    CANCELLED_STATUSES,
    COMPLETED_STATUSES,
    CURRENCY,
    IN_EXECUTION_STATUSES,
    METRICS_VERSION,
    PLANNED_STATUSES,
    QUERY_BUDGET,
    QUERY_VERSION,
    RELEASED_STATUSES,
    REPORT_VERSION,
    SHORT_CLOSED_STATUSES,
    ZERO,
)
from app.modules.reporting_analytics.filters import ReportFilters, utc_window
from app.modules.reporting_analytics.formulas import (
    coverage,
    known_zero,
    present,
    ratio_percent,
    reuse_contribution,
    reuse_gross,
    reuse_markup,
    unavailable,
)
from app.modules.reporting_analytics.metrics import METRICS


class QueryBudget:
    def __init__(self) -> None:
        self.count = 0

    def run(self, session: Session, statement):
        self.count += 1
        if self.count > QUERY_BUDGET:
            raise ValidationError("indisponivel")
        return list(session.scalars(statement))


def _anchor(order: ProductionOrder) -> datetime:
    return order.planned_start_at or order.created_at


def _in_window(moment: datetime, start: datetime, end: datetime) -> bool:
    return start <= moment < end


def _hash_payload(payload: dict) -> str:
    canonical = dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _status_group(status: str) -> str:
    if status in PLANNED_STATUSES:
        return "planned"
    if status in RELEASED_STATUSES:
        return "released"
    if status in IN_EXECUTION_STATUSES:
        return "in_execution"
    if status in COMPLETED_STATUSES:
        return "completed"
    if status in SHORT_CLOSED_STATUSES:
        return "short_closed"
    if status in CANCELLED_STATUSES:
        return "cancelled"
    return "other"


def _apply_order_filters(query, filters: ReportFilters):
    if filters.establishment_id:
        query = query.where(ProductionOrder.establishment_id == filters.establishment_id)
    if filters.technical_product_id:
        query = query.where(ProductionOrder.technical_product_id == filters.technical_product_id)
    if filters.formulation_version_id:
        query = query.where(ProductionOrder.formulation_version_id == filters.formulation_version_id)
    if filters.production_order_id:
        query = query.where(ProductionOrder.id == filters.production_order_id)
    if filters.status:
        query = query.where(ProductionOrder.status == filters.status)
    return query


def _orders(session: Session, org_id: UUID, filters: ReportFilters, budget: QueryBudget):
    start, end = utc_window(filters)
    query = _apply_order_filters(
        select(ProductionOrder).where(ProductionOrder.organization_id == org_id),
        filters,
    )
    rows = [row for row in budget.run(session, query) if _in_window(_anchor(row), start, end)]
    return rows


def _indicator(code: str, result: dict, coverage_data: dict | None = None) -> dict:
    spec = METRICS[code]
    return {
        "code": code,
        "name": spec.name,
        "version": spec.version,
        "unit": spec.unit,
        "drill_down": spec.drill_down,
        "origins": list(spec.origins),
        "coverage": coverage_data,
        **result,
    }


def _orders_by_status(orders: list[ProductionOrder]) -> dict:
    counts = defaultdict(int)
    for order in orders:
        counts[order.status] += 1
    if not orders:
        value = unavailable("conjunto_vazio")
    else:
        value = present(len(orders), unit="count")
    return _indicator(
        "orders_by_status",
        {**value, "by_status": dict(counts), "by_group": {
            "planned": sum(1 for item in orders if item.status in PLANNED_STATUSES),
            "released": sum(1 for item in orders if item.status in RELEASED_STATUSES),
            "in_execution": sum(1 for item in orders if item.status in IN_EXECUTION_STATUSES),
            "completed": sum(1 for item in orders if item.status in COMPLETED_STATUSES),
            "short_closed": sum(1 for item in orders if item.status in SHORT_CLOSED_STATUSES),
            "cancelled": sum(1 for item in orders if item.status in CANCELLED_STATUSES),
        }},
        coverage(len(orders), len(orders)) if orders else coverage(0, 0),
    )


def _quantity_block(orders: list[ProductionOrder], yields: list[ProductionYieldMeasurement]) -> tuple[dict, dict]:
    modes = {order.target_mode for order in orders}
    if not orders:
        planned = _indicator("planned_quantity", unavailable("conjunto_vazio"), coverage(0, 0))
    elif len(modes) > 1:
        planned = _indicator("planned_quantity", unavailable("unidade_incompativel"), coverage(0, len(orders)))
    else:
        total = sum((order.target_quantity for order in orders), ZERO)
        planned = _indicator(
            "planned_quantity",
            present(total, unit=next(iter(modes))),
            coverage(len(orders), len(orders)),
        )
    sellable = [row for row in yields if row.measurement_type == YIELD_GOOD_UNITS]
    if not sellable:
        actual = _indicator("actual_quantity", unavailable("rendimento_ausente"), coverage(0, len(orders)))
    else:
        units = {row.unit_code for row in sellable}
        if len(units) > 1:
            actual = _indicator("actual_quantity", unavailable("unidade_incompativel"), coverage(0, len(sellable)))
        else:
            total = sum((row.quantity for row in sellable), ZERO)
            actual = _indicator(
                "actual_quantity",
                present(total, unit=next(iter(units))),
                coverage(len({row.production_order_id for row in sellable}), len(orders) or 1),
            )
    return planned, actual


def _completion_rates(orders: list[ProductionOrder]) -> tuple[dict, dict]:
    closed = [item for item in orders if item.status in COMPLETED_STATUSES + SHORT_CLOSED_STATUSES]
    completed = [item for item in closed if item.status in COMPLETED_STATUSES]
    shorted = [item for item in closed if item.status in SHORT_CLOSED_STATUSES]
    cover = coverage(len(closed), len(orders)) if orders else coverage(0, 0)
    if not closed:
        empty = unavailable("conjunto_vazio")
        return _indicator("normal_completion_rate", empty, cover), _indicator("short_close_rate", empty, cover)
    normal = ratio_percent(len(completed), len(closed))
    short = ratio_percent(len(shorted), len(closed))
    return (
        _indicator("normal_completion_rate", present(normal, unit="percent"), cover),
        _indicator("short_close_rate", present(short, unit="percent"), cover),
    )


def _yield_metrics(orders: list[ProductionOrder], yields: list[ProductionYieldMeasurement]) -> tuple[dict, dict, dict]:
    pre = defaultdict(Decimal)
    post = defaultdict(Decimal)
    leftover = ZERO
    scrap = ZERO
    for row in yields:
        if row.reverses_id:
            continue
        if row.measurement_type == YIELD_PRE_BAKE_MASS:
            pre[row.production_batch_id] += row.quantity
        elif row.measurement_type == YIELD_POST_BAKE_MASS:
            post[row.production_batch_id] += row.quantity
        elif row.measurement_type == YIELD_LEFTOVER:
            leftover += row.quantity
        elif row.measurement_type == YIELD_SCRAP:
            scrap += row.quantity
    pairs = [
        (pre[key], post[key])
        for key in set(pre) | set(post)
        if pre.get(key, ZERO) > ZERO and key in post
    ]
    closed = [item for item in orders if item.status in COMPLETED_STATUSES + SHORT_CLOSED_STATUSES]
    cover = coverage(len(pairs), len(closed) or len(orders) or 0)
    if not pairs:
        missing = unavailable("rendimento_ausente")
        return (
            _indicator("yield_actual", missing, cover),
            _indicator("loss_actual", missing, cover),
            _indicator("yield_coverage", cover, cover),
        )
    pre_total = sum((item[0] for item in pairs), ZERO)
    post_total = sum((item[1] for item in pairs), ZERO)
    yield_rate = ratio_percent(post_total, pre_total)
    loss_rate = ratio_percent(pre_total - post_total, pre_total)
    extra = {"leftover": format(leftover, "f"), "scrap": format(scrap, "f"), "distinguished": True}
    return (
        _indicator("yield_actual", {**present(yield_rate, unit="percent"), **extra}, cover),
        _indicator("loss_actual", present(loss_rate, unit="percent"), cover),
        _indicator("yield_coverage", cover, cover),
    )


def _consumption(
    session: Session,
    org_id: UUID,
    orders: list[ProductionOrder],
    filters: ReportFilters,
    budget: QueryBudget,
) -> tuple[dict, dict]:
    order_ids = [item.id for item in orders]
    if not order_ids:
        empty = unavailable("conjunto_vazio")
        return _indicator("net_consumption", empty, coverage(0, 0)), _indicator(
            "consumption_variance", empty, coverage(0, 0)
        )
    planned_rows = budget.run(
        session,
        select(ProductionOrderMaterial).where(
            ProductionOrderMaterial.organization_id == org_id,
            ProductionOrderMaterial.production_order_id.in_(order_ids),
        ),
    )
    facts = budget.run(
        session,
        select(ProductionMaterialConsumption).where(
            ProductionMaterialConsumption.organization_id == org_id,
            ProductionMaterialConsumption.production_order_id.in_(order_ids),
        ),
    )
    if filters.ingredient_id:
        planned_rows = [row for row in planned_rows if row.ingredient_version_id]
    planned_units = {row.unit_code for row in planned_rows}
    fact_units = {row.canonical_unit_code for row in facts}
    if planned_rows and len(planned_units) > 1:
        return (
            _indicator("net_consumption", unavailable("unidade_incompativel"), coverage(0, len(planned_rows))),
            _indicator("consumption_variance", unavailable("unidade_incompativel"), coverage(0, len(planned_rows))),
        )
    consume = sum((row.canonical_quantity for row in facts if row.consumption_type == CONSUMPTION_CONSUME), ZERO)
    returned = sum((row.canonical_quantity for row in facts if row.consumption_type == CONSUMPTION_RETURN), ZERO)
    waste = sum((row.canonical_quantity for row in facts if row.consumption_type == CONSUMPTION_WASTE), ZERO)
    correction = sum(
        (row.canonical_quantity for row in facts if row.consumption_type == CONSUMPTION_CORRECTION), ZERO
    )
    net = consume - returned
    planned = sum((row.gross_quantity for row in planned_rows), ZERO)
    cover = coverage(len(facts), len(planned_rows) or len(facts) or 0)
    net_result = (
        known_zero()
        if facts and net == ZERO
        else present(net, unit=next(iter(fact_units), "mass"))
        if facts
        else unavailable("consumo_ausente")
    )
    variance = (
        present(ratio_percent(net - planned, planned), unit="percent")
        if planned > ZERO and facts
        else unavailable("planejado_ausente")
    )
    extra = {
        "returned": format(returned, "f"),
        "waste": format(waste, "f"),
        "correction": format(correction, "f"),
        "planned": format(planned, "f") if planned_rows else None,
    }
    return (
        _indicator("net_consumption", {**net_result, **extra}, cover),
        _indicator("consumption_variance", variance, cover),
    )


def _cost_metrics(session: Session, org_id: UUID, filters: ReportFilters, budget: QueryBudget, allowed: bool):
    if not allowed:
        blocked = unavailable("permissao_negada")
        return _indicator("cost_variance", blocked), _indicator("cost_per_sellable_unit", blocked)
    start, end = utc_window(filters)
    rows = budget.run(
        session,
        select(CostingCalculation).where(
            CostingCalculation.organization_id == org_id,
            CostingCalculation.created_at >= start,
            CostingCalculation.created_at < end,
        ),
    )
    if filters.technical_product_id:
        rows = [row for row in rows if row.technical_product_id == filters.technical_product_id]
    if any(row.currency != CURRENCY for row in rows):
        mixed = unavailable("moeda_incompativel")
        return _indicator("cost_variance", mixed), _indicator("cost_per_sellable_unit", mixed)
    planned = [row for row in rows if row.kind == "planned" and row.completeness == "complete"]
    actual = [row for row in rows if row.kind == "actual" and row.completeness == "complete"]
    planned_total = sum((row.total_amount or ZERO for row in planned), ZERO)
    actual_total = sum((row.total_amount or ZERO for row in actual), ZERO)
    cover = coverage(len(planned) + len(actual), len(rows) or 1)
    if not planned or not actual:
        variance = unavailable("par_previsto_realizado_ausente")
    else:
        variance = present(actual_total - planned_total, unit="BRL")
    sellable = [row for row in rows if row.sellable_unit_amount is not None]
    unit_cost = (
        present(sum((row.sellable_unit_amount for row in sellable), ZERO) / len(sellable), unit="BRL/unit")
        if sellable
        else unavailable("rendimento_vendavel_ausente")
    )
    return (
        _indicator("cost_variance", variance, cover),
        _indicator("cost_per_sellable_unit", unit_cost, coverage(len(sellable), len(rows) or 1)),
    )


def _price_metrics(session: Session, org_id: UUID, filters: ReportFilters, budget: QueryBudget, allowed: bool):
    if not allowed:
        blocked = unavailable("permissao_negada")
        return (
            _indicator("markup_percent", blocked),
            _indicator("gross_margin", blocked),
            _indicator("contribution_margin", blocked),
        )
    start, end = utc_window(filters)
    prices = budget.run(
        session,
        select(PracticedPrice).where(
            PracticedPrice.organization_id == org_id,
            PracticedPrice.valid_from < end,
        ),
    )
    if filters.price_channel:
        prices = [row for row in prices if row.channel == filters.price_channel]
    prices = [
        row
        for row in prices
        if row.valid_from < end and (row.valid_to is None or row.valid_to > start)
    ]
    if any(row.currency != CURRENCY for row in prices):
        mixed = unavailable("moeda_incompativel")
        return _indicator("markup_percent", mixed), _indicator("gross_margin", mixed), _indicator(
            "contribution_margin", mixed
        )
    calcs = budget.run(
        session,
        select(CostingCalculation).where(CostingCalculation.organization_id == org_id),
    )
    cost_by_product = {
        row.technical_product_id: row
        for row in calcs
        if row.kind in {"planned", "standard"} and row.completeness == "complete" and row.total_amount
    }
    sims = budget.run(
        session,
        select(PricingSimulation).where(PricingSimulation.organization_id == org_id),
    )
    markups = []
    grosses = []
    for price in prices:
        calc = cost_by_product.get(price.technical_product_id)
        if calc is None or calc.total_amount is None:
            continue
        markups.append(reuse_markup(price.amount, calc.total_amount))
        grosses.append(reuse_gross(price.amount, calc.total_amount))
    contribs = []
    for sim in sims:
        snap = sim.snapshot or {}
        if snap.get("contribution_margin") is not None:
            contribs.append(present(Decimal(str(snap["contribution_margin"])), unit="percent"))
        elif sim.suggested_price and snap.get("variable_product") is not None:
            contribs.append(
                reuse_contribution(
                    sim.suggested_price,
                    snap.get("variable_product") or ZERO,
                    snap.get("variable_selling") or ZERO,
                )
            )
    cover = coverage(len(markups), len(prices) or 1)

    def _first_or_missing(items, code):
        available = [item for item in items if item.get("status") == "available"]
        if not available:
            return _indicator(code, unavailable("preco_ou_custo_ausente"), cover)
        return _indicator(code, available[0], cover)

    return (
        _first_or_missing(markups, "markup_percent"),
        _first_or_missing(grosses, "gross_margin"),
        _first_or_missing(contribs, "contribution_margin"),
    )


def _price_coverage(session: Session, org_id: UUID, filters: ReportFilters, budget: QueryBudget) -> dict:
    ingredients = budget.run(
        session,
        select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.status == "active"),
    )
    if filters.ingredient_id:
        ingredients = [row for row in ingredients if row.id == filters.ingredient_id]
    items = budget.run(
        session,
        select(SupplierItem).where(SupplierItem.organization_id == org_id, SupplierItem.status == "active"),
    )
    prices = budget.run(session, select(SupplierItemPrice))
    item_ids = {row.id for row in items if row.ingredient_id in {ing.id for ing in ingredients}}
    priced_ingredients = {
        row.ingredient_id
        for row in items
        if row.id in {price.supplier_item_id for price in prices if price.supplier_item_id in item_ids}
    }
    cover = coverage(len(priced_ingredients), len(ingredients))
    return _indicator("price_coverage", cover, cover)


def _nutrition_coverage(session: Session, org_id: UUID, budget: QueryBudget) -> dict:
    versions = budget.run(
        session,
        select(IngredientVersion).where(
            IngredientVersion.organization_id == org_id,
            IngredientVersion.status == "published",
        ),
    )
    nutrients = budget.run(
        session,
        select(IngredientNutrient).where(IngredientNutrient.organization_id == org_id),
    )
    valued = {
        row.ingredient_version_id
        for row in nutrients
        if row.value is not None
    }
    valid = sum(1 for row in versions if row.id in valued)
    cover = coverage(valid, len(versions))
    return _indicator("nutrition_coverage", cover, cover)


def _compliance(session: Session, org_id: UUID, filters: ReportFilters, budget: QueryBudget, allowed: bool):
    if not allowed:
        return _indicator("compliance_coverage", unavailable("permissao_negada"))
    dossiers = budget.run(
        session,
        select(LabelingDossier).where(LabelingDossier.organization_id == org_id),
    )
    if filters.compliance_status:
        dossiers = [row for row in dossiers if row.status == filters.compliance_status]
    versions = budget.run(
        session,
        select(LabelingDossierVersion).where(LabelingDossierVersion.organization_id == org_id),
    )
    assessments = budget.run(
        session,
        select(LabelingAssessment).where(LabelingAssessment.organization_id == org_id),
    )
    assessed_versions = {row.labeling_dossier_version_id for row in assessments}
    assessed = {row.labeling_dossier_id for row in versions if row.id in assessed_versions}
    cover = coverage(len(assessed), len(dossiers))
    return _indicator("compliance_coverage", {**cover, "by_status": _count_status(dossiers)}, cover)


def _count_status(rows) -> dict:
    counts = defaultdict(int)
    for row in rows:
        counts[row.status] += 1
    return dict(counts)


def _data_coverage(parts: list[dict]) -> dict:
    valid = 0
    universe = 0
    used = 0
    for part in parts:
        cover = part.get("coverage") or {}
        if cover.get("universe"):
            valid += int(cover["valid_count"])
            universe += int(cover["universe"])
            used += 1
    if used == 0:
        result = coverage(0, 0)
    else:
        result = coverage(valid, universe)
    return _indicator("data_coverage", result, result)


def _occurrences(session: Session, org_id: UUID, orders: list[ProductionOrder], budget: QueryBudget) -> dict:
    if not orders:
        return _indicator("blocking_occurrences", unavailable("conjunto_vazio"), coverage(0, 0))
    rows = budget.run(
        session,
        select(ProductionOccurrence).where(
            ProductionOccurrence.organization_id == org_id,
            ProductionOccurrence.production_order_id.in_([item.id for item in orders]),
        ),
    )
    blocking = [row for row in rows if row.status == "open" and row.is_blocking]
    if not rows:
        return _indicator("blocking_occurrences", unavailable("ocorrencia_ausente"), coverage(0, len(orders)))
    return _indicator(
        "blocking_occurrences",
        present(len(blocking), unit="count") if blocking else known_zero(),
        coverage(len(rows), len(orders)),
    )


def _adherence(planned: dict, actual: dict, orders: list[ProductionOrder]) -> dict:
    if planned.get("status") != "available" or actual.get("status") != "available":
        return _indicator("quantity_adherence", unavailable("par_quantidade_ausente"), coverage(0, len(orders)))
    value = ratio_percent(Decimal(actual["value"]), Decimal(planned["value"]))
    if value is None:
        return _indicator("quantity_adherence", unavailable("denominador_invalido"))
    return _indicator("quantity_adherence", present(value, unit="percent"), planned.get("coverage"))


def _plans(session: Session, org_id: UUID, orders: list[ProductionOrder], budget: QueryBudget) -> dict:
    plans = budget.run(session, select(ProductionPlan).where(ProductionPlan.organization_id == org_id))
    linked = sum(1 for order in orders if order.plan_id)
    return {
        "plans": len(plans),
        "orders_with_plan": linked,
        "orders_without_plan": len(orders) - linked,
    }


def _trace_rows(
    session: Session,
    org_id: UUID,
    orders: list[ProductionOrder],
    budget: QueryBudget,
    filters: ReportFilters,
) -> list[dict]:
    if not orders:
        return []
    ids = [item.id for item in orders]
    events = budget.run(
        session,
        select(ProductionEvent).where(
            ProductionEvent.organization_id == org_id,
            ProductionEvent.order_id.in_(ids),
        ),
    )
    issues = budget.run(
        session,
        select(ProductionSheetIssue).where(
            ProductionSheetIssue.organization_id == org_id,
            ProductionSheetIssue.production_order_id.in_(ids),
        ),
    )
    steps = budget.run(
        session,
        select(ProductionStepExecution).where(
            ProductionStepExecution.organization_id == org_id,
            ProductionStepExecution.production_order_id.in_(ids),
        ),
    )
    rows = []
    for order in orders:
        rows.append(
            {
                "entity": "production_order",
                "id": str(order.id),
                "status": order.status,
                "hash": order.snapshot_hash,
                "at": order.created_at.isoformat(),
                "include": "ancora_no_periodo",
            }
        )
    for event in events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        rows.append(
            {
                "entity": "production_event",
                "id": str(event.id),
                "status": event.event_type,
                "hash": None,
                "at": event.occurred_at.isoformat(),
                "actor": str(event.actor_user_id) if event.actor_user_id else None,
                "correlation": str(event.correlation_id) if event.correlation_id else payload.get("correlation_id"),
                "causation": str(event.causation_event_id) if event.causation_event_id else None,
                "include": "evento_da_ordem",
            }
        )
    for issue in issues:
        rows.append(
            {
                "entity": "production_sheet_issue",
                "id": str(issue.id),
                "hash": getattr(issue, "payload_sha256", None),
                "at": issue.issued_at.isoformat(),
                "include": "emissao",
            }
        )
    timed = [row for row in steps if row.started_at and row.ended_at]
    coverage_ok = len(timed) >= 3 and len(timed) == len(steps)
    if coverage_ok:
        for step in timed:
            rows.append(
                {
                    "entity": "production_step_execution",
                    "id": str(step.id),
                    "duration_seconds": int((step.ended_at - step.started_at).total_seconds()),
                    "include": "tempo_com_cobertura",
                }
            )
    rows.sort(key=lambda item: item.get("at") or "")
    if filters.cursor:
        rows = [row for row in rows if row.get("id", "") > filters.cursor]
    return rows[: filters.limit]


def _quality_gaps(
    session: Session,
    org_id: UUID,
    orders: list[ProductionOrder],
    yields: list[ProductionYieldMeasurement],
    budget: QueryBudget,
) -> list[dict]:
    ingredients = budget.run(
        session,
        select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.status == "active"),
    )
    items = budget.run(session, select(SupplierItem).where(SupplierItem.organization_id == org_id))
    prices = budget.run(session, select(SupplierItemPrice))
    priced = {item.ingredient_id for item in items if any(price.supplier_item_id == item.id for price in prices)}
    gaps = []
    for ingredient in ingredients:
        if ingredient.id not in priced:
            gaps.append({"domain": "ingredient_price", "id": str(ingredient.id), "reason": "sem_preco_vigente"})
    closed = [item for item in orders if item.status in COMPLETED_STATUSES + SHORT_CLOSED_STATUSES]
    yielded = {row.production_order_id for row in yields}
    for order in closed:
        if order.id not in yielded:
            gaps.append({"domain": "order_yield", "id": str(order.id), "reason": "ordem_sem_rendimento"})
    calcs = budget.run(session, select(CostingCalculation).where(CostingCalculation.organization_id == org_id))
    for calc in calcs:
        if calc.completeness != "complete":
            gaps.append({"domain": "costing", "id": str(calc.id), "reason": "custo_parcial"})
    return gaps


def execute_report(
    session: Session,
    principal: Principal,
    report_code: str,
    filters: ReportFilters,
    *,
    persist_coverage: bool = False,
) -> dict:
    spec = REPORTS.get(report_code)
    if spec is None:
        raise ValidationError("relatorio_desconhecido")
    require_permission(principal, spec.permission)
    if report_code == "inventory":
        return _execute_inventory(session, principal, filters)
    org_id = principal.selected.organization_id
    budget = QueryBudget()
    started = perf_counter()
    cutoff = datetime.now(UTC)
    orders = _orders(session, org_id, filters, budget)
    order_ids = [item.id for item in orders]
    yields = (
        budget.run(
            session,
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.organization_id == org_id,
                ProductionYieldMeasurement.production_order_id.in_(order_ids),
            ),
        )
        if order_ids
        else []
    )
    indicators = []
    tables = []
    gaps = []
    can_cost = spec.permission == PERMISSION_REPORTING_COSTING_READ or (
        PERMISSION_REPORTING_COSTING_READ in principal.permissions and report_code == "executive"
    )
    can_price = spec.permission == PERMISSION_REPORTING_PRICING_READ or (
        PERMISSION_REPORTING_PRICING_READ in principal.permissions and report_code == "executive"
    )
    can_compliance = spec.permission == PERMISSION_REPORTING_COMPLIANCE_READ or (
        PERMISSION_REPORTING_COMPLIANCE_READ in principal.permissions and report_code == "executive"
    )
    if report_code in {"executive", "production"}:
        indicators.append(_orders_by_status(orders))
        planned, actual = _quantity_block(orders, yields)
        indicators.extend([planned, actual])
        indicators.append(_adherence(planned, actual, orders))
        normal, short = _completion_rates(orders)
        indicators.extend([normal, short])
        tables.append({"code": "orders", "rows": [
            {
                "id": str(order.id),
                "public_code": order.public_code,
                "status": order.status,
                "group": _status_group(order.status),
                "target_quantity": format(order.target_quantity, "f"),
                "target_mode": order.target_mode,
                "include": "ancora_no_periodo",
            }
            for order in orders[: filters.limit]
        ]})
        tables.append({"code": "plan_versus_orders", "rows": [_plans(session, org_id, orders, budget)]})
        indicators.append(_occurrences(session, org_id, orders, budget))
    if report_code in {"executive", "yield_losses", "production", "consumption"}:
        yld, loss, ycover = _yield_metrics(orders, yields)
        indicators.extend([yld, loss, ycover])
    if report_code in {"executive", "consumption"}:
        net, variance = _consumption(session, org_id, orders, filters, budget)
        indicators.extend([net, variance])
    if report_code in {"executive", "costing"} and (can_cost or report_code == "costing"):
        variance, unit_cost = _cost_metrics(session, org_id, filters, budget, can_cost or report_code == "costing")
        indicators.extend([variance, unit_cost])
    if report_code in {"executive", "pricing"} and (can_price or report_code == "pricing"):
        markup, gross, contrib = _price_metrics(session, org_id, filters, budget, can_price or report_code == "pricing")
        indicators.extend([markup, gross, contrib])
    price_cover = None
    nutrition = None
    compliance = None
    if report_code in {"executive", "data_quality", "consumption", "pricing"}:
        price_cover = _price_coverage(session, org_id, filters, budget)
        indicators.append(price_cover)
    if report_code in {"data_quality"}:
        nutrition = _nutrition_coverage(session, org_id, budget)
        indicators.append(nutrition)
        gaps = _quality_gaps(session, org_id, orders, yields, budget)
        tables.append({"code": "gaps", "rows": gaps[: filters.limit]})
    if report_code in {"executive", "compliance", "data_quality"}:
        compliance = _compliance(session, org_id, filters, budget, can_compliance or report_code in {"compliance", "data_quality"})
        indicators.append(compliance)
    if report_code in {"executive", "data_quality"}:
        indicators.append(_data_coverage([item for item in (price_cover, nutrition, compliance) if item]))
    if report_code == "traceability":
        tables.append({"code": "timeline", "rows": _trace_rows(session, org_id, orders, budget, filters)})
    if report_code == "pricing":
        tables.append({"code": "disclaimer", "rows": [{"note": "margem_estimada_nao_e_venda"}]})
    if report_code == "compliance":
        tables.append({"code": "disclaimer", "rows": [{"note": "contagem_nao_e_certificado"}]})
    available = [item for item in indicators if item.get("status") == "available"]
    completeness = "complete" if available and len(available) == len(indicators) else "partial" if available else "insufficient_data"
    payload = {
        "report_code": report_code,
        "report_version": REPORT_VERSION,
        "query_version": QUERY_VERSION,
        "metrics_version": METRICS_VERSION,
        "filters": filters.as_dict(),
        "timezone": filters.timezone,
        "period_start": filters.period_start.isoformat(),
        "period_end": filters.period_end.isoformat(),
        "data_cutoff_at": cutoff.isoformat(),
        "completeness": completeness,
        "indicators": indicators,
        "tables": tables,
        "gaps": gaps,
        "impossible": [
            "faturamento",
            "vendas",
            "lucro_liquido",
            "giro_de_estoque",
            "ruptura",
        ],
        "query_count": budget.count,
        "not_realtime": True,
    }
    payload["content_hash"] = _hash_payload(payload)
    payload["duration_ms"] = int((perf_counter() - started) * 1000)
    if persist_coverage:
        payload["_coverage_rows"] = [
            {
                "domain": item["code"],
                "universe": (item.get("coverage") or {}).get("universe") or 0,
                "valid_count": (item.get("coverage") or {}).get("valid_count") or 0,
                "missing_count": (item.get("coverage") or {}).get("missing_count") or 0,
                "reason": item.get("reason") or "cobertura",
            }
            for item in indicators
            if item.get("coverage")
        ]
    return payload


def drill_down(
    session: Session,
    principal: Principal,
    report_code: str,
    metric_code: str,
    filters: ReportFilters,
) -> dict:
    spec = REPORTS.get(report_code)
    if spec is None:
        raise ValidationError("relatorio_desconhecido")
    metric = METRICS.get(metric_code)
    if metric is None:
        raise ValidationError("metrica_desconhecida")
    require_permission(principal, spec.permission)
    payload = execute_report(session, principal, report_code, filters)
    rows = []
    for table in payload["tables"]:
        rows.extend(table.get("rows") or [])
    if metric.drill_down == "production_order":
        rows = [row for row in payload["tables"][0]["rows"]] if payload["tables"] else []
    total = None
    indicator = next((item for item in payload["indicators"] if item["code"] == metric_code), None)
    if indicator and indicator.get("status") == "available" and metric.unit == "count":
        reconstructed = len(rows)
        total = reconstructed
        if indicator.get("by_group") is None and int(Decimal(indicator["value"])) != reconstructed:
            raise ValidationError("conjunto_indisponivel")
    return {
        "metric": metric_code,
        "indicator": indicator,
        "rows": rows[: filters.limit],
        "next_cursor": rows[filters.limit]["id"] if len(rows) > filters.limit and "id" in rows[filters.limit] else None,
        "reconciled": total is None or str(total) == str(indicator.get("value")),
    }


def _execute_inventory(session: Session, principal: Principal, filters: ReportFilters) -> dict:
    require_permission(principal, PERMISSION_REPORTING_INVENTORY_READ)
    org_id = principal.selected.organization_id
    budget = QueryBudget()
    started = perf_counter()
    cutoff = datetime.now(UTC)
    balances = budget.run(session, select(InventoryBalance).where(InventoryBalance.organization_id == org_id))
    lots = budget.run(session, select(InventoryLot).where(InventoryLot.organization_id == org_id))
    items = budget.run(session, select(InventoryItem).where(InventoryItem.organization_id == org_id))
    movements = budget.run(session, select(InventoryMovement).where(InventoryMovement.organization_id == org_id))
    orders = budget.run(
        session,
        select(ProcurementOrder).where(
            ProcurementOrder.organization_id == org_id,
            ProcurementOrder.status.in_(("issued", "partially_received")),
        ),
    )
    requisitions = budget.run(
        session, select(ProcurementRequisition).where(ProcurementRequisition.organization_id == org_id)
    )
    postings = budget.run(
        session, select(InventoryConsumptionPosting).where(InventoryConsumptionPosting.organization_id == org_id)
    )
    suggestion = session.scalar(
        select(InventoryReplenishmentSuggestion)
        .where(InventoryReplenishmentSuggestion.organization_id == org_id)
        .order_by(InventoryReplenishmentSuggestion.created_at.desc())
    )
    budget.count += 1
    suggestion_items = (
        budget.run(
            session,
            select(InventoryReplenishmentItem).where(
                InventoryReplenishmentItem.inventory_replenishment_suggestion_id == suggestion.id
            ),
        )
        if suggestion
        else []
    )
    units = {row.unit_code for row in balances}
    if len(units) > 1:
        physical = unavailable("unidade_mista")
        available = unavailable("unidade_mista")
        reserved = unavailable("unidade_mista")
    elif not balances:
        physical = unavailable("sem_saldo_projetado")
        available = unavailable("sem_saldo_projetado")
        reserved = unavailable("sem_saldo_projetado")
    else:
        phys = sum((Decimal(row.physical_quantity) for row in balances), ZERO)
        res = sum((Decimal(row.reserved_quantity) for row in balances), ZERO)
        unit = next(iter(units))
        physical = {**present(phys, unit=unit), "code": "physical_on_hand"}
        reserved = {**present(res, unit=unit), "code": "reserved_quantity"}
        available = {**present(phys - res, unit=unit), "code": "available_quantity"}
    physical.setdefault("code", "physical_on_hand")
    reserved.setdefault("code", "reserved_quantity")
    available.setdefault("code", "available_quantity")
    today = datetime.now(UTC).date()
    expiring = [
        lot
        for lot in lots
        if lot.expires_on is not None and lot.status == "available" and lot.expires_on >= today and (lot.expires_on - today).days <= 7
    ]
    blocked = [lot for lot in lots if lot.status != "available"]
    expiring_ind = {**present(len(expiring), unit="count"), "code": "expiring_lots"}
    blocked_ind = {**present(len(blocked), unit="count"), "code": "blocked_lots"}
    if not suggestion_items:
        replenish = {**unavailable("sugestao_ausente"), "code": "replenishment_need"}
    else:
        need = sum(1 for item in suggestion_items if Decimal(item.suggested_quantity) > ZERO)
        replenish = {**present(need, unit="count"), "code": "replenishment_need"}
    pending = [row for row in postings if row.status != "posted"]
    missing_reorder = [item for item in items if item.reorder_point is None]
    quality = {**present(len(pending) + len(missing_reorder), unit="count"), "code": "inventory_data_quality"}
    count_ind = {**unavailable("sem_inventario_no_periodo"), "code": "count_variance"}
    transit = {**unavailable("sem_pedido_emitido"), "code": "in_transit_quantity"} if not orders else {**present(len(orders), unit="count"), "code": "in_transit_quantity"}
    indicators = [physical, reserved, available, transit, expiring_ind, blocked_ind, count_ind, replenish, quality]
    tables = [
        {
            "code": "position",
            "rows": [
                {
                    "id": str(row.id),
                    "inventory_item_id": str(row.inventory_item_id),
                    "inventory_location_id": str(row.inventory_location_id),
                    "inventory_lot_id": str(row.inventory_lot_id),
                    "physical": format(Decimal(row.physical_quantity), "f"),
                    "reserved": format(Decimal(row.reserved_quantity), "f"),
                    "available": format(Decimal(row.physical_quantity) - Decimal(row.reserved_quantity), "f"),
                    "unit_code": row.unit_code,
                }
                for row in balances[: filters.limit]
            ],
        },
        {
            "code": "lots",
            "rows": [
                {
                    "id": str(lot.id),
                    "status": lot.status,
                    "expires_on": None if lot.expires_on is None else lot.expires_on.isoformat(),
                    "internal_lot_code": lot.internal_lot_code,
                }
                for lot in lots[: filters.limit]
            ],
        },
        {
            "code": "movements",
            "rows": [
                {
                    "id": str(row.id),
                    "movement_type": row.movement_type,
                    "quantity": format(row.canonical_quantity, "f"),
                    "origin_type": row.origin_type,
                }
                for row in movements[: filters.limit]
            ],
        },
        {
            "code": "requisitions",
            "rows": [
                {"id": str(row.id), "status": row.status, "public_code": row.public_code}
                for row in requisitions[: filters.limit]
            ],
        },
    ]
    available_count = [item for item in indicators if item.get("status") == "available"]
    completeness = (
        "complete"
        if available_count and len(available_count) == len(indicators)
        else "partial"
        if available_count
        else "insufficient_data"
    )
    payload = {
        "report_code": "inventory",
        "report_version": REPORT_VERSION,
        "query_version": QUERY_VERSION,
        "metrics_version": METRICS_VERSION,
        "filters": filters.as_dict(),
        "timezone": filters.timezone,
        "period_start": filters.period_start.isoformat(),
        "period_end": filters.period_end.isoformat(),
        "data_cutoff_at": cutoff.isoformat(),
        "completeness": completeness,
        "indicators": indicators,
        "tables": tables,
        "gaps": [{"domain": "inventory", "reason": "item_sem_ponto_reposicao", "id": str(item.id)} for item in missing_reorder],
        "impossible": ["valor_contabil_de_estoque", "custo_medio", "fifo", "lifo", "giro_de_estoque"],
        "query_count": budget.count,
        "not_realtime": True,
    }
    payload["content_hash"] = _hash_payload(payload)
    payload["duration_ms"] = int((perf_counter() - started) * 1000)
    return payload
