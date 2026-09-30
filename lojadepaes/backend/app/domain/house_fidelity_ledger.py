from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.capacity import utc_now
from app.domain.errors import ConfirmationError
from app.domain.house_fidelity import campaign_is_publicly_active, current_campaign, cycle_of
from app.domain.payments import net_confirmed_cents
from app.models.enums import FinancialStatus, OrderStatus
from app.models.house_fidelity import (
    HouseFidelityAdjustment,
    HouseFidelityCredit,
    HouseFidelityEvent,
)
from app.models.orders import Order
from app.models.payments import PaymentRecord

PARTIAL_REVIEW_REASON = (
    "estorno parcial: revisão administrativa pendente, sem decisão automática de carimbo"
)


def _payments(session: Session, order: Order) -> list[PaymentRecord]:
    return list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))


def _paid_at(records: list[PaymentRecord]) -> datetime | None:
    moments = [
        row.confirmed_at
        for row in records
        if row.financial_status == FinancialStatus.PAID.value and row.confirmed_at
    ]
    return min(moments) if moments else None


def bread_net_paid(order: Order, records: list[PaymentRecord]) -> int:
    net = net_confirmed_cents(records)
    if net is None:
        return 0
    freight = order.delivery_fee_cents or 0
    return max(net - freight, 0)


def order_is_redemption(order: Order) -> bool:
    return order.order_kind == "redemption" or order.fidelity_credit_id is not None


CLOSED_STATUSES = frozenset(
    {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    }
)


def closed_at(order: Order) -> datetime | None:
    """Aceite administrativo. Não é entrega: fulfilled_at continua só operacional."""
    if order.status == OrderStatus.CANCELLED.value:
        return None
    if order.status not in CLOSED_STATUSES:
        return None
    return order.confirmed_at


def purchase_during_campaign(order: Order, campaign) -> bool:
    if campaign.starts_at is None or order.created_at is None:
        return False
    return order.created_at >= campaign.starts_at


def can_qualify(order: Order, records: list[PaymentRecord]) -> bool:
    if not order.fidelity_opt_in or order.fidelity_account_id is None:
        return False
    if closed_at(order) is None:
        return False
    if order.status == OrderStatus.CANCELLED.value:
        return False
    if order.fidelity_qualifies is False:
        return False
    if order_is_redemption(order) and (order.total_cents or 0) <= (order.delivery_fee_cents or 0):
        return False
    return bread_net_paid(order, records) > 0


def _has_refund_signal(records: list[PaymentRecord]) -> bool:
    return any(
        row.financial_status
        in {FinancialStatus.REFUNDED.value, FinancialStatus.PARTIALLY_REFUNDED.value}
        or (row.amount_refunded_cents or 0) > 0
        for row in records
    )


def should_reverse(order: Order, records: list[PaymentRecord]) -> bool:
    if not order.fidelity_opt_in or order.fidelity_account_id is None:
        return False
    if order.status == OrderStatus.CANCELLED.value:
        return True
    return bread_net_paid(order, records) <= 0 and _has_refund_signal(records)


def needs_partial_review(order: Order, records: list[PaymentRecord]) -> bool:
    if not order.fidelity_opt_in or order.fidelity_account_id is None:
        return False
    if order.status == OrderStatus.CANCELLED.value:
        return False
    if not _has_refund_signal(records):
        return False
    return bread_net_paid(order, records) > 0


def _event(
    session: Session,
    campaign_id,
    order_id,
    kind: str,
) -> HouseFidelityEvent | None:
    return session.scalar(
        select(HouseFidelityEvent).where(
            HouseFidelityEvent.campaign_id == campaign_id,
            HouseFidelityEvent.order_id == order_id,
            HouseFidelityEvent.kind == kind,
        )
    )


def open_partial_review(
    session: Session, settings: Settings, campaign, order: Order
) -> HouseFidelityEvent:
    review = _event(session, campaign.id, order.id, "partial_review")
    if review is None:
        paid_at = _paid_at(_payments(session, order))
        moment = paid_at or closed_at(order) or utc_now()
        year, month = cycle_of(settings, moment)
        review = HouseFidelityEvent(
            campaign_id=campaign.id,
            account_id=order.fidelity_account_id,
            order_id=order.id,
            kind="partial_review",
            status="pending",
            cycle_year=year,
            cycle_month=month,
            eligible_at=utc_now(),
            reason=PARTIAL_REVIEW_REASON,
            actor_ref="system",
        )
        session.add(review)
        session.add(
            HouseFidelityAdjustment(
                campaign_id=campaign.id,
                account_id=order.fidelity_account_id,
                kind="partial_review_pending",
                reason=PARTIAL_REVIEW_REASON,
                actor_ref="system",
            )
        )
        session.flush()
        return review
    if review.status != "pending":
        review.status = "pending"
        review.reason = PARTIAL_REVIEW_REASON
        session.flush()
    return review


def pending_partial_reviews(session: Session, campaign_id) -> list[dict]:
    rows = list(
        session.scalars(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.campaign_id == campaign_id,
                HouseFidelityEvent.kind == "partial_review",
                HouseFidelityEvent.status == "pending",
            )
        )
    )
    items = []
    for row in rows:
        order = session.get(Order, row.order_id) if row.order_id else None
        items.append(
            {
                "id": str(row.id),
                "account_id": str(row.account_id),
                "order_id": str(row.order_id) if row.order_id else None,
                "order_reference": order.public_reference if order is not None else None,
                "reason": row.reason,
                "eligible_at": row.eligible_at.isoformat() if row.eligible_at else None,
            }
        )
    return items


def _lock_credit_row(session: Session, credit: HouseFidelityCredit) -> HouseFidelityCredit:
    return session.execute(
        select(HouseFidelityCredit).where(HouseFidelityCredit.id == credit.id).with_for_update()
    ).scalar_one()


def _sync_credits(
    session: Session,
    campaign_id,
    account_id,
    year: int,
    month: int,
    qualify_events: list[HouseFidelityEvent],
) -> None:
    needed = len(qualify_events) // 4
    existing = list(
        session.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.campaign_id == campaign_id,
                HouseFidelityCredit.account_id == account_id,
                HouseFidelityCredit.cycle_year == year,
                HouseFidelityCredit.cycle_month == month,
            )
        )
    )
    have = {row.group_index: row for row in existing}
    for index in range(needed):
        if index in have:
            continue
        source = qualify_events[(index + 1) * 4 - 1]
        session.add(
            HouseFidelityCredit(
                campaign_id=campaign_id,
                account_id=account_id,
                source_event_id=source.id,
                cycle_year=year,
                cycle_month=month,
                group_index=index,
                status="available",
            )
        )
    session.flush()


def reconcile_order(session: Session, settings: Settings, order: Order) -> None:
    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        return
    if order.fidelity_account_id is None or not order.fidelity_opt_in:
        return
    if not purchase_during_campaign(order, campaign):
        return
    records = _payments(session, order)
    qualify = _event(session, campaign.id, order.id, "qualify")
    if needs_partial_review(order, records):
        open_partial_review(session, settings, campaign, order)
        return
    if can_qualify(order, records):
        paid_at = _paid_at(records)
        eligible_at = max(stamp for stamp in (paid_at, closed_at(order)) if stamp is not None)
        year, month = cycle_of(settings, eligible_at)
        if qualify is None:
            qualify = HouseFidelityEvent(
                campaign_id=campaign.id,
                account_id=order.fidelity_account_id,
                order_id=order.id,
                kind="qualify",
                status="applied",
                cycle_year=year,
                cycle_month=month,
                eligible_at=eligible_at,
                reason="fechada e paga",
            )
            session.add(qualify)
            session.flush()
        elif qualify.status == "reversed":
            qualify.status = "applied"
            qualify.eligible_at = eligible_at
            qualify.cycle_year = year
            qualify.cycle_month = month
            session.flush()
        events = list(
            session.scalars(
                select(HouseFidelityEvent)
                .where(
                    HouseFidelityEvent.campaign_id == campaign.id,
                    HouseFidelityEvent.account_id == order.fidelity_account_id,
                    HouseFidelityEvent.kind == "qualify",
                    HouseFidelityEvent.status == "applied",
                    HouseFidelityEvent.cycle_year == year,
                    HouseFidelityEvent.cycle_month == month,
                )
                .order_by(HouseFidelityEvent.eligible_at, HouseFidelityEvent.created_at)
            )
        )
        _sync_credits(session, campaign.id, order.fidelity_account_id, year, month, events)
        return
    if qualify is not None and qualify.status == "applied" and should_reverse(order, records):
        reverse = session.scalar(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.campaign_id == campaign.id,
                HouseFidelityEvent.order_id == order.id,
                HouseFidelityEvent.kind == "reverse",
            )
        )
        if reverse is None:
            session.add(
                HouseFidelityEvent(
                    campaign_id=campaign.id,
                    account_id=order.fidelity_account_id,
                    order_id=order.id,
                    kind="reverse",
                    status="applied",
                    cycle_year=qualify.cycle_year,
                    cycle_month=qualify.cycle_month,
                    eligible_at=utc_now(),
                    reason="cancelamento ou estorno da compra qualificadora",
                )
            )
        qualify.status = "reversed"
        session.flush()
        events = list(
            session.scalars(
                select(HouseFidelityEvent)
                .where(
                    HouseFidelityEvent.campaign_id == campaign.id,
                    HouseFidelityEvent.account_id == order.fidelity_account_id,
                    HouseFidelityEvent.kind == "qualify",
                    HouseFidelityEvent.status == "applied",
                    HouseFidelityEvent.cycle_year == qualify.cycle_year,
                    HouseFidelityEvent.cycle_month == qualify.cycle_month,
                )
                .order_by(HouseFidelityEvent.eligible_at, HouseFidelityEvent.created_at)
            )
        )
        needed = len(events) // 4
        credits = list(
            session.scalars(
                select(HouseFidelityCredit).where(
                    HouseFidelityCredit.campaign_id == campaign.id,
                    HouseFidelityCredit.account_id == order.fidelity_account_id,
                    HouseFidelityCredit.cycle_year == qualify.cycle_year,
                    HouseFidelityCredit.cycle_month == qualify.cycle_month,
                )
            )
        )
        extras = [row for row in credits if row.group_index >= needed]
        for credit in extras:
            locked = _lock_credit_row(session, credit)
            if locked.status == "available":
                locked.status = "returned"
        session.flush()


def reserve_credit(
    session: Session, settings: Settings, account_id, order: Order
) -> HouseFidelityCredit:
    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        raise ConfirmationError("a fidelidade da casa ainda não está em vigor")
    credit = session.scalar(
        select(HouseFidelityCredit)
        .where(
            HouseFidelityCredit.campaign_id == campaign.id,
            HouseFidelityCredit.account_id == account_id,
            HouseFidelityCredit.status == "available",
        )
        .order_by(HouseFidelityCredit.created_at)
        .with_for_update(skip_locked=True)
    )
    if credit is None:
        raise ConfirmationError("não há crédito disponível para resgate")
    credit.status = "reserved"
    credit.reserved_order_id = order.id
    order.fidelity_credit_id = credit.id
    session.flush()
    return credit


def consume_or_return_credit(session: Session, order: Order) -> None:
    if order.fidelity_credit_id is None:
        return
    credit = session.get(HouseFidelityCredit, order.fidelity_credit_id)
    if credit is None:
        return
    locked = _lock_credit_row(session, credit)
    if order.status == OrderStatus.CANCELLED.value and locked.status == "reserved":
        locked.status = "available"
        locked.reserved_order_id = None
        order.fidelity_credit_id = None
        session.flush()
        return
    if order.fulfilled_at is not None and locked.status == "reserved":
        locked.status = "used"
        locked.used_order_id = order.id
        session.flush()
