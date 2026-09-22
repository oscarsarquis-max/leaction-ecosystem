"""Agrega o recorte operacional do dia. Somente leitura; ausência não vira zero."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.models import CostingCalculation, PracticedPrice
from app.modules.dashboard_today.charts import build_charts, order_in_period
from app.modules.fiscal_inbound.constants import (
    STATUS_AWAITING_CHECK,
    STATUS_AWAITING_MATCH,
    STATUS_AWAITING_XML,
    STATUS_DIVERGENT,
)
from app.modules.fiscal_inbound.models import FiscalInboundDocument
from app.modules.formula_lab.models import (
    Formulation,
    FormulationVersion,
    ProcessStep,
    TechnicalProduct,
)
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.identity_organization.authorization import (
    PERMISSION_COSTING_READ,
    PERMISSION_INVENTORY_READ,
    PERMISSION_LABELING_READ,
    PERMISSION_PRODUCT_READ,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_REPORTING_DASHBOARD_READ,
    AuthorizationError,
    Principal,
)
from app.modules.identity_organization.models import Establishment, Organization
from app.modules.inventory_procurement.models import InventoryBalance, InventoryItem, InventoryMovement
from app.modules.inventory_procurement.operational_date import (
    OPERATIONAL_TIMEZONE,
    inventory_operational_date,
)
from app.modules.labeling_compliance.models import LabelingDossier
from app.modules.production_planning.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_READY,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SHORT_CLOSED,
)
from app.modules.production_planning.models import ProductionOrder, ProductionPlan

_ZONE = ZoneInfo(OPERATIONAL_TIMEZONE)

_DASHBOARD_ANY = (
    PERMISSION_REPORTING_DASHBOARD_READ,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_INVENTORY_READ,
    PERMISSION_COSTING_READ,
    PERMISSION_PRODUCT_READ,
    PERMISSION_LABELING_READ,
)

_RUNNING = (
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
)
_IN_PROGRESS = (
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_ON_HOLD,
)
_DONE = (ORDER_STATUS_COMPLETED, ORDER_STATUS_SHORT_CLOSED)
_OPEN_ORDER = (
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_ON_HOLD,
    "draft",
    "scheduled",
)
_FISCAL_PENDING = (
    STATUS_AWAITING_XML,
    STATUS_AWAITING_MATCH,
    STATUS_AWAITING_CHECK,
    STATUS_DIVERGENT,
)
_LABEL_PENDING = ("draft", "in_review", "pending_review", "awaiting_review")
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def require_dashboard_access(principal: Principal) -> None:
    if not any(code in principal.permissions for code in _DASHBOARD_ANY):
        raise AuthorizationError("permissao_negada")


def _has(principal: Principal, code: str) -> bool:
    return code in principal.permissions


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _metric(
    *,
    available: bool,
    value: str | None = None,
    unit: str | None = None,
    source: str,
    period: str,
    empty: bool = False,
    reason: str | None = None,
) -> dict:
    payload: dict = {
        "available": available,
        "source": source,
        "period": period,
        "empty": empty,
    }
    if available:
        payload["value"] = value
        payload["unit"] = unit
    else:
        payload["reason"] = reason or "sem_informacao"
    return payload


def _count_metric(count: int, *, unit: str, source: str, period: str) -> dict:
    return _metric(
        available=True,
        value=str(count),
        unit=unit,
        source=source,
        period=period,
        empty=count == 0,
    )


def _qty_from_movements(
    session: Session,
    *,
    organization_id: UUID,
    movement_type: str,
    start: datetime,
    end: datetime,
    period: str,
    source: str,
) -> dict:
    filters = [
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.movement_type == movement_type,
        InventoryMovement.created_at >= start,
        InventoryMovement.created_at < end,
    ]
    stmt = select(
        func.count(InventoryMovement.id),
        func.sum(InventoryMovement.canonical_quantity),
        func.count(func.distinct(InventoryMovement.unit_code)),
        func.min(InventoryMovement.unit_code),
    ).where(*filters)
    row = session.execute(stmt).one()
    count, total, distinct_units, unit_code = row
    if not count:
        return _count_metric(0, unit="registros", source=source, period=period)
    if distinct_units and distinct_units > 1:
        return _metric(
            available=False,
            source=source,
            period=period,
            reason="unidades_misturadas",
        )
    return _metric(
        available=True,
        value=_dec(total or Decimal("0")),
        unit=unit_code or "un",
        source=source,
        period=period,
        empty=total is None or total == 0,
    )


def _scope_orders(query, organization_id: UUID, establishment_id: UUID | None):
    query = query.where(ProductionOrder.organization_id == organization_id)
    if establishment_id is not None:
        query = query.where(ProductionOrder.establishment_id == establishment_id)
    return query


def _completed_in_window(session: Session, organization_id: UUID, establishment_id: UUID | None, start: datetime, end: datetime) -> int:
    completed_at = func.coalesce(ProductionOrder.completed_at, ProductionOrder.short_closed_at)
    stmt = _scope_orders(
        select(func.count(ProductionOrder.id)).where(
            ProductionOrder.status.in_(_DONE),
            completed_at.is_not(None),
            completed_at >= start,
            completed_at < end,
        ),
        organization_id,
        establishment_id,
    )
    return int(session.execute(stmt).scalar_one() or 0)


def build_today(
    session: Session,
    principal: Principal,
    organization_id: UUID,
    establishment_id: UUID | None,
    period: str = "today",
) -> dict:
    require_dashboard_access(principal)
    today = inventory_operational_date()
    yesterday = today - timedelta(days=1)
    start_yesterday = datetime.combine(yesterday, time.min, tzinfo=_ZONE)
    start_today = datetime.combine(today, time.min, tzinfo=_ZONE)
    end_today = datetime.combine(today + timedelta(days=1), time.min, tzinfo=_ZONE)

    org = session.get(Organization, organization_id)
    org_name = org.display_name if org is not None else ""

    establishment_name = None
    resolved_est = establishment_id
    if resolved_est is not None:
        est = session.get(Establishment, resolved_est)
        if est is None or est.organization_id != organization_id:
            resolved_est = None
        else:
            establishment_name = est.display_name
    if resolved_est is None:
        first = session.execute(
            select(Establishment)
            .where(
                Establishment.organization_id == organization_id,
                Establishment.status == "active",
            )
            .order_by(Establishment.display_name)
            .limit(1)
        ).scalar_one_or_none()
        if first is not None:
            resolved_est = first.id
            establishment_name = first.display_name

    can_orders = _has(principal, PERMISSION_PRODUCTION_ORDER_READ)
    can_stock = _has(principal, PERMISSION_INVENTORY_READ)
    can_products = _has(principal, PERMISSION_PRODUCT_READ)
    can_labels = _has(principal, PERMISSION_LABELING_READ)
    can_economy = _has(principal, PERMISSION_COSTING_READ)

    yesterday_band = _yesterday_band(
        session,
        organization_id=organization_id,
        establishment_id=resolved_est,
        can_orders=can_orders,
        can_stock=can_stock,
        start=start_yesterday,
        end=start_today,
    )
    today_band = _today_band(
        session,
        organization_id=organization_id,
        establishment_id=resolved_est,
        can_orders=can_orders,
        can_stock=can_stock,
        today=today,
        start=start_today,
        end=end_today,
    )
    attentions = _attentions(
        session,
        organization_id=organization_id,
        establishment_id=resolved_est,
        can_stock=can_stock,
        can_products=can_products,
        can_labels=can_labels,
        can_economy=can_economy,
        can_orders=can_orders,
        start_today=start_today,
    )
    business = None
    if can_economy:
        business = _business(
            session,
            organization_id=organization_id,
            establishment_id=resolved_est,
            today=today,
            start_today=start_today,
        )

    headline = _headline(yesterday_band, today_band, attentions)
    charts = build_charts(
        session,
        organization_id=organization_id,
        establishment_id=resolved_est,
        establishment_name=establishment_name,
        today=today,
        period=period,
        can_orders=can_orders,
        can_stock=can_stock,
        can_economy=can_economy,
    )

    return {
        "operational_date": today.isoformat(),
        "timezone": OPERATIONAL_TIMEZONE,
        "organization": {"name": org_name},
        "establishment": None if not establishment_name else {"name": establishment_name},
        "headline": headline,
        "yesterday": yesterday_band,
        "today": today_band,
        "attentions": attentions,
        "business": business,
        "charts": charts,
        "permissions": {"economy": can_economy},
    }


def _yesterday_band(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID | None,
    can_orders: bool,
    can_stock: bool,
    start: datetime,
    end: datetime,
) -> dict:
    period = "Ontem"
    unavailable = _metric(available=False, source="Sem permissão neste recorte", period=period)
    produced = (
        _qty_from_movements(
            session,
            organization_id=organization_id,
            movement_type="production_return",
            start=start,
            end=end,
            period=period,
            source="Movimentações de estoque (retorno de produção)",
        )
        if can_stock
        else unavailable
    )
    received = (
        _qty_from_movements(
            session,
            organization_id=organization_id,
            movement_type="receipt",
            start=start,
            end=end,
            period=period,
            source="Movimentações de estoque (recebimento)",
        )
        if can_stock
        else unavailable
    )
    consumed = (
        _qty_from_movements(
            session,
            organization_id=organization_id,
            movement_type="production_consume",
            start=start,
            end=end,
            period=period,
            source="Movimentações de estoque (consumo de produção)",
        )
        if can_stock
        else unavailable
    )
    losses = (
        _qty_from_movements(
            session,
            organization_id=organization_id,
            movement_type="waste",
            start=start,
            end=end,
            period=period,
            source="Movimentações de estoque (perda)",
        )
        if can_stock
        else unavailable
    )
    if can_orders:
        completed = _completed_in_window(session, organization_id, establishment_id, start, end)
        orders_completed = _count_metric(
            completed,
            unit="ordens",
            source="Ordens de produção concluídas ou encerradas",
            period=period,
        )
    else:
        orders_completed = unavailable
    return {
        "period": {"start": start.date().isoformat(), "end": end.date().isoformat(), "label": period},
        "produced": produced,
        "received": received,
        "consumed": consumed,
        "losses": losses,
        "orders_completed": orders_completed,
    }


def _today_band(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID | None,
    can_orders: bool,
    can_stock: bool,
    today: date,
    start: datetime,
    end: datetime,
) -> dict:
    period = "Hoje"
    unavailable = _metric(available=False, source="Sem permissão neste recorte", period=period)
    if can_orders:
        planned_ids = select(ProductionPlan.id).where(
            ProductionPlan.organization_id == organization_id,
            ProductionPlan.operational_date == today,
        )
        if establishment_id is not None:
            planned_ids = planned_ids.where(ProductionPlan.establishment_id == establishment_id)
        planned = int(
            session.execute(
                _scope_orders(
                    select(func.count(ProductionOrder.id)).where(
                        or_(
                            ProductionOrder.plan_id.in_(planned_ids),
                            (ProductionOrder.planned_start_at >= start) & (ProductionOrder.planned_start_at < end),
                        ),
                        ProductionOrder.status != ORDER_STATUS_CANCELLED,
                    ),
                    organization_id,
                    establishment_id,
                )
            ).scalar_one()
            or 0
        )
        in_progress = int(
            session.execute(
                _scope_orders(
                    select(func.count(ProductionOrder.id))
                    .outerjoin(
                        ProductionPlan,
                        (ProductionPlan.id == ProductionOrder.plan_id)
                        & (ProductionPlan.organization_id == ProductionOrder.organization_id),
                    )
                    .where(
                        ProductionOrder.status.in_(_RUNNING),
                        order_in_period(start, end),
                    ),
                    organization_id,
                    establishment_id,
                )
            ).scalar_one()
            or 0
        )
        overdue = session.execute(
            _scope_orders(
                select(ProductionOrder.public_code, TechnicalProduct.display_name)
                .join(
                    TechnicalProduct,
                    (TechnicalProduct.id == ProductionOrder.technical_product_id)
                    & (TechnicalProduct.organization_id == ProductionOrder.organization_id),
                )
                .where(
                    ProductionOrder.status.in_(_OPEN_ORDER),
                    ProductionOrder.planned_end_at.is_not(None),
                    ProductionOrder.planned_end_at < start,
                )
                .order_by(ProductionOrder.planned_end_at)
                .limit(8),
                organization_id,
                establishment_id,
            )
        ).all()
        agenda_rows = session.execute(
            _scope_orders(
                select(ProductionOrder.public_code, TechnicalProduct.display_name, ProductionOrder.planned_start_at)
                .join(
                    TechnicalProduct,
                    (TechnicalProduct.id == ProductionOrder.technical_product_id)
                    & (TechnicalProduct.organization_id == ProductionOrder.organization_id),
                )
                .where(
                    ProductionOrder.status != ORDER_STATUS_CANCELLED,
                    or_(
                        (ProductionOrder.planned_start_at >= start) & (ProductionOrder.planned_start_at < end),
                        ProductionOrder.plan_id.in_(planned_ids),
                    ),
                )
                .order_by(ProductionOrder.planned_start_at.nulls_last())
                .limit(8),
                organization_id,
                establishment_id,
            )
        ).all()
        orders_planned = _count_metric(planned, unit="ordens", source="Ordens ligadas ao dia operacional", period=period)
        orders_in_progress = _count_metric(
            in_progress,
            unit="ordens",
            source="Ordens em pesagem, prontas ou em execução no recorte do dia",
            period=period,
        )
        agenda = [
            {
                "title": f"{code} · {name}",
                "when_label": "Programada para hoje",
                "href": "/ordens",
            }
            for code, name, _start in agenda_rows
        ]
        priority = [
            {
                "title": f"{code} · {name} atrasada",
                "severity": "high",
                "href": "/ordens",
            }
            for code, name in overdue
        ]
    else:
        orders_planned = unavailable
        orders_in_progress = unavailable
        agenda = []
        priority = []

    if can_stock:
        expected = int(
            session.execute(
                select(func.count(FiscalInboundDocument.id)).where(
                    FiscalInboundDocument.organization_id == organization_id,
                    FiscalInboundDocument.status.in_(_FISCAL_PENDING),
                    *(
                        [FiscalInboundDocument.establishment_id == establishment_id]
                        if establishment_id is not None
                        else []
                    ),
                )
            ).scalar_one()
            or 0
        )
        expected_receipts = _count_metric(
            expected,
            unit="entradas",
            source="Documentos fiscais ainda não recebidos",
            period=period,
        )
        if expected:
            priority.append(
                {
                    "title": "Entradas fiscais aguardando conferência",
                    "severity": "medium",
                    "href": "/gestao/compras/entradas",
                }
            )
    else:
        expected_receipts = unavailable

    return {
        "period": {"start": today.isoformat(), "end": today.isoformat(), "label": period},
        "orders_planned": orders_planned,
        "orders_in_progress": orders_in_progress,
        "expected_receipts": expected_receipts,
        "agenda": agenda,
        "priority_tasks": priority,
    }


def _attentions(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID | None,
    can_stock: bool,
    can_products: bool,
    can_labels: bool,
    can_economy: bool,
    can_orders: bool,
    start_today: datetime,
) -> list[dict]:
    items: list[dict] = []

    if can_stock:
        available_qty = InventoryBalance.physical_quantity - InventoryBalance.reserved_quantity
        threshold = func.coalesce(InventoryItem.safety_stock, InventoryItem.reorder_point)
        has_balance = session.execute(
            select(func.count(InventoryBalance.id)).where(InventoryBalance.organization_id == organization_id)
        ).scalar_one()
        if has_balance:
            critical = session.execute(
                select(Ingredient.display_name, func.sum(available_qty), InventoryItem.unit_code)
                .join(InventoryItem, InventoryItem.id == InventoryBalance.inventory_item_id)
                .join(
                    Ingredient,
                    (Ingredient.id == InventoryItem.ingredient_id)
                    & (Ingredient.organization_id == InventoryItem.organization_id),
                )
                .where(
                    InventoryBalance.organization_id == organization_id,
                    InventoryItem.organization_id == organization_id,
                    InventoryItem.status == "active",
                    *(
                        [InventoryBalance.establishment_id == establishment_id]
                        if establishment_id is not None
                        else []
                    ),
                )
                .group_by(Ingredient.display_name, InventoryItem.unit_code, threshold)
                .having(
                    or_(
                        (threshold.is_not(None)) & (func.sum(available_qty) <= threshold),
                        (threshold.is_(None)) & (func.sum(available_qty) <= 0),
                    )
                )
                .limit(12)
            ).all()
            if critical:
                names = ", ".join(name for name, _qty, _unit in critical[:4])
                items.append(
                    {
                        "code": "critical_stock",
                        "title": "Estoque crítico",
                        "detail": names,
                        "severity": "high",
                        "count": len(critical),
                        "href": "/componentes/estoque",
                    }
                )
        inbound = int(
            session.execute(
                select(func.count(FiscalInboundDocument.id)).where(
                    FiscalInboundDocument.organization_id == organization_id,
                    FiscalInboundDocument.status.in_(_FISCAL_PENDING),
                    *(
                        [FiscalInboundDocument.establishment_id == establishment_id]
                        if establishment_id is not None
                        else []
                    ),
                )
            ).scalar_one()
            or 0
        )
        if inbound:
            items.append(
                {
                    "code": "inbound_check",
                    "title": "Entradas aguardando conferência",
                    "detail": f"{inbound} documento(s) ainda sem recebimento concluído",
                    "severity": "high",
                    "count": inbound,
                    "href": "/gestao/compras/entradas",
                }
            )

    if can_products:
        produced = session.execute(
            select(TechnicalProduct.id, TechnicalProduct.display_name).where(
                TechnicalProduct.organization_id == organization_id,
                TechnicalProduct.status == "active",
                TechnicalProduct.supply_mode == "produced",
            )
        ).all()
        missing: list[str] = []
        for product_id, name in produced:
            has_recipe = session.execute(
                select(FormulationVersion.id)
                .join(Formulation, Formulation.id == FormulationVersion.formulation_id)
                .where(
                    Formulation.technical_product_id == product_id,
                    Formulation.organization_id == organization_id,
                    FormulationVersion.organization_id == organization_id,
                    FormulationVersion.status == "published",
                )
                .limit(1)
            ).scalar_one_or_none()
            if has_recipe is None:
                missing.append(name)
                continue
            has_steps = session.execute(
                select(ProcessStep.id)
                .join(FormulationVersion, FormulationVersion.id == ProcessStep.formulation_version_id)
                .join(Formulation, Formulation.id == FormulationVersion.formulation_id)
                .where(
                    Formulation.technical_product_id == product_id,
                    Formulation.organization_id == organization_id,
                    FormulationVersion.status == "published",
                    ProcessStep.organization_id == organization_id,
                )
                .limit(1)
            ).scalar_one_or_none()
            if has_steps is None:
                missing.append(name)
        if missing:
            items.append(
                {
                    "code": "product_without_prep",
                    "title": "Produtos sem receita ou preparo",
                    "detail": ", ".join(missing[:4]),
                    "severity": "medium",
                    "count": len(missing),
                    "href": "/produtos",
                }
            )

    if can_labels:
        pending_labels = int(
            session.execute(
                select(func.count(LabelingDossier.id)).where(
                    LabelingDossier.organization_id == organization_id,
                    LabelingDossier.status.in_(_LABEL_PENDING),
                )
            ).scalar_one()
            or 0
        )
        if pending_labels:
            items.append(
                {
                    "code": "labeling_pending",
                    "title": "Rotulagem pendente",
                    "detail": f"{pending_labels} dossiê(s) ainda em elaboração ou revisão",
                    "severity": "medium",
                    "count": pending_labels,
                    "href": "/conformidade",
                }
            )

    if can_economy:
        incomplete = int(
            session.execute(
                select(func.count(CostingCalculation.id)).where(
                    CostingCalculation.organization_id == organization_id,
                    CostingCalculation.completeness != "complete",
                )
            ).scalar_one()
            or 0
        )
        if incomplete:
            items.append(
                {
                    "code": "cost_incomplete",
                    "title": "Custos incompletos",
                    "detail": f"{incomplete} cálculo(s) sem cobertura completa",
                    "severity": "high",
                    "count": incomplete,
                    "href": "/gestao/custos",
                }
            )
        now = start_today
        prices = session.execute(
            select(PracticedPrice.sale_basis_quantity, PracticedPrice.sale_basis_unit_id).where(
                PracticedPrice.organization_id == organization_id,
                PracticedPrice.status != "draft",
                PracticedPrice.valid_from <= now,
                or_(PracticedPrice.valid_to.is_(None), PracticedPrice.valid_to >= now),
            )
        ).all()
        if prices:
            without_basis = sum(1 for qty, unit in prices if qty is None or unit is None)
            if without_basis:
                items.append(
                    {
                        "code": "price_without_basis",
                        "title": "Preços sem base comercial",
                        "detail": f"{without_basis} preço(s) vigente(s) sem quantidade e unidade de venda",
                        "severity": "high",
                        "count": without_basis,
                        "href": "/gestao/custos/precos",
                    }
                )

    if can_orders:
        done_yesterday = _completed_in_window(
            session,
            organization_id,
            establishment_id,
            start_today - timedelta(days=1),
            start_today,
        )
        planned_yesterday = int(
            session.execute(
                _scope_orders(
                    select(func.count(ProductionOrder.id))
                    .join(
                        ProductionPlan,
                        (ProductionPlan.id == ProductionOrder.plan_id)
                        & (ProductionPlan.organization_id == ProductionOrder.organization_id),
                    )
                    .where(
                        ProductionPlan.operational_date == (start_today.date() - timedelta(days=1)),
                        ProductionOrder.status != ORDER_STATUS_CANCELLED,
                    ),
                    organization_id,
                    establishment_id,
                )
            ).scalar_one()
            or 0
        )
        if planned_yesterday and done_yesterday != planned_yesterday:
            items.append(
                {
                    "code": "variance",
                    "title": "Desvio previsto × realizado",
                    "detail": (
                        f"Ontem: {planned_yesterday} "
                        f"{'ordem' if planned_yesterday == 1 else 'ordens'} no plano e "
                        f"{done_yesterday} "
                        f"{'concluída' if done_yesterday == 1 else 'concluídas'}"
                    ),
                    "severity": "medium",
                    "count": abs(planned_yesterday - done_yesterday),
                    "href": "/gestao/custos/variacao",
                }
            )

    items.sort(key=lambda row: _SEVERITY_RANK.get(row["severity"], 9))
    return items


def _business(
    session: Session,
    *,
    organization_id: UUID,
    establishment_id: UUID | None,
    today: date,
    start_today: datetime,
) -> dict:
    period = "Posição atual"
    complete = session.execute(
        select(CostingCalculation)
        .where(
            CostingCalculation.organization_id == organization_id,
            CostingCalculation.completeness == "complete",
            CostingCalculation.sellable_unit_amount.is_not(None),
        )
        .order_by(CostingCalculation.valuation_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    complete_products = int(
        session.execute(
            select(func.count(func.distinct(CostingCalculation.technical_product_id))).where(
                CostingCalculation.organization_id == organization_id,
                CostingCalculation.technical_product_id.is_not(None),
                CostingCalculation.completeness == "complete",
            )
        ).scalar_one()
        or 0
    )
    analyzed_products = int(
        session.execute(
            select(func.count(func.distinct(CostingCalculation.technical_product_id))).where(
                CostingCalculation.organization_id == organization_id,
                CostingCalculation.technical_product_id.is_not(None),
            )
        ).scalar_one()
        or 0
    )
    if analyzed_products == 0:
        cost_coverage = _metric(
            available=False,
            source="Último cálculo de custeio por produto",
            period=period,
            reason="sem_informacao",
        )
    else:
        analyzed_unit = (
            "de 1 produto analisado" if analyzed_products == 1 else f"de {analyzed_products} produtos analisados"
        )
        cost_coverage = _metric(
            available=True,
            value=str(complete_products),
            unit=analyzed_unit,
            source="Último cálculo de custeio por produto",
            period=period,
            empty=False,
        )
    if complete is None:
        known_cost = _metric(
            available=False,
            source="Cálculos de custeio com cobertura completa",
            period=period,
            reason="sem_informacao",
        )
    else:
        known_cost = _metric(
            available=True,
            value=_dec(complete.sellable_unit_amount),
            unit=f"{complete.currency} por unidade vendável",
            source="Último cálculo de custeio completo",
            period=period,
            empty=False,
        )

    now = start_today
    current_prices = int(
        session.execute(
            select(func.count(PracticedPrice.id)).where(
                PracticedPrice.organization_id == organization_id,
                PracticedPrice.status != "draft",
                PracticedPrice.valid_from <= now,
                or_(PracticedPrice.valid_to.is_(None), PracticedPrice.valid_to >= now),
            )
        ).scalar_one()
        or 0
    )
    prices_metric = _count_metric(
        current_prices,
        unit="preços",
        source="Preços praticados vigentes",
        period=period,
    )

    margin = None
    if complete is not None and complete.technical_product_id is not None:
        price = session.execute(
            select(PracticedPrice)
            .where(
                PracticedPrice.organization_id == organization_id,
                PracticedPrice.technical_product_id == complete.technical_product_id,
                PracticedPrice.status != "draft",
                PracticedPrice.sale_basis_quantity.is_not(None),
                PracticedPrice.sale_basis_unit_id.is_not(None),
                PracticedPrice.valid_from <= now,
                or_(PracticedPrice.valid_to.is_(None), PracticedPrice.valid_to >= now),
            )
            .order_by(PracticedPrice.valid_from.desc())
            .limit(1)
        ).scalar_one_or_none()
        if (
            price is not None
            and price.amount is not None
            and complete.sellable_unit_amount is not None
            and price.amount > 0
        ):
            ratio = (price.amount - complete.sellable_unit_amount) / price.amount
            margin = {
                "available": True,
                "value": format(ratio, "f"),
                "unit": "fração do preço",
                "source": "Preço vigente com base comercial e custo completo do mesmo produto",
                "period": period,
                "empty": False,
            }

    chart: list[dict] = []
    for offset in range(4, -1, -1):
        day = today - timedelta(days=offset)
        day_start = datetime.combine(day, time.min, tzinfo=_ZONE)
        day_end = day_start + timedelta(days=1)
        produced = _completed_in_window(session, organization_id, establishment_id, day_start, day_end)
        cost_row = session.execute(
            select(func.sum(CostingCalculation.total_amount)).where(
                CostingCalculation.organization_id == organization_id,
                CostingCalculation.completeness == "complete",
                CostingCalculation.valuation_at >= day_start,
                CostingCalculation.valuation_at < day_end,
            )
        ).scalar_one()
        chart.append(
            {
                "label": day.isoformat(),
                "produced": produced if produced else None,
                "cost": None if cost_row is None else format(cost_row, "f"),
                "variance": None,
            }
        )
    if not any(point["produced"] or point["cost"] for point in chart):
        chart = []

    return {
        "known_cost": known_cost,
        "cost_coverage": cost_coverage,
        "current_prices": prices_metric,
        "complete_calculations": complete_products,
        "margin": margin,
        "chart": chart,
    }


def _headline(yesterday: dict, today: dict, attentions: list[dict]) -> dict:
    top = attentions[0] if attentions else None
    y_done = yesterday["orders_completed"]
    t_run = today["orders_in_progress"]
    if top and top["severity"] == "high":
        return {
            "situation": "Há pendências que pedem decisão hoje.",
            "attention": top["title"],
            "next_action": top["title"],
            "next_href": top["href"],
        }
    if t_run.get("available") and not t_run.get("empty"):
        return {
            "situation": "A produção do dia já está em andamento.",
            "attention": top["title"] if top else "Acompanhe as ordens em curso.",
            "next_action": top["title"] if top else "Abrir produção",
            "next_href": top["href"] if top else "/producao",
        }
    if y_done.get("available") and not y_done.get("empty"):
        return {
            "situation": "O registro de ontem está disponível para começar o dia.",
            "attention": top["title"] if top else "Revise o que ficou pendente.",
            "next_action": top["title"] if top else "Abrir fluxo produtivo",
            "next_href": top["href"] if top else "/fluxo",
        }
    return {
        "situation": "Ainda não há movimento suficiente para um retrato do dia.",
        "attention": top["title"] if top else "Abra o fluxo produtivo e complete o que faltar.",
        "next_action": top["title"] if top else "Abrir fluxo produtivo",
        "next_href": top["href"] if top else "/fluxo",
    }
