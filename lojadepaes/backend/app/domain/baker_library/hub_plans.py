"""Fronteira temporária Loja → ActionHub para planos da Biblioteca.

Não chama o checkout de pedidos (`/v1/checkout/amount`).
Não usa Spider. IDs de operação e capacidades ficam estáveis para troca futura.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.domain.actionhub_client import HubUnavailableError
from app.domain.errors import ConfirmationError

CAPABILITIES = {
    "LIST_HUB_CATALOG": ("GET", "/v1/catalog/{app_id}", False),
    "GET_HUB_ENTITLEMENTS": ("GET", "/v1/entitlements", True),
    "LIST_HUB_SUBSCRIPTIONS": ("GET", "/v1/subscriptions", True),
    "START_HUB_CATALOG_CHECKOUT": ("POST", "/v1/checkout/catalog", False),
    "CANCEL_HUB_SUBSCRIPTION": ("POST", "/v1/subscriptions/cancel", True),
    "RESERVE_HUB_CREDITS": ("POST", "/v1/credits/reserve", True),
    "CONFIRM_HUB_CREDITS": ("POST", "/v1/credits/confirm", True),
    "RELEASE_HUB_CREDITS": ("POST", "/v1/credits/release", True),
}


def invoke(
    settings: Settings,
    capability_id: str,
    inputs: dict[str, Any],
    *,
    correlation_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    spec = CAPABILITIES.get(capability_id)
    if not spec:
        raise HubUnavailableError("capacidade da Biblioteca não reconhecida")
    method, path, require_secret = spec
    if require_secret and not settings.actionhub_app_secret.strip():
        raise HubUnavailableError("ActionHub sem credencial técnica para planos")
    url = _url(settings, path)
    params, body = _request_parts(settings, capability_id, inputs)
    timeout = min(float(settings.actionhub_timeout_seconds or 15), 15)
    try:
        response = httpx.request(
            method,
            url,
            params=params or None,
            json=body,
            headers=_headers(settings, idempotency_key, correlation_id),
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise HubUnavailableError("timeout ao consultar o ActionHub") from exc
    except httpx.HTTPError as exc:
        raise HubUnavailableError("falha ao consultar o ActionHub") from exc
    return _parse_response(capability_id, response)


def _url(settings: Settings, path: str) -> str:
    base = settings.actionhub_base_url.rstrip("/")
    app_id = settings.actionhub_app_id.strip() or "lojadepaes"
    return f"{base}{path.format(app_id=app_id)}"


def _headers(settings: Settings, idempotency_key: str, correlation_id: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key[:180],
        "X-App-Id": settings.actionhub_app_id,
        "X-Correlation-ID": correlation_id[:80],
    }
    secret = settings.actionhub_app_secret.strip()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
        headers["X-App-Secret"] = secret
    return headers


def _request_parts(
    settings: Settings, capability_id: str, inputs: dict[str, Any]
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    app_id = settings.actionhub_app_id.strip() or "lojadepaes"
    subject = str(inputs.get("subject_id") or "").strip()
    if capability_id == "LIST_HUB_CATALOG":
        return None, None
    if capability_id == "GET_HUB_ENTITLEMENTS":
        return {"app_id": app_id, "subject_id": subject}, None
    if capability_id == "LIST_HUB_SUBSCRIPTIONS":
        return {"app_id": app_id, "subject_id": subject}, None
    if capability_id == "START_HUB_CATALOG_CHECKOUT":
        return None, {
            "app_id": app_id,
            "subject_id": subject,
            "sku": str(inputs.get("sku") or "").strip(),
            "return_origin": str(inputs.get("return_origin") or settings.public_origin),
            "return_to": str(inputs.get("return_to") or "/#biblioteca"),
        }
    if capability_id == "CANCEL_HUB_SUBSCRIPTION":
        return None, {
            "app_id": app_id,
            "subject_id": subject,
            "sku": str(inputs.get("sku") or "").strip(),
        }
    body: dict[str, Any] = {
        "app_id": app_id,
        "subject_id": subject,
        "operation_id": str(inputs.get("operation_id") or "").strip(),
    }
    if inputs.get("amount") is not None:
        body["amount"] = inputs["amount"]
    return None, body


def _parse_response(capability_id: str, response: httpx.Response) -> dict[str, Any]:
    payload = _json_body(response)
    if response.status_code in {200, 201}:
        return payload if isinstance(payload, dict) else {}
    if capability_id.startswith(("RESERVE_", "CONFIRM_", "RELEASE_")) and response.status_code in {409, 400}:
        error = ""
        if isinstance(payload, dict):
            error = str(payload.get("error") or payload.get("reason") or "")
        return {
            "ok": False,
            "error": error or "credit_denied",
            "reason": error or "credit_denied",
            "credits": payload.get("credits") if isinstance(payload, dict) else None,
            "valid_until": payload.get("valid_until") if isinstance(payload, dict) else None,
        }
    if response.status_code in {401, 403}:
        raise ConfirmationError("ActionHub recusou a credencial de planos")
    if response.status_code >= 500:
        raise HubUnavailableError("ActionHub indisponível")
    detail = "ActionHub recusou a operação de planos"
    if isinstance(payload, dict) and payload.get("error"):
        detail = str(payload["error"])
    raise ConfirmationError(detail)


def _json_body(response: httpx.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        payload = response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
