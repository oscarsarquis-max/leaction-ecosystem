"""Leitura gerencial. Não grava pedido, aviso, pagamento nem status."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import bakery_today
from app.domain.orders import order_delivery_pending
from app.domain.payments import order_is_financially_settled
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import AdaptationStatus, OrderStatus
from app.models.orders import Order, OrderItem, OrderItemAdaptation
from app.models.payments import PaymentRecord

OPEN_DATE_REQUESTS = ("pending", "alternative_proposed", "awaiting_details")
FLOW_ORDER_STATUSES = (
    OrderStatus.SUBMITTED.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
)
VIGENTE_ORDER_STATUSES = (*FLOW_ORDER_STATUSES, OrderStatus.READY.value)
READY_EXCEPTION_LABEL = "Pronto — aguardando confirmação de entrega"
VISIBLE_LABELS = {
    "open": "Aberto",
    "accepted": "Aceito",
    "paid": "Pago",
    "in_production": "Em produção",
    "delivered": "Entregue",
    "finalized": "Finalizado",
    "ready_legacy": READY_EXCEPTION_LABEL,
    "cancelled": "Cancelado",
    "rejected": "Rejeitado",
    "converted": "Convertida em pedido",
}
OBSERVED_FINANCIAL = {
    "paid": "Pago",
    "no_amount": "Sem valor a pagar",
    "unknown": "Estado financeiro desconhecido",
    "awaiting": "Aguardando pagamento",
    "processing": "Em processamento",
    "failed": "Falha de pagamento",
    "no_charge": "Sem cobrança iniciada",
    "refunded": "Estornado",
    "partial_refund": "Estorno parcial",
    "charge_cancelled": "Cobrança cancelada",
    "cancelled_open": "Sem pagamento regular",
}
_STAGE_LENS = {
    "open": "stage:open",
    "accepted": "stage:accepted",
    "paid": "stage:paid",
    "in_production": "stage:in_production",
    "delivered": "stage:delivered",
    "finalized": "stage:finalized",
    "ready_legacy": "stage:ready_legacy",
    "cancelled": "stage:cancelled",
    "rejected": "stage:rejected",
}
CUSTOMER_NOTICE_KINDS = (
    "order_submitted",
    "payment_approved",
    "order_accepted",
    "date_request_received",
    "date_request_proposed",
    "date_request_available",
    "date_request_declined",
    "date_request_complete",
    "adaptation_proposed",
)

LENS_LABELS = {
    "stage:open": "Aberto — solicitação ou encomenda ainda em avaliação",
    "stage:accepted": "Aceito — pedido formalizado, sem quitação regular e sem produção",
    "stage:paid": "Pago — pagamento confirmado, produção ainda não iniciada",
    "stage:in_production": "Em produção — iniciada por ação operacional",
    "stage:delivered": "Entregue — confirmação explícita do gestor; fora da fila vigente",
    "stage:finalized": "Finalizado — conclusão antiga, sem comprovação de entrega",
    "stage:ready_legacy": READY_EXCEPTION_LABEL,
    "stage:cancelled": "Cancelado — distinto de rejeição",
    "stage:rejected": "Rejeitado — solicitação recusada, fora do fluxo vigente",
    "payment:awaiting": "Aguardando pagamento — cobrança aberta, sem processamento no provedor",
    "payment:processing": "Em processamento — cobrança já encaminhada, ainda pendente",
    "payment:paid": "Pagos — valor quitado, sem estorno",
    "payment:failed": "Falha de pagamento",
    "payment:no_charge": "Sem cobrança iniciada",
    "payment:no_amount": "Sem valor a pagar",
    "payment:refunded": "Estornados",
    "payment:partial_refund": "Estorno parcial",
    "payment:unknown": "Estado financeiro desconhecido",
    "payment:charge_cancelled": "Cobrança cancelada no registro",
    "payment:cancelled_open": "Pedido cancelado, sem pagamento regular",
    "pending:address": "Endereço de entrega incompleto",
    "pending:notice_pending": "Aviso ao cliente ainda na fila de envio",
    "pending:notice_failed": "Falha efetiva no aviso ao cliente",
    "pending:notice_skipped": "Aviso ao cliente registrado, envio não disparado",
    "pending:overdue": "Data da fornada ou data desejada já passou",
    "pending:adaptation": "Adaptação ainda sem desfecho",
    "work:payment:awaiting": "Aguardando no fluxo",
    "work:payment:processing": "Em processamento no fluxo",
    "work:payment:paid": "Quitados no fluxo",
    "work:payment:failed": "Falha no fluxo",
    "audit:tests": "Testes fora da operação",
    "work:needs_action": "Precisa de ação — pedidos e solicitações com passo da equipe",
}


def lens_fetch_status(lens: str) -> str | None:
    if lens.startswith("stage:"):
        return {
            "stage:open": "submitted",
            "stage:accepted": "confirmed",
            "stage:paid": "confirmed",
            "stage:in_production": "in_production",
            "stage:delivered": "completed",
            "stage:finalized": "completed",
            "stage:ready_legacy": "ready",
            "stage:cancelled": "cancelled",
            "stage:rejected": "date_closed",
        }.get(lens)
    if lens.startswith("payment:") or lens.startswith("pending:") or lens.startswith("work:"):
        return "all"
    if lens == "audit:tests":
        return "all"
    return None


def _anchor(row: EmailOutbox) -> str | None:
    if row.order_id is not None:
        return f"order:{row.order_id}"
    if row.date_request_id is not None:
        return f"date_request:{row.date_request_id}"
    return None


def classify_payment(order: Order, records: list[PaymentRecord]) -> str:
    """Um pedido, uma classe. Não consulta o provedor."""
    matching = [row for row in records if row.currency == order.currency]
    statuses = {row.financial_status for row in matching}
    if "unknown" in statuses:
        return "unknown"
    if "refunded" in statuses:
        return "refunded"
    if "partially_refunded" in statuses:
        return "partial_refund"
    if order.total_cents == 0:
        return "no_amount"
    if order.total_cents is None:
        return "unknown"
    if not matching:
        if order.status == OrderStatus.CANCELLED.value:
            return "cancelled_open"
        return "no_charge"
    settled = order_is_financially_settled(order, matching)
    if settled and "paid" in statuses:
        return "paid"
    if any(row.financial_status == "pending" and row.external_reference for row in matching):
        return "processing"
    if "pending" in statuses:
        return "awaiting"
    if "failed" in statuses:
        return "failed"
    if "cancelled" in statuses:
        return "charge_cancelled"
    if order.status == OrderStatus.CANCELLED.value:
        return "cancelled_open"
    return "unknown"


def production_clearance(bucket: str) -> str:
    if bucket in {"paid", "no_amount"}:
        return "clear"
    if bucket == "unknown":
        return "uncertain"
    return "unpaid"


def observed_financial_label(bucket: str) -> str:
    return OBSERVED_FINANCIAL.get(bucket, "Estado financeiro desconhecido")


def visible_stage_for_order(order: Order, bucket: str) -> str:
    status = order.status
    if status == OrderStatus.CANCELLED.value:
        return "cancelled"
    if status == OrderStatus.COMPLETED.value:
        if order.delivery_confirmed_at is not None:
            return "delivered"
        return "finalized"
    if status == OrderStatus.READY.value:
        return "ready_legacy"
    if status == OrderStatus.IN_PRODUCTION.value:
        return "in_production"
    if status == OrderStatus.CONFIRMED.value:
        return "paid" if bucket == "paid" else "accepted"
    return "open"


def visible_label_for_order(order: Order, bucket: str) -> str:
    return VISIBLE_LABELS[visible_stage_for_order(order, bucket)]


def payment_attention_label(order: Order, bucket: str) -> str | None:
    if order.status == OrderStatus.CANCELLED.value:
        return None
    clearance = production_clearance(bucket)
    if clearance == "clear":
        return None
    if clearance == "uncertain":
        return "Pagamento não confirmado"
    return "Pagamento pendente"


def date_visible(status: str) -> tuple[str | None, str | None]:
    if status in OPEN_DATE_REQUESTS:
        return "open", VISIBLE_LABELS["open"]
    if status == "closed":
        return "rejected", VISIBLE_LABELS["rejected"]
    if status == "converted":
        return "converted", VISIBLE_LABELS["converted"]
    return None, None


def _count(keys: dict[str, set[str]], lens: str) -> int:
    return len(keys.get(lens, ()))


def _metric(label: str, lens: str, keys: dict[str, set[str]]) -> dict:
    return {"label": label, "count": _count(keys, lens), "lens": lens}


def managerial_board(session: Session, settings: Settings) -> tuple[dict, dict[str, set[str]]]:
    from app.domain.managerial_exclusion import active_exclusion_sets

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
        if row.id not in excluded_dates
    ]
    order_ids = [order.id for order in orders]
    records_by_order: dict = {order.id: [] for order in orders}
    if order_ids:
        payment_rows = session.scalars(
            select(PaymentRecord).where(PaymentRecord.order_id.in_(order_ids))
        )
        for record in payment_rows:
            records_by_order.setdefault(record.order_id, []).append(record)
    adaptations: set = set()
    adaptation_text: dict = {}
    if order_ids:
        for order_id, customer_text in session.execute(
            select(OrderItem.order_id, OrderItemAdaptation.customer_text)
            .join(OrderItemAdaptation, OrderItemAdaptation.order_item_id == OrderItem.id)
            .where(OrderItem.order_id.in_(order_ids))
            .where(
                OrderItemAdaptation.status.notin_(
                    (
                        AdaptationStatus.ACCEPTED.value,
                        AdaptationStatus.ALTERNATIVE_ACCEPTED.value,
                    )
                )
            )
        ):
            adaptations.add(order_id)
            adaptation_text.setdefault(order_id, customer_text)
    notices: dict[tuple[str, str], str] = {}
    notice_rows = session.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.kind.in_(CUSTOMER_NOTICE_KINDS))
        .order_by(EmailOutbox.created_at.asc(), EmailOutbox.id.asc())
    )
    for row in notice_rows:
        anchor = _anchor(row)
        if anchor is not None:
            notices[(anchor, row.kind)] = row.status
    notice_status: dict[str, set[str]] = {}
    for (anchor, _kind), status in notices.items():
        notice_status.setdefault(anchor, set()).add(status)

    from app.domain.order_tracks import date_request_tracks, order_tracks

    keys: dict[str, set[str]] = {lens: set() for lens in LENS_LABELS}
    for row in dates:
        if row.status in OPEN_DATE_REQUESTS:
            keys["stage:open"].add(f"date_request:{row.id}")
            if row.desired_date < today:
                keys["pending:overdue"].add(f"date_request:{row.id}")
        elif row.status == "closed":
            keys["stage:rejected"].add(f"date_request:{row.id}")
        anchor = f"date_request:{row.id}"
        statuses = notice_status.get(anchor, set())
        if "failed" in statuses:
            keys["pending:notice_failed"].add(anchor)
        if "pending" in statuses:
            keys["pending:notice_pending"].add(anchor)
        if "skipped" in statuses:
            keys["pending:notice_skipped"].add(anchor)
        if date_request_tracks(row, today=today)["next_action"]["primary"]:
            keys["work:needs_action"].add(anchor)
    for order in orders:
        anchor = f"order:{order.id}"
        bucket = classify_payment(order, records_by_order.get(order.id, []))
        stage_lens = _STAGE_LENS.get(visible_stage_for_order(order, bucket))
        if stage_lens:
            keys[stage_lens].add(anchor)
        payment_lens = f"payment:{bucket}"
        if payment_lens in keys:
            keys[payment_lens].add(anchor)
        if visible_stage_for_order(order, bucket) in {
            "open",
            "accepted",
            "paid",
            "in_production",
            "ready_legacy",
        }:
            work_lens = f"work:payment:{bucket}"
            if work_lens in keys:
                keys[work_lens].add(anchor)
        # Pronto sem entrega conserva o marcador de endereço; Entregue e Finalizado ficam de fora.
        if order_delivery_pending(order) and order.status in VIGENTE_ORDER_STATUSES:
            keys["pending:address"].add(anchor)
        if order.id in adaptations and order.status in VIGENTE_ORDER_STATUSES:
            keys["pending:adaptation"].add(anchor)
        operational_date = order.production_local_date or order.proposed_production_date
        if (
            order.status in VIGENTE_ORDER_STATUSES
            and operational_date is not None
            and operational_date < today
        ):
            keys["pending:overdue"].add(anchor)
        statuses = notice_status.get(anchor, set())
        if "failed" in statuses:
            keys["pending:notice_failed"].add(anchor)
        if "pending" in statuses:
            keys["pending:notice_pending"].add(anchor)
        if "skipped" in statuses:
            keys["pending:notice_skipped"].add(anchor)
        projection = order_tracks(
            order,
            bucket,
            unresolved_adaptation=order.id in adaptations,
            adaptation_text=adaptation_text.get(order.id),
            today=today,
        )
        if projection["next_action"]["primary"]:
            keys["work:needs_action"].add(anchor)

    for order_id in excluded_orders:
        keys["audit:tests"].add(f"order:{order_id}")
    for date_id in excluded_dates:
        keys["audit:tests"].add(f"date_request:{date_id}")

    current = (
        _count(keys, "stage:open")
        + _count(keys, "stage:accepted")
        + _count(keys, "stage:paid")
        + _count(keys, "stage:in_production")
        + _count(keys, "stage:ready_legacy")
    )
    zone = ZoneInfo(settings.bakery_timezone)
    stamp = datetime.now(zone)
    board = {
        "scope": (
            "Situação atual de todos os registros, sem filtro de data de criação. "
            "A data ultrapassada usa a data da fornada ou a data desejada."
        ),
        "timezone": settings.bakery_timezone,
        "updated_label": stamp.strftime("%d/%m/%Y %H:%M"),
        "operational_total": current,
        "stages": [
            _metric("Aberto", "stage:open", keys),
            _metric("Aceito", "stage:accepted", keys),
            _metric("Pago", "stage:paid", keys),
            _metric("Em produção", "stage:in_production", keys),
        ],
        "exceptions": [
            _metric(READY_EXCEPTION_LABEL, "stage:ready_legacy", keys),
        ],
        "composition_note": (
            "O total vigente soma Aberto, Aceito, Pago e Em produção "
            "com a exceção Pronto — aguardando confirmação de entrega."
        ),
        "history": [
            _metric("Entregue", "stage:delivered", keys),
            _metric("Finalizado", "stage:finalized", keys),
            _metric("Cancelado", "stage:cancelled", keys),
            _metric("Rejeitado", "stage:rejected", keys),
        ],
        "legacy_note": (
            "Pronto sem confirmação de entrega permanece na fila vigente como exceção operacional. "
            "Finalizado permanece com o significado original. Não foram convertidos em Entregue."
        ),
        "payment_note": (
            "Classifica os pedidos já criados, inclusive em produção, finalizados, "
            "entregues e cancelados. Não soma com o fluxo vigente. "
            "Solicitação sem pedido não é cobrança. "
            "Pagamento posterior não tira o pedido de Em produção nem o marca Entregue."
        ),
        "payments": [
            _metric("Aguardando pagamento", "payment:awaiting", keys),
            _metric("Em processamento", "payment:processing", keys),
            _metric("Pagos", "payment:paid", keys),
            _metric("Falha de pagamento", "payment:failed", keys),
        ],
        "payment_other": [
            _metric("Sem cobrança iniciada", "payment:no_charge", keys),
            _metric("Sem valor a pagar", "payment:no_amount", keys),
            _metric("Estornados", "payment:refunded", keys),
            _metric("Estorno parcial", "payment:partial_refund", keys),
            _metric("Estado desconhecido", "payment:unknown", keys),
            _metric("Cobrança cancelada", "payment:charge_cancelled", keys),
            _metric("Cancelado sem pagamento regular", "payment:cancelled_open", keys),
        ],
        "payment_orders": len(orders),
        "payment_scope_label": "Financeiro de todo o histórico",
        "work_payments": [
            _metric("Aguardando no fluxo", "work:payment:awaiting", keys),
            _metric("Em processamento no fluxo", "work:payment:processing", keys),
            _metric("Quitados no fluxo", "work:payment:paid", keys),
            _metric("Falha no fluxo", "work:payment:failed", keys),
        ],
        "work_payment_orders": _count(keys, "work:payment:awaiting")
        + _count(keys, "work:payment:processing")
        + _count(keys, "work:payment:paid")
        + _count(keys, "work:payment:failed"),
        "excluded_tests": len(excluded_orders) + len(excluded_dates),
        "excluded_holding_capacity": sum(
            1
            for order in session.scalars(select(Order).where(Order.id.in_(excluded_orders)))
            if order.holds_capacity
        )
        if excluded_orders
        else 0,
        "pending_note": (
            "Um mesmo pedido pode ter mais de uma pendência. "
            "Isso não aumenta o total do fluxo. Aviso enviado não é pão enviado."
        ),
        "pendings": [
            _metric("Endereço de entrega incompleto", "pending:address", keys),
            _metric("Aviso na fila de envio", "pending:notice_pending", keys),
            _metric("Falha no aviso ao cliente", "pending:notice_failed", keys),
            _metric("Aviso não disparado", "pending:notice_skipped", keys),
            _metric("Data ultrapassada", "pending:overdue", keys),
            _metric("Adaptação em aberto", "pending:adaptation", keys),
        ],
        "not_tracked": [],
    }
    return board, keys
