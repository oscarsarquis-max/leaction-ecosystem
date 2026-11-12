from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.cpf import is_valid_cpf, only_cpf_digits
from app.domain.errors import ConfirmationError

logger = logging.getLogger(__name__)


class HubUnavailableError(ConfirmationError):
    pass


class HubConflictError(ConfirmationError):
    pass


@dataclass(frozen=True)
class HubCheckoutResult:
    order_id: str
    status: str
    checkout_url: str | None
    amount_cents: int
    reused: bool
    method: str
    pix_qr_code: str | None = None
    pix_qr_code_base64: str | None = None
    pix_ticket_url: str | None = None
    pix_date_of_expiration: str | None = None
    mp_payment_id: str | None = None
    currency: str = "BRL"
    order_reference: str | None = None
    paid_amount_cents: int | None = None
    refunded_amount_cents: int | None = None
    provider_status: str | None = None
    provider_observed_at: str | None = None
    provider_approved_at: str | None = None


def _headers(settings: Settings, idempotency_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.actionhub_app_secret}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-App-Id": settings.actionhub_app_id,
    }


def _require_configured(settings: Settings) -> None:
    if not settings.actionhub_app_secret.strip():
        raise HubUnavailableError("ActionHub não configurado para cobrança de teste")


def _parse_result(payload: dict[str, Any], *, reused: bool) -> HubCheckoutResult:
    pix = payload.get("pix") if isinstance(payload.get("pix"), dict) else {}
    checkout_url = payload.get("checkout_url")
    return HubCheckoutResult(
        order_id=str(payload["order_id"]),
        status=str(payload.get("status") or "PENDING"),
        checkout_url=str(checkout_url) if checkout_url else None,
        amount_cents=int(payload["amount_cents"]),
        reused=reused,
        method=str(payload.get("method") or "card"),
        currency=str(payload.get("currency") or "BRL"),
        order_reference=payload.get("order_reference"),
        paid_amount_cents=payload.get("paid_amount_cents"),
        refunded_amount_cents=payload.get("amount_refunded_cents"),
        provider_status=payload.get("provider_status"),
        provider_observed_at=payload.get("provider_observed_at"),
        provider_approved_at=payload.get("provider_approved_at"),
        pix_qr_code=str(pix["qr_code"]) if pix.get("qr_code") else None,
        pix_qr_code_base64=str(pix["qr_code_base64"]) if pix.get("qr_code_base64") else None,
        pix_ticket_url=str(pix["ticket_url"]) if pix.get("ticket_url") else None,
        pix_date_of_expiration=(
            str(pix["date_of_expiration"]) if pix.get("date_of_expiration") else None
        ),
        mp_payment_id=(
            str(pix["mp_payment_id"])
            if pix.get("mp_payment_id")
            else str(payload["mp_payment_id"])
            if payload.get("mp_payment_id")
            else None
        ),
    )


def _raise_from_response(response: httpx.Response) -> None:
    if response.status_code == 409:
        raise HubConflictError("chave de cobrança já usada com outro valor ou método")
    if response.status_code >= 500:
        raise HubUnavailableError("ActionHub indisponível")
    detail = "ActionHub recusou a cobrança"
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("error"):
            detail = str(payload["error"])
    except Exception:
        pass
    raise ConfirmationError(detail)


def _clean(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def build_card_payer(order: Any, *, cpf: str | None = None) -> dict[str, Any] | None:
    """Monta o pagador com o que o pedido já tem. Campo inválido sai fora.

    A fidelidade guarda só o hash do CPF, não os dígitos. Sem `cpf` explícito,
    o documento não entra.
    """
    try:
        payer: dict[str, Any] = {}
        parts = [part for part in _clean(getattr(order, "customer_name", ""), 120).split(" ") if part]
        if parts:
            payer["first_name"] = parts[0][:40]
            if len(parts) > 1:
                payer["last_name"] = " ".join(parts[1:])[:80]
        email = _clean(getattr(order, "customer_email", ""), 254).lower()
        if "@" in email and " " not in email:
            payer["email"] = email
        digits = is_valid_cpf(cpf or "")
        if cpf and digits:
            payer["identification"] = {"type": "CPF", "number": only_cpf_digits(cpf or "")}
        elif cpf:
            logger.info("campo do pagador descartado: identification")
        phone = re.sub(r"\D", "", str(getattr(order, "customer_phone", "") or ""))
        if phone.startswith("55") and len(phone) in {12, 13}:
            phone = phone[2:]
        if len(phone) in {10, 11}:
            payer["phone"] = {"area_code": phone[:2], "number": phone[2:]}
        elif phone:
            logger.info("campo do pagador descartado: phone")
        address: dict[str, str] = {}
        postal = re.sub(r"\D", "", str(getattr(order, "delivery_postal_code", "") or ""))
        if len(postal) == 8:
            address["zip_code"] = postal
        elif postal:
            logger.info("campo do pagador descartado: zip_code")
        street = _clean(getattr(order, "delivery_street", ""), 80)
        number = _clean(getattr(order, "delivery_number", ""), 20)
        district = _clean(getattr(order, "delivery_district", ""), 80)
        city = _clean(getattr(order, "delivery_city", ""), 80)
        state = _clean(getattr(order, "delivery_state", ""), 2).upper()
        if street:
            address["street_name"] = street
        if number:
            address["street_number"] = number
        if district:
            address["neighborhood"] = district
        if city:
            address["city"] = city
        if len(state) == 2 and state.isalpha():
            address["federal_unit"] = state
        if address:
            payer["address"] = address
        if not payer:
            return None
        logger.info("pagador do cartão preparado campos=%s", ",".join(sorted(payer)))
        return payer
    except Exception:
        logger.info("pagador do cartão omitido")
        return None


def checkout_request_body(
    *,
    app_id: str,
    order_reference: str,
    payment_request_id: str,
    amount_cents: int,
    description: str,
    method: str,
    customer_email: str,
    customer_name: str,
    return_origin: str,
    return_to: str,
    payer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "app_id": app_id,
        "order_reference": order_reference,
        "payment_request_id": payment_request_id,
        "amount_cents": amount_cents,
        "currency": "BRL",
        "description": description,
        "method": method,
        "customer": {"email": customer_email, "name": customer_name},
        "return_origin": return_origin,
        "return_to": return_to,
    }
    if method == "card" and payer:
        body["payer"] = payer
    return body


def request_amount_checkout(
    settings: Settings,
    *,
    order_reference: str,
    payment_request_id: str,
    amount_cents: int,
    description: str,
    customer_email: str,
    customer_name: str,
    return_to: str,
    idempotency_key: str,
    method: str,
    payer: dict[str, Any] | None = None,
) -> HubCheckoutResult:
    _require_configured(settings)
    url = f"{settings.actionhub_base_url.rstrip('/')}/v1/checkout/amount"
    body = checkout_request_body(
        app_id=settings.actionhub_app_id,
        order_reference=order_reference,
        payment_request_id=payment_request_id,
        amount_cents=amount_cents,
        description=description,
        method=method,
        customer_email=customer_email,
        customer_name=customer_name,
        return_origin=settings.public_origin,
        return_to=return_to,
        payer=payer,
    )
    try:
        response = httpx.post(
            url,
            json=body,
            headers=_headers(settings, idempotency_key),
            timeout=settings.actionhub_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise HubUnavailableError("timeout ao criar cobrança no ActionHub") from exc
    except httpx.HTTPError as exc:
        raise HubUnavailableError("falha ao falar com o ActionHub") from exc
    if response.status_code not in {200, 201}:
        _raise_from_response(response)
    payload = response.json()
    return _parse_result(payload, reused=bool(payload.get("reused")))


def lookup_amount_checkout(
    settings: Settings, *, payment_request_id: str
) -> HubCheckoutResult | None:
    _require_configured(settings)
    url = f"{settings.actionhub_base_url.rstrip('/')}/v1/checkout/amount"
    try:
        response = httpx.get(
            url,
            params={
                "app_id": settings.actionhub_app_id,
                "payment_request_id": payment_request_id,
            },
            headers=_headers(settings, payment_request_id),
            timeout=settings.actionhub_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise HubUnavailableError("timeout ao consultar cobrança no ActionHub") from exc
    except httpx.HTTPError as exc:
        raise HubUnavailableError("falha ao falar com o ActionHub") from exc
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HubUnavailableError("ActionHub indisponível para reconciliação")
    payload = response.json()
    return _parse_result(payload, reused=True)


def cancel_amount_checkout(settings: Settings, hub_order_id: str) -> None:
    _require_configured(settings)
    url = f"{settings.actionhub_base_url.rstrip('/')}/v1/checkout/amount/{hub_order_id}/cancel"
    try:
        response = httpx.post(
            url,
            headers=_headers(settings, hub_order_id),
            timeout=settings.actionhub_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise HubUnavailableError("timeout ao cancelar cobrança no ActionHub") from exc
    except httpx.HTTPError as exc:
        raise HubUnavailableError("falha ao cancelar cobrança no ActionHub") from exc
    if response.status_code == 409:
        raise HubConflictError("há um pagamento já aprovado nesta tentativa")
    if response.status_code >= 400:
        _raise_from_response(response)
