"""Cliente HTTP para o microsserviço Diário de Obra (spoke)."""

from __future__ import annotations

import os
from typing import Any

import requests


class SatelliteClient:
    def __init__(self) -> None:
        self.base_url = (
            os.getenv("DIARIO_OBRA_API_URL", "http://127.0.0.1:6010").rstrip("/")
        )
        self.api_key = (
            os.getenv("INTEGRATION_API_KEY")
            or os.getenv("GEMBA_WEBHOOK_API_KEY")
            or ""
        )

    def _headers(self, *, require_auth: bool = False) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Integration-Key"] = self.api_key
        elif require_auth:
            raise RuntimeError(
                "INTEGRATION_API_KEY não configurada para integrar com o satélite."
            )
        return headers

    def create_rdo_site(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/rdo/sites — endpoint público do satélite (sem API key obrigatória)."""
        url = f"{self.base_url}/api/rdo/sites"
        response = requests.post(
            url, json=payload, headers=self._headers(require_auth=False), timeout=20
        )
        data = response.json() if response.content else {}
        if not response.ok:
            raise RuntimeError(
                data.get("error") or f"Satélite respondeu HTTP {response.status_code}"
            )
        return data.get("site") or data

    def push_daily_goals(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/integration/daily-goals — exige autenticação de integração."""
        url = f"{self.base_url}/api/integration/daily-goals"
        response = requests.post(
            url, json=payload, headers=self._headers(require_auth=True), timeout=30
        )
        data = response.json() if response.content else {}
        if not response.ok:
            raise RuntimeError(
                data.get("error") or f"Satélite respondeu HTTP {response.status_code}"
            )
        return data

    def reopen_rdo_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/integration/logs/reopen — reabre RDO para edição."""
        url = f"{self.base_url}/api/integration/logs/reopen"
        response = requests.post(
            url, json=payload, headers=self._headers(require_auth=True), timeout=30
        )
        data = response.json() if response.content else {}
        if not response.ok:
            raise RuntimeError(
                data.get("error") or f"Satélite respondeu HTTP {response.status_code}"
            )
        return data
