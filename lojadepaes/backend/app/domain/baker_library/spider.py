"""Consumidor EXPERIENCE da Loja: Loja → capacidades Spider → Hub.

Não chama a API financeira do Hub. Timeout do Spider não prova falha da operação.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.actionhub_client import HubUnavailableError

OBJECTIVES = {
    "LIST_HUB_CATALOG": "LIST_LOJA_PLANS",
    "GET_HUB_ENTITLEMENTS": "GET_LOJA_ENTITLEMENTS",
    "LIST_HUB_SUBSCRIPTIONS": "LIST_LOJA_SUBSCRIPTIONS",
    "START_HUB_CATALOG_CHECKOUT": "START_LOJA_CHECKOUT",
    "CANCEL_HUB_SUBSCRIPTION": "CANCEL_LOJA_SUBSCRIPTION",
    "RESERVE_HUB_CREDITS": "RESERVE_LOJA_CREDITS",
    "CONFIRM_HUB_CREDITS": "CONFIRM_LOJA_CREDITS",
    "RELEASE_HUB_CREDITS": "RELEASE_LOJA_CREDITS",
}


def invoke(
    settings: Settings,
    capability_id: str,
    inputs: dict[str, Any],
    *,
    correlation_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    objective = OBJECTIVES.get(capability_id)
    if not objective:
        raise HubUnavailableError("capacidade da Biblioteca não reconhecida")
    base = str(getattr(settings, "spider_base_url", "") or "").strip().rstrip("/")
    satellite = str(getattr(settings, "spider_satellite_id", "") or "lojadepaes").strip()
    secret = str(getattr(settings, "spider_satellite_secret", "") or "").strip()
    if not base or not secret:
        raise HubUnavailableError("Spider sem destino ou credencial de satélite")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "contractVersion": "1.5",
        "messageId": f"msg-{uuid.uuid4()}",
        "correlationId": correlation_id[:80],
        "satelliteId": satellite,
        "satelliteRole": "EXPERIENCE",
        "interactionType": "QUERY_STATUS",
        "createdAt": now,
        "idempotencyKey": idempotency_key[:80],
        "purpose": "LOJA_BIBLIOTECA",
        "objective": {"text": objective, "origin": "SATELLITE_GOVERNED", "declaredAt": now},
        "dataClassification": "INTERNAL",
        "responseChannel": "SYNC",
        "context": {
            "snapshot": {
                "schemaVersion": "1.5",
                "classification": "INTERNAL",
                "nonPersonal": True,
                "provenance": {
                    "sourceType": "SATELLITE_GOVERNED",
                    "sourceId": "LOJADEPAES_BIBLIOTECA_V1",
                    "sourceTimestamp": now,
                    "captureMethod": "SERVER_REGISTRY",
                    "trustLevel": "GOVERNED",
                },
                "selectedContribution": "GOVERNED_SOURCE",
                "contributions": [
                    {
                        "role": "GOVERNED_SOURCE",
                        "sourceType": "SATELLITE_GOVERNED",
                        "sourceId": "LOJADEPAES_BIBLIOTECA_V1",
                        "sourceTimestamp": now,
                        "captureMethod": "SERVER_REGISTRY",
                        "trustLevel": "GOVERNED",
                        "used": True,
                        "elements": {"theme": "biblioteca_plans"},
                    }
                ],
                "attributes": {
                    "channel": "LOJADEPAES",
                    "theme": "biblioteca_plans",
                    "appId": settings.actionhub_app_id,
                    "purposeVersion": "biblioteca-v1",
                },
            }
        },
        "extensions": {"biblioteca": _biblioteca_extension(settings, inputs)},
    }
    timeout = min(float(getattr(settings, "spider_timeout_seconds", 8) or 8), 12)
    try:
        response = httpx.post(
            f"{base}/v1/satellites/interactions",
            json=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Spider-Satellite-Id": satellite,
                "X-Spider-Satellite-Secret": secret,
                "X-Correlation-ID": correlation_id,
            },
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise HubUnavailableError("timeout ao consultar a Spider") from exc
    except httpx.HTTPError as exc:
        raise HubUnavailableError("falha ao consultar a Spider") from exc
    if response.status_code >= 500:
        raise HubUnavailableError("Spider indisponível")
    if response.status_code >= 400:
        raise HubUnavailableError("Spider recusou a interação da Biblioteca")
    payload = response.json() if response.content else {}
    if not isinstance(payload, dict):
        raise HubUnavailableError("resposta inválida da Spider")
    if payload.get("status") != "READY" or payload.get("capabilityId") != capability_id:
        raise HubUnavailableError(
            str(payload.get("explanation") or "capacidade da Biblioteca indisponível")
        )
    summary = payload.get("resultSummary")
    return summary if isinstance(summary, dict) else {}


def _biblioteca_extension(settings: Settings, inputs: dict[str, Any]) -> dict[str, Any]:
    extension: dict[str, Any] = {"appId": settings.actionhub_app_id}
    for key, dest in (
        ("subject_id", "subjectId"),
        ("sku", "sku"),
        ("operation_id", "operationId"),
        ("amount", "amount"),
        ("return_origin", "returnOrigin"),
        ("return_to", "returnTo"),
    ):
        value = inputs.get(key)
        if value is None or value == "":
            continue
        extension[dest] = value
    return extension
