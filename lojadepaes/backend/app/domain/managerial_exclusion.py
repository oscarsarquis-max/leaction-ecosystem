"""Retirada gerencial de testes. Não apaga cadastro, pagamento nem reserva."""

from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.date_requests import DateRequest
from app.models.managerial import ManagerialExclusion
from app.models.orders import Order

EXACT_TEST_NAMES = frozenset({"rastro", "oscar"})
EXCLUSION_REASON = "registro de teste identificado pelo proprietário"


def folded_name(value: str | None) -> str:
    raw = unicodedata.normalize("NFKD", value or "")
    ascii_name = "".join(char for char in raw if not unicodedata.combining(char))
    return " ".join(ascii_name.casefold().split())


def identity_class(name: str | None) -> str:
    """Nome inteiro igual a rastro ou oscar. Homônimo fica ambíguo e não sai."""
    folded = folded_name(name)
    if not folded:
        return "other"
    if folded in EXACT_TEST_NAMES:
        return "exact"
    tokens = set(folded.split())
    if tokens & EXACT_TEST_NAMES:
        return "ambiguous"
    return "other"


def active_exclusion_sets(session: Session) -> tuple[set[UUID], set[UUID]]:
    rows = session.scalars(
        select(ManagerialExclusion).where(ManagerialExclusion.reversed_at.is_(None))
    )
    orders: set[UUID] = set()
    dates: set[UUID] = set()
    for row in rows:
        if row.subject_type == "order":
            orders.add(row.subject_id)
        elif row.subject_type == "date_request":
            dates.add(row.subject_id)
    return orders, dates


def _active(session: Session, subject_type: str, subject_id: UUID) -> ManagerialExclusion | None:
    return session.scalar(
        select(ManagerialExclusion).where(
            ManagerialExclusion.subject_type == subject_type,
            ManagerialExclusion.subject_id == subject_id,
            ManagerialExclusion.reversed_at.is_(None),
        )
    )


def exclude_subject(
    session: Session,
    subject_type: str,
    subject_id: UUID,
    *,
    author_ref: str,
    reason: str = EXCLUSION_REASON,
) -> ManagerialExclusion:
    existing = _active(session, subject_type, subject_id)
    if existing is not None:
        return existing
    row = ManagerialExclusion(
        subject_type=subject_type,
        subject_id=subject_id,
        reason=reason[:280],
        author_ref=author_ref[:120],
    )
    session.add(row)
    session.flush()
    return row


def reverse_subject(
    session: Session,
    subject_type: str,
    subject_id: UUID,
    *,
    author_ref: str,
    reason: str,
) -> ManagerialExclusion | None:
    row = _active(session, subject_type, subject_id)
    if row is None:
        return None
    row.reversed_at = datetime.now(UTC)
    row.reversed_by = author_ref[:120]
    row.reverse_reason = reason[:280]
    session.flush()
    return row


def _mark_episode(session: Session, order: Order | None, request: DateRequest | None, author: str) -> None:
    if order is not None:
        exclude_subject(session, "order", order.id, author_ref=author)
        if order.source_date_request_id is not None:
            exclude_subject(session, "date_request", order.source_date_request_id, author_ref=author)
    if request is not None:
        exclude_subject(session, "date_request", request.id, author_ref=author)
        if request.converted_order_id is not None:
            exclude_subject(session, "order", request.converted_order_id, author_ref=author)


def classify_tests(session: Session) -> dict:
    orders = list(session.scalars(select(Order)))
    dates = list(session.scalars(select(DateRequest)))
    exact_orders = []
    exact_dates = []
    ambiguous = []
    for order in orders:
        kind = identity_class(order.customer_name)
        item = {
            "source": "order",
            "reference": order.public_reference,
            "status": order.status,
            "holds_capacity": bool(order.holds_capacity),
            "production_date": order.production_local_date.isoformat()
            if order.production_local_date
            else None,
        }
        if kind == "exact":
            exact_orders.append(order)
        elif kind == "ambiguous":
            ambiguous.append(item)
    exact_report = [
        {
            "source": "order",
            "reference": order.public_reference,
            "status": order.status,
            "holds_capacity": bool(order.holds_capacity),
            "production_date": order.production_local_date.isoformat()
            if order.production_local_date
            else None,
        }
        for order in exact_orders
    ]
    for request in dates:
        kind = identity_class(request.customer_name)
        item = {
            "source": "date_request",
            "reference": f"SD{str(request.id).replace('-', '')[:8].upper()}",
            "status": request.status,
            "holds_capacity": False,
            "production_date": request.desired_date.isoformat(),
        }
        if kind == "exact":
            exact_dates.append(request)
            exact_report.append(item)
        elif kind == "ambiguous":
            ambiguous.append(item)
    holding = [order.public_reference for order in exact_orders if order.holds_capacity]
    return {
        "exact_orders": exact_orders,
        "exact_dates": exact_dates,
        "exact": exact_report,
        "ambiguous": ambiguous,
        "still_holding_capacity": holding,
    }


def exclude_references(session: Session, references: list[str], *, author_ref: str) -> dict:
    """Marca referências já revistas. Não interpreta nome."""
    found = []
    missing = []
    for reference in references:
        order = session.scalar(select(Order).where(Order.public_reference == reference))
        if order is None:
            missing.append(reference)
            continue
        _mark_episode(session, order, None, author_ref)
        found.append(reference)
    session.flush()
    excluded_orders, excluded_dates = active_exclusion_sets(session)
    holding = [
        order.public_reference
        for order in session.scalars(select(Order))
        if order.id in excluded_orders and order.holds_capacity
    ]
    return {
        "marked": found,
        "missing": missing,
        "excluded_orders": len(excluded_orders),
        "still_holding_capacity": holding,
    }


def apply_identified_tests(session: Session, *, author_ref: str) -> dict:
    """Marca só nome exato. Não mexe em conta administrativa, pagamento nem reserva."""
    found = classify_tests(session)
    for order in found["exact_orders"]:
        _mark_episode(session, order, None, author_ref)
    for request in found["exact_dates"]:
        _mark_episode(session, None, request, author_ref)
    session.flush()
    excluded_orders, excluded_dates = active_exclusion_sets(session)
    holding = [
        order.public_reference
        for order in session.scalars(select(Order))
        if order.id in excluded_orders and order.holds_capacity
    ]
    return {
        "exact_orders": len(found["exact_orders"]),
        "exact_dates": len(found["exact_dates"]),
        "excluded_orders": len(excluded_orders),
        "excluded_dates": len(excluded_dates),
        "ambiguous": found["ambiguous"],
        "still_holding_capacity": holding,
        "exact": found["exact"],
    }
