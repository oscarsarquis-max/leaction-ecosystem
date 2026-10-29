"""Reserva, confirmação e recuperação de crédito via ActionHub. Sem ledger local."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.actionhub_client import HubUnavailableError
from app.domain.baker_library.access import subject_hmac
from app.domain.baker_library.hub_plans import invoke as hub_plans_invoke
from app.models.baker_library import GigioCreditOperation
from app.models.customers import CustomerAccount

logger = logging.getLogger("lojadepaes.biblioteca")


def recovered_reply(session: Session, operation_id: str) -> dict[str, Any] | None:
    row = session.get(GigioCreditOperation, operation_id)
    if row is None or row.status != "confirmed" or not row.reply_json:
        return None
    try:
        payload = json.loads(row.reply_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not payload.get("reply"):
        return None
    return payload


def remember_operation(
    session: Session,
    settings: Settings,
    account: CustomerAccount | None,
    operation_id: str,
    status: str,
    reply: dict[str, Any] | None = None,
) -> None:
    digest = subject_hmac(settings, account.email) if account else None
    row = session.get(GigioCreditOperation, operation_id)
    if row is None:
        row = GigioCreditOperation(operation_id=operation_id)
        session.add(row)
    row.subject_hmac = digest
    row.status = status
    if reply is not None:
        row.reply_json = json.dumps(reply, ensure_ascii=False)
    row.updated_at = datetime.now(UTC)
    session.flush()


def reserve_credit(
    settings: Settings,
    account: CustomerAccount,
    operation_id: str,
    *,
    amount: int = 1,
) -> dict[str, Any]:
    return _call(settings, "reserve", account.email, operation_id, amount=amount)


def confirm_credit(settings: Settings, account: CustomerAccount, operation_id: str) -> dict[str, Any]:
    return _call(settings, "confirm", account.email, operation_id)


def release_credit(settings: Settings, account: CustomerAccount, operation_id: str) -> dict[str, Any]:
    return _call(settings, "release", account.email, operation_id)


def _call(
    settings: Settings,
    action: str,
    email: str,
    operation_id: str,
    *,
    amount: int | None = None,
) -> dict[str, Any]:
    capability = {
        "reserve": "RESERVE_HUB_CREDITS",
        "confirm": "CONFIRM_HUB_CREDITS",
        "release": "RELEASE_HUB_CREDITS",
    }.get(action)
    if not capability:
        raise HubUnavailableError("operação de crédito não reconhecida")
    inputs: dict[str, Any] = {"subject_id": email, "operation_id": operation_id}
    if amount is not None:
        inputs["amount"] = amount
    payload = hub_plans_invoke(
        settings,
        capability,
        inputs,
        correlation_id=f"loja-credit-{operation_id}"[:80],
        idempotency_key=f"credit:{action}:{operation_id}",
    )
    if not isinstance(payload, dict):
        payload = {}
    if payload.get("ok") is False or payload.get("error"):
        reason = str(payload.get("error") or payload.get("reason") or "credit_denied")
        return {
            "ok": False,
            "reason": reason,
            "credits": payload.get("credits"),
            "valid_until": payload.get("valid_until"),
            "message": _credit_error_message(reason),
        }
    return {
        "ok": True,
        "status": payload.get("status"),
        "idempotent": bool(payload.get("idempotent")),
        "credits": payload.get("credits"),
        "valid_until": payload.get("valid_until"),
    }


def _credit_error_message(reason: str) -> str:
    if reason == "insufficient_credits":
        return (
            "As consultas de IA deste saldo acabaram. Artigos, calculadora, compras e atendimento "
            "continuam abertos. O pacote adicional é compra avulsa na página de planos do ActionHub."
        )
    if reason == "expired":
        return "O ciclo do ActionHub terminou. A leitura e a calculadora continuam abertas."
    if reason == "no_entitlement":
        return "Este aprofundamento faz parte do plano mensal da Biblioteca."
    return "Não foi possível validar o crédito no ActionHub agora. Isso não esgota o saldo nem cancela a assinatura."
