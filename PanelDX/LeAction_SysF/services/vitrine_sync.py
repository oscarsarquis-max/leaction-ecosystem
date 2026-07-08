"""Publicação em lote da vitrine CRM → ActionHub (Billing Hub)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import requests


def _hub_gateway_base() -> str:
    return (
        os.environ.get("HUB_GATEWAY_INTERNAL_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).rstrip("/")


def publicar_vitrine_actionhub(
    planos: list[dict[str, Any]],
    *,
    addons: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Envia catálogo ativo ao ActionHub (push) e exige confirmação de recebimento."""
    if not planos:
        raise ValueError("Nenhum plano ativo para publicar na vitrine.")

    sync_id = str(uuid.uuid4())
    payload = {
        "sync_id": sync_id,
        "source": "paneldx",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "planos": planos,
        "addons": addons or [],
    }

    headers = {"Content-Type": "application/json"}
    secret = (os.environ.get("VITRINE_SYNC_SECRET") or "").strip()
    if secret:
        headers["X-PanelDX-Vitrine-Sync"] = secret

    url = f"{_hub_gateway_base()}/v1/vitrine/paneldx/sync"
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json() if response.content else {}

    if not data.get("received"):
        raise RuntimeError(data.get("error") or "ActionHub não confirmou o recebimento da vitrine.")

    return {
        "received": True,
        "sync_id": data.get("sync_id") or sync_id,
        "planos_count": int(data.get("planos_count") or len(planos)),
        "received_at": data.get("received_at"),
        "hub_url": url,
    }
