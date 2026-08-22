"""Porta ModelGateway. Sem boto3 e sem modelo fixo no domínio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class GatewayError(RuntimeError):
    """Falha normalizada do gateway de modelo."""


@dataclass(frozen=True)
class ModelRequest:
    interaction_type: str
    system_prompt: str
    user_payload: dict[str, Any]
    output_schema: dict[str, Any]
    schema_name: str


@dataclass(frozen=True)
class ModelResponse:
    content: dict[str, Any]
    provider: str
    model_id: str
    region: str
    input_token_count: int | None
    output_token_count: int | None
    stop_reason: str
    latency_ms: int
    structured_output_mode: str


class ModelGateway(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse:
        """Recebe solicitação estruturada e devolve JSON validável."""
