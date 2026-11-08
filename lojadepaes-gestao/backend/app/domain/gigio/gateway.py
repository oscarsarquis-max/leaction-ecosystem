"""Contrato do modelo. O resto do Gestão não fala com a AWS direto."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class GatewayError(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class ChatTurn:
    role: str
    text: str = ""


@dataclass(frozen=True)
class ChatRequest:
    system_prompt: str
    messages: list[ChatTurn]
    tools: list[dict[str, Any]]
    max_tokens: int


@dataclass(frozen=True)
class ChatResponse:
    text: str
    tool_use: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = "end_turn"
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    provider: str = ""
    model_id: str = ""
    region: str = ""


class GigioGateway(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...
