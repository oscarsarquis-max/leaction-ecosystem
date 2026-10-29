"""Agenda de produção lida dos pedidos reais. Não grava e não inventa data."""

from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.attendance import date_request_reference
from app.domain.bakery_time import bakery_today
from app.domain.managerial_exclusion import active_exclusion_sets
from app.domain.order_board import (
    classify_payment,
    observed_financial_label,
    payment_attention_label,
    visible_label_for_order,
)
from app.models.date_requests import DateRequest
from app.models.enums import OrderStatus
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord

_OPEN = {
    OrderStatus.SUBMITTED.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
    OrderStatus.READY.value,
}


def _item_label(rows: list[OrderItem]) -> tuple[str, int]:
    parts = []
    total = 0
    for row in rows:
        total += int(row.quantity)
        name = (row.dough_name_snapshot or row.shape_name_snapshot or "pão").strip()
        parts.append(f"{row.quantity}× {name}")
    return (", ".join(parts) if parts else "composição no pedido"), total


def _entry(order: Order, items: list[OrderItem], records: list[PaymentRecord]) -> dict:
    bucket = classify_payment(order, records)
    label, quantity = _item_label(items)
    return {
        "id": str(order.id),
        "source": "order",
        "reference": order.public_reference,
        "customer_name": order.customer_name,
        "composition": label,
        "quantity": quantity,
        "stage": visible_label_for_order(order, bucket),
        "payment": observed_financial_label(bucket),
        "pending": payment_attention_label(order, bucket),
        "href": f"/admin/pedidos/{order.id}",
    }


def _blank(day: date) -> dict:
    return {
        "date": day.isoformat(),
        "orders": 0,
        "open_orders": 0,
        "historical_orders": 0,
        "pending_requests": 0,
        "bread_units": 0,
        "open": [],
        "historical": [],
        "pending": [],
        "cancelled": [],
    }


def production_agenda(session: Session, settings: Settings, year: int, month: int) -> dict:
    if month < 1 or month > 12:
        raise ValueError("mês inválido")
    today = bakery_today(settings)
    excluded_orders, excluded_dates = active_exclusion_sets(session)
    orders = [
        order
        for order in session.scalars(select(Order).where(Order.status != OrderStatus.DRAFT.value))
        if order.id not in excluded_orders
    ]
    dates = [
        row
        for row in session.scalars(select(DateRequest))
        if row.id not in excluded_dates and row.status != "converted" and row.status != "closed"
    ]
    ids = [order.id for order in orders]
    items: dict = {order.id: [] for order in orders}
    records: dict = {order.id: [] for order in orders}
    if ids:
        for row in session.scalars(select(OrderItem).where(OrderItem.order_id.in_(ids))):
            items.setdefault(row.order_id, []).append(row)
        for row in session.scalars(select(PaymentRecord).where(PaymentRecord.order_id.in_(ids))):
            records.setdefault(row.order_id, []).append(row)
    last_day = calendar.monthrange(year, month)[1]
    days = {date(year, month, day): _blank(date(year, month, day)) for day in range(1, last_day + 1)}
    undated = []

    def bucket_for(day: date | None) -> dict | None:
        if day is None:
            return None
        return days.get(day)

    for order in orders:
        entry = _entry(order, items.get(order.id, []), records.get(order.id, []))
        confirmed = order.production_local_date
        desired_only = confirmed is None and order.proposed_production_date is not None
        if order.status == OrderStatus.CANCELLED.value:
            target = bucket_for(confirmed or order.proposed_production_date)
            if target is None:
                continue
            target["cancelled"].append(entry)
            continue
        if desired_only and order.status == OrderStatus.SUBMITTED.value:
            target = bucket_for(order.proposed_production_date)
            pending = {
                **entry,
                "pending_kind": "solicitação pendente",
            }
            if target is None:
                undated.append(pending)
            else:
                target["pending"].append(pending)
                target["pending_requests"] += 1
            continue
        if confirmed is None:
            undated.append(entry)
            continue
        target = bucket_for(confirmed)
        if target is None:
            continue
        historical = order.status == OrderStatus.COMPLETED.value
        if historical:
            target["historical"].append(entry)
            target["historical_orders"] += 1
        elif order.status in _OPEN:
            target["open"].append(entry)
            target["open_orders"] += 1
        else:
            continue
        target["orders"] += 1
        target["bread_units"] += entry["quantity"]

    for request in dates:
        if request.status not in {"pending", "alternative_proposed", "awaiting_details"}:
            continue
        pending = {
            "id": str(request.id),
            "source": "date_request",
            "reference": date_request_reference(request.id),
            "customer_name": request.customer_name,
            "composition": "solicitação ainda aberta",
            "quantity": request.intended_quantity,
            "stage": "Aberto",
            "payment": "Sem cobrança",
            "pending": "solicitação pendente",
            "pending_kind": "solicitação pendente",
            "href": f"/admin/pedidos/solicitacao/{request.id}",
        }
        target = bucket_for(request.desired_date)
        if target is None:
            undated.append(pending)
            continue
        target["pending"].append(pending)
        target["pending_requests"] += 1

    return {
        "timezone": settings.bakery_timezone,
        "year": year,
        "month": month,
        "today": today.isoformat(),
        "days": [days[date(year, month, day)] for day in range(1, last_day + 1)],
        "undated": undated,
    }
