"""Projeção só de leitura das quatro trilhas e do próximo passo.

Não grava, não muda status e não consulta o banco. O bucket de pagamento
já vem de classify_payment.
"""

from __future__ import annotations

from datetime import date

from app.domain.order_board import OPEN_DATE_REQUESTS
from app.domain.orders import order_delivery_pending

VIGENTE = ("submitted", "confirmed", "in_production", "ready")
_OPEN_DATES = set(OPEN_DATE_REQUESTS)


def _clip(text: str, limit: int = 60) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _track(state: str, label: str, tone: str, hint: str | None = None) -> dict:
    return {"state": state, "label": label, "tone": tone, "hint": hint}


def _action(code: str, label: str, primary: bool) -> dict:
    return {"code": code, "label": label, "primary": primary}


def _payment(order, bucket: str) -> dict:
    if bucket == "no_charge":
        if getattr(order, "status", None) == "submitted":
            return _track("no_charge", "Após aceite", "none", "A cobrança abre depois do aceite")
        return _track("no_charge", "Sem cobrança", "none", "Nenhuma cobrança iniciada")
    table = {
        "paid": ("paid", "Pago", "paid", None),
        "no_amount": ("no_amount", "Sem valor", "none", "Pedido sem valor a pagar"),
        "awaiting": ("awaiting", "Aguardando", "none", "Cobrança aberta, cliente ainda não pagou"),
        "processing": ("processing", "Processando", "none", "Pagamento encaminhado ao provedor, ainda pendente"),
        "unknown": ("unknown", "Verificando", "warn", "Pagamento não confirmado; a consulta ao provedor não respondeu"),
        "failed": ("failed", "Falhou", "warn", "Falha de pagamento"),
        "refunded": ("refunded", "Estornado", "warn", "Valor estornado"),
        "partial_refund": ("partial_refund", "Estorno parc.", "warn", "Estorno parcial; conferir saldo"),
        "charge_cancelled": ("charge_cancelled", "Cancelada", "none", "Cobrança cancelada no registro"),
        "cancelled_open": ("cancelled_open", "Sem cobrança", "none", "Pedido cancelado sem pagamento regular"),
    }
    state, label, tone, hint = table.get(
        bucket, ("unknown", "Verificando", "warn", "Pagamento não confirmado; a consulta ao provedor não respondeu")
    )
    return _track(state, label, tone, hint)


def _commercial_order(status: str) -> dict:
    if status == "cancelled":
        return _track("cancelled", "Cancelado", "cancelled")
    if status in {"confirmed", "in_production", "ready", "completed"}:
        return _track("accepted", "Aceito", "accepted")
    return _track("open", "Aberto", "open")


def _stamp(moment) -> str | None:
    if moment is None:
        return None
    from app.core.config import get_settings
    from app.domain.bakery_time import format_short_stamp

    return format_short_stamp(moment, get_settings().bakery_timezone)


def _production(order) -> dict:
    status = order.status
    started = _stamp(getattr(order, "production_started_at", None))
    started_hint = f"iniciada em {started}" if started else None
    if status in {"submitted", "confirmed"}:
        return _track("not_started", "Não iniciada", "none")
    if status == "in_production":
        return _track("in_production", "Em produção", "production", started_hint)
    if status == "ready":
        hint = "Pronto — aguardando confirmação de entrega"
        if started_hint:
            hint = f"{hint}. {started_hint}"
        return _track("ready", "Pronto", "open", hint)
    if status == "completed":
        return _track("done", "Concluída", "none", started_hint)
    if status == "cancelled" and getattr(order, "production_started_at", None):
        return _track("interrupted", "Interrompida", "cancelled", started_hint)
    return _track("not_applicable", "—", "none", "Não se aplica")


def _delivery(order) -> dict:
    status = order.status
    if status == "cancelled":
        return _track("not_applicable", "—", "none", "Não se aplica")
    if status == "completed" and getattr(order, "delivery_confirmed_at", None):
        delivered = _stamp(order.delivery_confirmed_at)
        hint = f"entregue em {delivered}" if delivered else None
        return _track("delivered", "Entregue", "delivered", hint)
    if status == "completed":
        return _track("finalized", "Finalizado", "none", "Conclusão antiga, sem comprovação de entrega")
    vigente = status in VIGENTE
    if vigente and getattr(order, "fulfillment_modality", None) == "pickup":
        return _track("pickup", "Retirada", "none")
    if vigente and order_delivery_pending(order):
        return _track("address_pending", "Sem endereço", "warn", "Endereço de entrega incompleto")
    if vigente:
        return _track("awaiting", "Aguardando", "none", "Entrega exige confirmação da equipe")
    return _track("not_applicable", "—", "none", "Não se aplica")


def _next_order(order, bucket: str, unresolved_adaptation: bool, *, duplicate_other_paid: bool = False) -> dict:
    status = order.status
    if (
        duplicate_other_paid
        and status == "confirmed"
        and bucket not in {"paid", "no_amount"}
    ):
        return _action("check_duplicate", "Ver duplicidade", True)
    if status == "submitted" and unresolved_adaptation:
        return _action("resolve_adaptation", "Resolver adaptação", True)
    if status == "submitted":
        return _action("accept", "Avaliar e aceitar", True)
    if status == "confirmed" and bucket in {"unknown", "failed"}:
        return _action("check_payment", "Ver pagamento", True)
    if status == "confirmed" and bucket in {"paid", "no_amount"}:
        return _action("start_production", "Iniciar produção", True)
    if status in {"in_production", "ready"}:
        return _action("confirm_delivery", "Confirmar entrega", True)
    return _action("open", "Abrir", False)


def _attention_order(
    order,
    bucket: str,
    unresolved_adaptation: bool,
    adaptation_text: str | None,
    today: date | None,
    *,
    duplicate_of: str | None = None,
    voided_of: str | None = None,
) -> str | None:
    if voided_of:
        return f"Duplicado de {voided_of}"
    if unresolved_adaptation:
        text = _clip(adaptation_text or "")
        return f"Adaptação pedida: {text}" if text else "Adaptação pedida"
    if duplicate_of:
        return f"Possível duplicado de {duplicate_of}"
    if bucket == "unknown":
        return "Pagamento não confirmado pelo provedor"
    operational = getattr(order, "production_local_date", None) or getattr(order, "proposed_production_date", None)
    if (
        today is not None
        and order.status in VIGENTE
        and operational is not None
        and operational < today
    ):
        return "Data da fornada já passou"
    reason = (getattr(order, "cancellation_reason", None) or "").strip()
    if order.status == "cancelled" and reason:
        return f"Motivo: {_clip(reason)}"
    return None


def _void_tracks(reference: str) -> dict:
    blank = _track("not_applicable", "—", "none", "Não se aplica")
    return {
        "commercial": blank,
        "payment": blank,
        "production": blank,
        "delivery": blank,
        "next_action": _action("open", "Abrir", False),
        "attention": f"Duplicado de {reference}",
    }


def order_tracks(
    order,
    bucket: str,
    *,
    unresolved_adaptation: bool,
    adaptation_text: str | None = None,
    today: date | None = None,
    duplicate_of: str | None = None,
    duplicate_other_paid: bool = False,
    voided_of: str | None = None,
) -> dict:
    from app.domain.order_reschedule import schedule_exception_of

    if voided_of:
        projection = _void_tracks(voided_of)
        projection["schedule_exception"] = schedule_exception_of(order)
        return projection
    return {
        "commercial": _commercial_order(order.status),
        "payment": _payment(order, bucket),
        "production": _production(order),
        "delivery": _delivery(order),
        "next_action": _next_order(
            order, bucket, unresolved_adaptation, duplicate_other_paid=duplicate_other_paid
        ),
        "attention": _attention_order(
            order,
            bucket,
            unresolved_adaptation,
            adaptation_text,
            today,
            duplicate_of=duplicate_of,
            voided_of=voided_of,
        ),
        "schedule_exception": schedule_exception_of(order),
    }


def _commercial_date(status: str) -> dict:
    if status == "closed":
        return _track("rejected", "Rejeitado", "cancelled")
    if status == "converted":
        return _track("converted", "Convertida", "none")
    return _track("open", "Aberto", "open")


def date_request_tracks(row, *, today: date | None = None) -> dict:
    status = row.status
    open_row = status in _OPEN_DATES
    attention = None
    desired = getattr(row, "desired_date", None)
    if open_row and today is not None and desired is not None and desired < today:
        attention = "Data da fornada já passou"
    return {
        "commercial": _commercial_date(status),
        "payment": _track("not_applicable", "Sem cobrança", "none", "Solicitação não é cobrança"),
        "production": _track("not_applicable", "—", "none", "Não se aplica"),
        "delivery": _track("not_applicable", "—", "none", "Não se aplica"),
        "next_action": (
            _action("respond_date_request", "Avaliar e responder", True)
            if open_row
            else _action("open", "Abrir", False)
        ),
        "attention": attention,
    }


def track_labels(projection: dict) -> list[str]:
    return [projection[name]["label"] for name in ("commercial", "payment", "production", "delivery")]
