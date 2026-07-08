"""Cliente HTTP para notificar o Chamelleon Hub após assinatura do RDO."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

EVENT_TYPE_RDO_FINALIZED = "rdo.finalized"
SOURCE_APP = "diario-obra"


class HubWebhookClient:
    def __init__(self) -> None:
        self.webhook_url = os.getenv(
            "CHAMELLEON_WEBHOOK_URL", "http://127.0.0.1:5010/api/webhooks/gemba/rdo"
        )
        self.api_key = (
            os.getenv("INTEGRATION_API_KEY")
            or os.getenv("GEMBA_WEBHOOK_API_KEY")
            or ""
        )

    def notify_rdo_signed(self, payload: dict[str, Any]) -> None:
        if not self.api_key:
            logger.warning("INTEGRATION_API_KEY ausente — webhook Chamelleon não enviado.")
            return

        headers = {
            "Content-Type": "application/json",
            "X-Integration-Key": self.api_key,
        }
        try:
            response = requests.post(
                self.webhook_url, json=payload, headers=headers, timeout=20
            )
            if not response.ok:
                logger.error(
                    "Webhook Chamelleon falhou: HTTP %s — %s",
                    response.status_code,
                    response.text[:500],
                )
        except requests.RequestException as exc:
            logger.error("Erro ao chamar webhook Chamelleon: %s", exc)
