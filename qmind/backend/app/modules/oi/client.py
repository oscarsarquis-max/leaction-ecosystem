"""Thin HTTP client for QMind OI endpoints — no business rules."""

from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.errors import AppError
from app.modules.improvement_cases.problem_schemas import (
    ProblemAnalysis,
    ProblemContextInput,
    dump_jsonable as dump_problem,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceInput,
    ExecutionIntelligenceResult,
    dump_jsonable as dump_execution,
)
from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights, dump_jsonable

ANALYZE_PATH = "/api/v1/organizational-intelligence/analyze"
PROBLEM_ANALYSIS_PATH = "/api/v1/organizational-intelligence/problem-analysis"
EXECUTION_INTELLIGENCE_PATH = (
    "/api/v1/organizational-intelligence/execution-intelligence"
)


class OrganizationalIntelligenceClient:
    """HTTP JSON client for QMind OI public endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _post_json(self, path: str, body: dict) -> dict:
        base = (self._settings.qmind_oi_base_url or "").rstrip("/")
        if not base:
            raise AppError(
                "oi_not_configured",
                "QMind OI base URL is not configured",
                status_code=503,
            )

        url = f"{base}{path}"
        timeout = self._settings.qmind_oi_timeout_seconds

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
            return response.json()
        except Exception as exc:
            raise AppError(
                "oi_invalid_response",
                "QMind OI returned invalid JSON",
                status_code=502,
            ) from exc

    def analyze(self, payload: OrganizationContextInput) -> OrganizationalInsights:
        raw = self._post_json(ANALYZE_PATH, dump_jsonable(payload))
        try:
            return OrganizationalInsights.model_validate(raw)
        except Exception as exc:
            raise AppError(
                "oi_invalid_response",
                "QMind OI returned an invalid OrganizationalInsights payload",
                status_code=502,
            ) from exc

    def analyze_problem(self, payload: ProblemContextInput) -> ProblemAnalysis:
        raw = self._post_json(PROBLEM_ANALYSIS_PATH, dump_problem(payload))
        try:
            return ProblemAnalysis.model_validate(raw)
        except Exception as exc:
            raise AppError(
                "oi_invalid_response",
                "QMind OI returned an invalid ProblemAnalysis payload",
                status_code=502,
            ) from exc

    def analyze_execution(
        self, payload: ExecutionIntelligenceInput
    ) -> ExecutionIntelligenceResult:
        raw = self._post_json(EXECUTION_INTELLIGENCE_PATH, dump_execution(payload))
        try:
            return ExecutionIntelligenceResult.model_validate(raw)
        except Exception as exc:
            raise AppError(
                "oi_invalid_response",
                "QMind OI returned an invalid ExecutionIntelligenceResult payload",
                status_code=502,
            ) from exc
