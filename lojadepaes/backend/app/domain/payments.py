from collections.abc import Sequence

from app.models.orders import Order
from app.models.payments import PaymentRecord

SETTLING_STATUSES = frozenset({"paid", "partially_refunded", "refunded"})
IGNORED_STATUSES = frozenset({"failed", "cancelled"})


def net_confirmed_cents(records: Sequence[PaymentRecord]) -> int | None:
    """Soma pago − estornado. None se algum registro relevante tem valor desconhecido."""
    total = 0
    saw_settling = False
    for record in records:
        if record.financial_status in IGNORED_STATUSES:
            continue
        if record.financial_status not in SETTLING_STATUSES:
            if record.financial_status in {"pending", "unknown"}:
                return None
            continue
        saw_settling = True
        if record.amount_paid_cents is None:
            return None
        refunded = record.amount_refunded_cents
        if refunded is None and record.financial_status in {"partially_refunded", "refunded"}:
            return None
        total += record.amount_paid_cents - (refunded or 0)
    if not saw_settling:
        return 0
    return total


def order_is_financially_settled(order: Order, records: Sequence[PaymentRecord]) -> bool:
    if order.total_cents is None:
        return False
    matching = [
        row for row in records if row.order_id == order.id and row.currency == order.currency
    ]
    net = net_confirmed_cents(matching)
    return net is not None and net >= order.total_cents


def financial_list_kind(order: Order, records: Sequence[PaymentRecord]) -> str:
    """Resumo seguro para listagem. Não usa 'paid' no nível do pedido."""
    matching = [row for row in records if row.order_id == order.id]
    if not matching:
        return "none"
    if order_is_financially_settled(order, matching):
        return "settled"
    if net_confirmed_cents(matching) is None:
        return "unknown"
    return "open"
