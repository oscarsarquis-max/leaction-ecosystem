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


def _production(order) -> dict:
    status = order.status
    if status in {"submitted", "confirmed"}:
        return _track("not_started", "Não iniciada", "none")
    if status == "in_production":
        return _track("in_production", "Em produção", "production")
    if status == "ready":
        return _track("ready", "Pronto", "open", "Pronto — aguardando confirmação de entrega")
    if status == "completed":
        return _track("done", "Concluída", "none")
    if status == "cancelled" and getattr(order, "production_started_at", None):
        return _track("interrupted", "Interrompida", "cancelled")
    return _track("not_applicable", "—", "none", "Não se aplica")


def _delivery(order) -> dict:
    status = order.status
    if status == "cancelled":
        return _track("not_applicable", "—", "none", "Não se aplica")
    if status == "completed" and getattr(order, "delivery_confirmed_at", None):
        return _track("delivered", "Entregue", "delivered")
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


def _next_order(order, bucket: str, unresolved_adaptation: bool) -> dict:
    status = order.status
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


def _attention_order(order, bucket: str, unresolved_adaptation: bool, adaptation_text: str | None, today: date | None) -> str | None:
    if unresolved_adaptation:
        text = _clip(adaptation_text or "")
        return f"Adaptação pedida: {text}" if text else "Adaptação pedida"
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


def order_tracks(
    order,
    bucket: str,
    *,
    unresolved_adaptation: bool,
    adaptation_text: str | None = None,
    today: date | None = None,
) -> dict:
    return {
        "commercial": _commercial_order(order.status),
        "payment": _payment(order, bucket),
        "production": _production(order),
        "delivery": _delivery(order),
        "next_action": _next_order(order, bucket, unresolved_adaptation),
        "attention": _attention_order(order, bucket, unresolved_adaptation, adaptation_text, today),
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
