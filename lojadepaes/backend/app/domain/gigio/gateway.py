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
    tool_use: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ChatRequest:
    system_prompt: str
    messages: list[ChatTurn]
    tools: list[dict[str, Any]]
    max_tokens: int


@dataclass(frozen=True)
class ChatResponse:
    text: str
    tool_use: list[dict[str, Any]]
    stop_reason: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    provider: str
    model_id: str
    region: str


class GigioGateway(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...
