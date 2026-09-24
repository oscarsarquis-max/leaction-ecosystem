from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.errors import ConfirmationError


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
) -> HubCheckoutResult:
    _require_configured(settings)
    url = f"{settings.actionhub_base_url.rstrip('/')}/v1/checkout/amount"
    body = {
        "app_id": settings.actionhub_app_id,
        "order_reference": order_reference,
        "payment_request_id": payment_request_id,
        "amount_cents": amount_cents,
        "currency": "BRL",
        "description": description,
        "method": method,
        "customer": {"email": customer_email, "name": customer_name},
        "return_origin": settings.public_origin,
        "return_to": return_to,
    }
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
