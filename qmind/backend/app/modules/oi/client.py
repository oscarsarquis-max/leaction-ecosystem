"""Thin HTTP client for QMind OI analyze endpoint — no business rules."""

from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.errors import AppError
from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights, dump_jsonable

ANALYZE_PATH = "/api/v1/organizational-intelligence/analyze"


class OrganizationalIntelligenceClient:
    """POST OrganizationContextInput → OrganizationalInsights over HTTP JSON."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def analyze(self, payload: OrganizationContextInput) -> OrganizationalInsights:
        base = (self._settings.qmind_oi_base_url or "").rstrip("/")
        if not base:
            raise AppError(
                "oi_not_configured",
                "QMind OI base URL is not configured",
                status_code=503,
            )

        url = f"{base}{ANALYZE_PATH}"
        timeout = self._settings.qmind_oi_timeout_seconds
        body = dump_jsonable(payload)

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=body)
        except httpx.TimeoutException as exc:
            raise AppError(
                "oi_timeout",
                "QMind OI request timed out",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "oi_unavailable",
                "QMind OI is unavailable",
                status_code=502,
            ) from exc

        if response.status_code >= 500:
            raise AppError(
                "oi_error",
                "QMind OI returned a server error",
                status_code=502,
            )
        if response.status_code >= 400:
            raise AppError(
                "oi_bad_response",
                "QMind OI rejected the request",
                status_code=502,
            )

        try:
            return OrganizationalInsights.model_validate(response.json())
        except Exception as exc:
            raise AppError(
                "oi_invalid_response",
                "QMind OI returned an invalid OrganizationalInsights payload",
                status_code=502,
            ) from exc
