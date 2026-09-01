"""Séries de leitura para os gráficos do painel. Ausência não vira zero."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.models import CostingCalculation, CostingComponent, PracticedPrice
from app.modules.costing_pricing.presentation import infer_supply_mode
from app.modules.formula_lab.models import TechnicalProduct
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.inventory_procurement.models import InventoryBalance, InventoryItem, InventoryLot, InventoryMovement
from app.modules.inventory_procurement.operational_date import OPERATIONAL_TIMEZONE
from app.modules.production_execution.constants import (
    YIELD_GOOD_UNITS,
    YIELD_POST_BAKE_MASS,
    YIELD_REJECTED_UNITS,
    YIELD_SCRAP,
)
from app.modules.production_execution.models import ProductionYieldMeasurement
from app.modules.production_planning.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_READY,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SHORT_CLOSED,
    TARGET_MODE_MASS,
)
from app.modules.production_planning.models import ProductionOrder, ProductionPlan

_ZONE = ZoneInfo(OPERATIONAL_TIMEZONE)
PERIODS = ("today", "yesterday", "last_7_days")
_PERIODS = PERIODS
_SHIFT_LABEL = {
    "morning": "Manhã",
    "afternoon": "Tarde",
    "night": "Noite",
}
_STATUS_BUCKET = {
    "draft": "planned",
    "scheduled": "planned",
    ORDER_STATUS_RELEASED: "released",
    ORDER_STATUS_IN_WEIGHING: "running",
    ORDER_STATUS_READY: "running",
    ORDER_STATUS_IN_PROGRESS: "running",
    ORDER_STATUS_COMPLETED: "done",
    ORDER_STATUS_SHORT_CLOSED: "done",
    ORDER_STATUS_ON_HOLD: "blocked",
    ORDER_STATUS_CANCELLED: "blocked",
}
_BUCKET_LABEL = {
    "planned": "Planejada",
    "released": "Liberada",
    "running": "Em execução",
    "done": "Concluída",
    "blocked": "Bloqueada",
}


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _empty_chart(*, title: str, source: str, detail: str, href: str, action: str, unit: str | None = None) -> dict:
    return {
        "available": False,
        "coverage": "empty",
        "title": title,
        "unit": unit,
        "source": source,
        "empty_title": detail,
        "empty_action": action,
        "empty_href": href,
        "series": [],
        "unit_groups": [],
    }


def period_bounds(today: date, period: str) -> tuple[date, date, str]:
    code = period if period in _PERIODS else "today"
    if code == "yesterday":
        return today - timedelta(days=1), today, "Ontem"
    if code == "last_7_days":
        return today - timedelta(days=6), today + timedelta(days=1), "Últimos 7 dias"
    return today, today + timedelta(days=1), "Hoje"


def order_in_period(start: datetime, end: datetime):
    """Ordem entra pelo dia do plano; sem plano, pelo início planejado. Fim exclusivo."""
    start_day = start.date()
    end_day = end.date()
    return or_(
        (ProductionPlan.operational_date.is_not(None))
        & (ProductionPlan.operational_date >= start_day)
        & (ProductionPlan.operational_date < end_day),
        (ProductionPlan.operational_date.is_(None))
        & (ProductionOrder.planned_start_at.is_not(None))
        & (ProductionOrder.planned_start_at >= start)
        & (ProductionOrder.planned_start_at < end),
    )


def _dt(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=_ZONE)


def _chart_frame(*, title: str, source: str, unit: str | None, coverage: str, series: list) -> dict:
    return {
        "available": bool(series),
        "coverage": coverage if series else "empty",
        "title": title,
        "unit": unit,
        "source": source,
        "series": series,
        "empty_title": None if series else "Sem informação suficiente para desenhar este gráfico.",
        "empty_action": None,
        "empty_href": None,
        "unit_groups": [],
    }


def build_charts(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID | None,
    establishment_name: str | None,
    today: date,
    period: str,
    can_orders: bool,
    can_stock: bool,
    can_economy: bool,
) -> dict:
    start_day, end_day, period_label = period_bounds(today, period)
    start = _dt(start_day)
    end = _dt(end_day)
    now = datetime.now(tz=_ZONE)
    meta = {
        "period": period if period in _PERIODS else "today",
        "period_label": period_label,
        "period_start": start_day.isoformat(),
        "period_end": (end_day - timedelta(days=1)).isoformat(),
        "timezone": OPERATIONAL_TIMEZONE,
        "establishment": establishment_name,
        "as_of": today.isoformat(),
        "generated_at": now.isoformat(),
    }
    production = (
        _production_chart(session, organization_id, establishment_id, start, end)
        if can_orders
        else _empty_chart(
            title="Produção planejada e realizada",
            source="Ordens de produção",
            detail="Sem permissão para ler a produção.",
            href="/fluxo",
            action="Abrir fluxo produtivo",
        )
    )
    movements = (
        _movement_chart(session, organization_id, start, end, start_day, end_day)
        if can_stock
        else _empty_chart(
            title="Entradas e saídas",
            source="Movimentações de estoque",
            detail="Sem permissão para ler o estoque.",
            href="/fluxo",
            action="Abrir fluxo produtivo",
        )
    )
    stock = (
        _stock_chart(session, organization_id, establishment_id, today)
        if can_stock
        else _empty_chart(
            title="Estoque crítico",
            source="Saldos e pontos de reposição",
            detail="Sem permissão para ler o estoque.",
            href="/fluxo",
            action="Abrir fluxo produtivo",
        )
    )
    agenda = (
        _agenda_chart(session, organization_id, establishment_id, start, end, today)
        if can_orders
        else _empty_chart(
            title="Agenda e situação das ordens",
            source="Ordens de produção",
            detail="Sem permissão para ler as ordens.",
            href="/fluxo",
            action="Abrir fluxo produtivo",
        )
    )
    costs = prices = None
    if can_economy:
        costs = _cost_chart(session, organization_id)
        prices = _price_chart(session, organization_id, start)
    return {
        "meta": meta,
        "production": production,
        "movements": movements,
        "stock": stock,
        "agenda": agenda,
        "costs": costs,
        "prices": prices,
    }


def _production_chart(session: Session, organization_id: UUID, establishment_id: UUID | None, start: datetime, end: datetime) -> dict:
    title = "Produção planejada e realizada"
    source = "Ordens de produção e medições de rendimento"
    stmt = (
        select(ProductionOrder, TechnicalProduct.display_name, ProductionPlan.operational_date)
        .join(
            TechnicalProduct,
            (TechnicalProduct.id == ProductionOrder.technical_product_id)
            & (TechnicalProduct.organization_id == ProductionOrder.organization_id),
        )
        .outerjoin(
            ProductionPlan,
            (ProductionPlan.id == ProductionOrder.plan_id)
            & (ProductionPlan.organization_id == ProductionOrder.organization_id),
        )
        .where(
            ProductionOrder.organization_id == organization_id,
            ProductionOrder.status != ORDER_STATUS_CANCELLED,
            order_in_period(start, end),
        )
        .order_by(TechnicalProduct.display_name, ProductionOrder.public_code)
        .limit(16)
    )
    if establishment_id is not None:
        stmt = stmt.where(ProductionOrder.establishment_id == establishment_id)
    rows = session.execute(stmt).all()
    if not rows:
        chart = _empty_chart(
            title=title,
            source=source,
            detail="Ainda não há ordem neste período. O gráfico aparece quando o plano do dia existir.",
            href="/planejamento",
            action="Abrir planejamento",
            unit="un",
        )
        return chart

    series: list[dict] = []
    for order, name, _day in rows:
        unit = "g" if order.target_mode == TARGET_MODE_MASS else "un"
        yield_type = YIELD_GOOD_UNITS if unit == "un" else YIELD_POST_BAKE_MASS
        actual = session.execute(
            select(func.sum(ProductionYieldMeasurement.quantity)).where(
                ProductionYieldMeasurement.organization_id == organization_id,
                ProductionYieldMeasurement.production_order_id == order.id,
                ProductionYieldMeasurement.measurement_type == yield_type,
                ProductionYieldMeasurement.reverses_id.is_(None),
            )
        ).scalar_one()
        loss = session.execute(
            select(func.sum(ProductionYieldMeasurement.quantity)).where(
                ProductionYieldMeasurement.organization_id == organization_id,
                ProductionYieldMeasurement.production_order_id == order.id,
                ProductionYieldMeasurement.measurement_type.in_((YIELD_SCRAP, YIELD_REJECTED_UNITS)),
                ProductionYieldMeasurement.reverses_id.is_(None),
            )
        ).scalar_one()
        actual_n = actual if actual and actual > 0 else None
        loss_n = loss if loss and loss > 0 else None
        if actual_n is None:
            flag = "sem_medicao"
            flag_label = "Sem medição"
        elif order.status in (ORDER_STATUS_COMPLETED, ORDER_STATUS_SHORT_CLOSED) and actual_n >= order.target_quantity:
            flag = "conforme"
            flag_label = "Conforme"
        elif loss_n:
            flag = "perda"
            flag_label = "Perda registrada"
        else:
            flag = "incompleto"
            flag_label = "Produção incompleta"
        series.append(
            {
                "label": f"{name} · {order.public_code}",
                "order_code": order.public_code,
                "href": f"/ordens/{order.id}",
                "unit": unit,
                "planned": _dec(order.target_quantity),
                "actual": _dec(actual_n),
                "loss": _dec(loss_n),
                "status": flag,
                "status_label": flag_label,
            }
        )
    units = {row["unit"] for row in series}
    unit = next(iter(units)) if len(units) == 1 else None
    groups = []
    if len(units) > 1:
        for code in sorted(units):
            groups.append({"unit": code, "series": [row for row in series if row["unit"] == code]})
    coverage = "partial" if any(row["actual"] is None for row in series) else "complete"
    payload = _chart_frame(title=title, source=source, unit=unit, coverage=coverage, series=series)
    payload["unit_groups"] = groups
    if len(units) > 1:
        payload["coverage_note"] = "Comparações ficam na unidade de cada ordem; eixos não misturam kg e unidade."
    return payload


def _movement_chart(
    session: Session,
    organization_id: UUID,
    start: datetime,
    end: datetime,
    start_day: date,
    end_day: date,
) -> dict:
    title = "Entradas e saídas"
    source = "Movimentações de estoque"
    kinds = (
        ("receipt", "Recebimentos"),
        ("production_consume", "Consumo produtivo"),
        ("adjust_plus", "Ajustes a mais"),
        ("adjust_minus", "Ajustes a menos"),
        ("waste", "Perdas"),
    )
    days: list[date] = []
    cursor = start_day
    last = end_day - timedelta(days=1)
    while cursor <= last:
        days.append(cursor)
        cursor += timedelta(days=1)

    unit_totals: dict[str, int] = {}
    raw: list[tuple[date, str, str, Decimal]] = []
    for day in days:
        day_start = _dt(day)
        day_end = day_start + timedelta(days=1)
        for code, _label in kinds:
            row = session.execute(
                select(
                    InventoryMovement.unit_code,
                    func.sum(InventoryMovement.canonical_quantity),
                ).where(
                    InventoryMovement.organization_id == organization_id,
                    InventoryMovement.movement_type == code,
                    InventoryMovement.created_at >= day_start,
                    InventoryMovement.created_at < day_end,
                ).group_by(InventoryMovement.unit_code)
            ).all()
            for unit_code, total in row:
                if total is None:
                    continue
                unit_totals[unit_code] = unit_totals.get(unit_code, 0) + 1
                raw.append((day, code, unit_code, total))

    if not raw:
        return _empty_chart(
            title=title,
            source=source,
            detail="Não há movimentação neste período. O gráfico aparece após recebimento, consumo, ajuste ou perda.",
            href="/componentes/estoque/movimentacoes",
            action="Abrir movimentações",
        )

    main_unit = max(unit_totals, key=unit_totals.get)
    series = []
    for day in days:
        point = {"label": day.isoformat(), "href": "/componentes/estoque/movimentacoes", "unit": main_unit}
        has_any = False
        for code, _label in kinds:
            match = next((total for d, c, u, total in raw if d == day and c == code and u == main_unit), None)
            point[code] = _dec(match) if match is not None else None
            if match is not None:
                has_any = True
        if has_any:
            series.append(point)
    extra = [u for u in unit_totals if u != main_unit]
    payload = _chart_frame(
        title=title,
        source=source,
        unit=main_unit,
        coverage="partial" if extra else "complete",
        series=series,
    )
    payload["keys"] = [{"code": code, "label": label} for code, label in kinds]
    if extra:
        payload["coverage_note"] = (
            f"Eixo em {main_unit}. Há movimentações em outras unidades, mostradas só na tabela."
        )
        payload["other_units"] = extra
    return payload


def _stock_chart(session: Session, organization_id: UUID, establishment_id: UUID | None, today: date) -> dict:
    title = "Estoque crítico"
    source = "Saldos físicos, ponto de reposição e validade de lote"
    available_qty = InventoryBalance.physical_quantity - InventoryBalance.reserved_quantity
    stmt = (
        select(
            Ingredient.display_name,
            InventoryItem.id,
            InventoryItem.unit_code,
            func.sum(available_qty),
            InventoryItem.safety_stock,
            InventoryItem.reorder_point,
        )
        .join(InventoryItem, InventoryItem.id == InventoryBalance.inventory_item_id)
        .join(
            Ingredient,
            (Ingredient.id == InventoryItem.ingredient_id) & (Ingredient.organization_id == InventoryItem.organization_id),
        )
        .where(
            InventoryBalance.organization_id == organization_id,
            InventoryItem.organization_id == organization_id,
            InventoryItem.status == "active",
        )
        .group_by(
            Ingredient.display_name,
            InventoryItem.id,
            InventoryItem.unit_code,
            InventoryItem.safety_stock,
            InventoryItem.reorder_point,
        )
        .limit(24)
    )
    if establishment_id is not None:
        stmt = stmt.where(InventoryBalance.establishment_id == establishment_id)
    rows = session.execute(stmt).all()
    if not rows:
        return _empty_chart(
            title=title,
            source=source,
            detail="Ainda não há saldo neste estabelecimento. O gráfico aparece depois do primeiro recebimento.",
            href="/componentes/estoque",
            action="Abrir estoque",
        )
    alert_until = today + timedelta(days=7)
    series = []
    for name, item_id, unit, qty, safety, reorder in rows:
        current = qty if qty is not None else Decimal("0")
        reference = safety if safety is not None else reorder
        near = session.execute(
            select(func.count(InventoryLot.id)).where(
                InventoryLot.organization_id == organization_id,
                InventoryLot.inventory_item_id == item_id,
                InventoryLot.expires_on.is_not(None),
                InventoryLot.expires_on <= alert_until,
                InventoryLot.status == "available",
            )
        ).scalar_one()
        if current <= 0:
            flag, flag_label = "ruptura", "Ruptura"
        elif reference is not None and current <= reference:
            flag, flag_label = "abaixo", "Abaixo do mínimo"
        elif near:
            flag, flag_label = "validade", "Validade próxima"
        else:
            continue
        series.append(
            {
                "label": name,
                "href": "/componentes/lotes",
                "unit": unit,
                "current": _dec(current),
                "reference": _dec(reference),
                "status": flag,
                "status_label": flag_label,
            }
        )
    series = series[:10]
    if not series:
        return _empty_chart(
            title=title,
            source=source,
            detail="Nenhum item crítico neste recorte. Ruptura, mínimo ou validade próxima apareceriam aqui.",
            href="/componentes/estoque",
            action="Abrir estoque",
        )
    return _chart_frame(title=title, source=source, unit=None, coverage="complete", series=series)


def _agenda_chart(
    session: Session,
    organization_id: UUID,
    establishment_id: UUID | None,
    start: datetime,
    end: datetime,
    today: date,
) -> dict:
    title = "Agenda e situação das ordens"
    source = "Ordens e planos do período operacional"
    stmt = (
        select(
            ProductionOrder,
            TechnicalProduct.display_name,
            ProductionPlan.shift,
            ProductionPlan.operational_date,
        )
        .join(
            TechnicalProduct,
            (TechnicalProduct.id == ProductionOrder.technical_product_id)
            & (TechnicalProduct.organization_id == ProductionOrder.organization_id),
        )
        .outerjoin(
            ProductionPlan,
            (ProductionPlan.id == ProductionOrder.plan_id)
            & (ProductionPlan.organization_id == ProductionOrder.organization_id),
        )
        .where(
            ProductionOrder.organization_id == organization_id,
            ProductionOrder.status != ORDER_STATUS_CANCELLED,
            order_in_period(start, end),
        )
        .order_by(ProductionOrder.planned_start_at.nulls_last(), ProductionOrder.public_code)
        .limit(20)
    )
    if establishment_id is not None:
        stmt = stmt.where(ProductionOrder.establishment_id == establishment_id)
    rows = session.execute(stmt).all()
    if not rows:
        return _empty_chart(
            title=title,
            source=source,
            detail="Não há ordem neste recorte. O gráfico aparece quando o plano do dia for publicado.",
            href="/producao",
            action="Abrir produção",
        )
    buckets = {key: 0 for key in _BUCKET_LABEL}
    series = []
    for order, name, shift, op_day in rows:
        bucket = _STATUS_BUCKET.get(order.status, "planned")
        buckets[bucket] += 1
        when = None
        if order.planned_start_at is not None:
            local = order.planned_start_at.astimezone(_ZONE)
            when = local.strftime("%H:%M")
        elif shift:
            when = _SHIFT_LABEL.get(shift, shift)
        elif op_day:
            when = op_day.isoformat()
        series.append(
            {
                "label": f"{order.public_code} · {name}",
                "href": f"/ordens/{order.id}",
                "status": bucket,
                "status_label": _BUCKET_LABEL[bucket],
                "when_label": when or "Horário não informado",
            }
        )
    payload = _chart_frame(title=title, source=source, unit="ordens", coverage="complete", series=series)
    payload["distribution"] = [
        {"code": code, "label": label, "count": buckets[code]} for code, label in _BUCKET_LABEL.items()
    ]
    payload["board_href"] = "/producao"
    payload["as_of"] = today.isoformat()
    return payload


def _cost_chart(session: Session, organization_id: UUID) -> dict:
    title = "Composição do custo"
    source = "Último cálculo de custeio por produto"
    calcs = session.execute(
        select(CostingCalculation)
        .where(
            CostingCalculation.organization_id == organization_id,
            CostingCalculation.technical_product_id.is_not(None),
        )
        .order_by(CostingCalculation.valuation_at.desc())
        .limit(80)
    ).scalars().all()
    latest: dict[UUID, CostingCalculation] = {}
    for calc in calcs:
        if calc.technical_product_id not in latest:
            latest[calc.technical_product_id] = calc
    if not latest:
        return _empty_chart(
            title=title,
            source=source,
            detail="Ainda não há cálculo de custo. O gráfico aparece depois da primeira formação.",
            href="/gestao/custos",
            action="Abrir custos e preços",
        )
    series = []
    for product_id, calc in list(latest.items())[:20]:
        product = session.get(TechnicalProduct, product_id)
        name = product.display_name if product is not None else "Produto"
        code = getattr(product, "code", None) if product is not None else None
        supply = getattr(product, "supply_mode", None) if product is not None else None
        inferred = infer_supply_mode(name, code)
        if supply == "purchased" or inferred == "purchased":
            supply = "purchased"
        elif supply not in {"produced", "mixed", "combo"}:
            supply = inferred or "produced"
        components = session.execute(
            select(CostingComponent.category, func.sum(CostingComponent.amount)).where(
                CostingComponent.organization_id == organization_id,
                CostingComponent.costing_calculation_id == calc.id,
            ).group_by(CostingComponent.category)
        ).all()
        by_cat = {cat: total for cat, total in components}
        merged_indirect = None
        for code in ("variable_indirect", "fixed_indirect"):
            if by_cat.get(code) is not None:
                merged_indirect = (merged_indirect or Decimal("0")) + by_cat[code]
        parts = {
            "ingredient": _dec(by_cat["ingredient"]) if "ingredient" in by_cat else None,
            "packaging": _dec(by_cat["packaging"]) if "packaging" in by_cat else None,
            "labor": _dec(by_cat["labor"]) if "labor" in by_cat else None,
            "energy": _dec(by_cat["energy"]) if "energy" in by_cat else None,
            "indirect": _dec(merged_indirect) if merged_indirect is not None else None,
        }
        if calc.completeness == "complete":
            completeness, completeness_label = "complete", "Custo completo"
        elif any(value is not None for value in parts.values()):
            completeness, completeness_label = "partial", "Custo parcial"
        else:
            completeness, completeness_label = "empty", "Sem informação"
        series.append(
            {
                "label": name,
                "href": f"/gestao/custos/formacao?produto={product_id}",
                "completeness": completeness,
                "completeness_label": completeness_label,
                "currency": calc.currency,
                "supply_mode": supply,
                "unit_cost": _dec(calc.sellable_unit_amount) if calc.sellable_unit_amount is not None else None,
                **parts,
            }
        )
    payload = _chart_frame(title=title, source=source, unit="BRL", coverage="partial", series=series)
    payload["keys"] = [
        {"code": "ingredient", "label": "Ingredientes"},
        {"code": "packaging", "label": "Embalagem"},
        {"code": "labor", "label": "Mão de obra"},
        {"code": "energy", "label": "Energia"},
        {"code": "indirect", "label": "Indiretos"},
    ]
    return payload


def _price_chart(session: Session, organization_id: UUID, now: datetime) -> dict:
    title = "Preço, custo e margem"
    source = "Preço praticado vigente e custo completo comparável"
    prices = session.execute(
        select(PracticedPrice, TechnicalProduct.display_name)
        .join(
            TechnicalProduct,
            (TechnicalProduct.id == PracticedPrice.technical_product_id)
            & (TechnicalProduct.organization_id == PracticedPrice.organization_id),
        )
        .where(
            PracticedPrice.organization_id == organization_id,
            PracticedPrice.status != "draft",
            PracticedPrice.valid_from <= now,
            or_(PracticedPrice.valid_to.is_(None), PracticedPrice.valid_to >= now),
        )
        .order_by(TechnicalProduct.display_name, PracticedPrice.valid_from.desc(), PracticedPrice.id)
    ).all()
    if not prices:
        return _empty_chart(
            title=title,
            source=source,
            detail="Não há preço vigente. O gráfico aparece depois de publicar um preço com base comercial.",
            href="/gestao/custos/precos",
            action="Abrir preços e histórico",
        )
    grouped: dict[UUID, list[tuple[PracticedPrice, str]]] = {}
    for price, name in prices:
        grouped.setdefault(price.technical_product_id, []).append((price, name))
    series = []
    for product_id, rows in grouped.items():
        name = rows[0][1]
        calc = session.execute(
            select(CostingCalculation)
            .where(
                CostingCalculation.organization_id == organization_id,
                CostingCalculation.technical_product_id == product_id,
                CostingCalculation.completeness == "complete",
                CostingCalculation.sellable_unit_amount.is_not(None),
            )
            .order_by(CostingCalculation.valuation_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if len(rows) > 1:
            series.append(
                {
                    "label": name,
                    "href": "/gestao/custos/precos",
                    "cost": None if calc is None else _dec(calc.sellable_unit_amount),
                    "price": None,
                    "currency": rows[0][0].currency,
                    "margin": None,
                    "margin_label": "Não calculável",
                    "basis": "conflito",
                    "status": "conflict",
                    "status_label": "Conflito de preços vigentes",
                }
            )
            continue
        price, name = rows[0]
        comparable = (
            calc is not None
            and price.sale_basis_quantity is not None
            and price.sale_basis_unit_id is not None
            and price.amount is not None
            and price.amount > 0
        )
        margin = None
        margin_label = "Não calculável"
        if comparable:
            ratio = (price.amount - calc.sellable_unit_amount) / price.amount
            margin = format(ratio * Decimal("100"), "f")
            margin_label = "Comparável"
        series.append(
            {
                "label": name,
                "href": "/gestao/custos/precos",
                "cost": None if calc is None else _dec(calc.sellable_unit_amount),
                "price": _dec(price.amount),
                "currency": price.currency,
                "margin": margin,
                "margin_label": margin_label,
                "basis": "informada" if price.sale_basis_quantity is not None else "ausente",
            }
        )
    return _chart_frame(title=title, source=source, unit="BRL", coverage="partial", series=series)
