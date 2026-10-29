"""Adaptador falso para testes. Sem AWS."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from app.modules.ai_orchestration.gateway import GatewayError, ModelRequest, ModelResponse
from app.modules.ai_orchestration.schema import ASSISTIVE_DISCLAIMER


def default_proposal_payload(request: ModelRequest) -> dict[str, Any]:
    evidence = request.user_payload.get("evidence") or []
    allowed = request.user_payload.get("allowed_ingredient_versions") or []
    token = evidence[0]["token"] if evidence else "e1"
    ingredient = allowed[0] if allowed else {"id": None, "code": "farinha"}
    proposal_type = (
        "adapt"
        if request.interaction_type == "adapt_formulation_proposal"
        else "create"
    )
    return {
        "proposal_type": proposal_type,
        "title": "Pão de teste assistivo",
        "objective": request.user_payload.get("objective") or "proposta sintética",
        "summary": "Sugestão assistiva de massa para revisão humana.",
        "justification": "Hipótese técnica a partir das evidências fornecidas.",
        "assistive_disclaimer": ASSISTIVE_DISCLAIMER,
        "items": [
            {
                "sequence": 1,
                "ingredient_version_id": ingredient.get("id"),
                "proposed_ingredient_name": ingredient.get("code") or "farinha",
                "net_quantity_g": "100",
                "correction_factor": "1",
                "is_flour_basis": True,
                "role": "ingredient",
                "rationale": "Sugestão a partir da evidência fornecida.",
                "confidence_note": "baixa, depende de revisão humana",
                "cited_evidence_tokens": [token] if evidence else [],
                "measurement_unit_code": "g",
            }
        ],
        "steps": [
            {
                "sequence": 1,
                "title": "Misturar",
                "instructions": "Misturar os ingredientes sugeridos.",
                "duration_seconds": 300,
                "temperature_celsius": "24",
                "rationale": "Etapa sugerida, não é comando executável.",
                "cited_evidence_tokens": [token] if evidence else [],
            }
        ],
        "assumptions": ["Prévia assistiva; motores determinísticos calculam depois."],
        "unresolved_questions": [],
        "warnings": [ASSISTIVE_DISCLAIMER],
        "cited_evidence_tokens": [token] if evidence else [],
    }


class FakeModelGateway:
    def __init__(
        self,
        handler: Callable[[ModelRequest], dict[str, Any]] | None = None,
        *,
        error: GatewayError | None = None,
        model_id: str = "fake-model",
        region: str = "us-east-1",
    ) -> None:
        self.handler = handler or default_proposal_payload
        self.error = error
        self.model_id = model_id
        self.region = region
        self.last_request: ModelRequest | None = None

    def complete(self, request: ModelRequest) -> ModelResponse:
        started = perf_counter()
        self.last_request = request
        if self.error is not None:
            raise self.error
        content = self.handler(request)
        latency_ms = int((perf_counter() - started) * 1000)
        return ModelResponse(
            content=content,
            provider="fake",
            model_id=self.model_id,
            region=self.region,
            input_token_count=12,
            output_token_count=34,
            stop_reason="end_turn",
            latency_ms=latency_ms,
            structured_output_mode="json_schema",
        )
