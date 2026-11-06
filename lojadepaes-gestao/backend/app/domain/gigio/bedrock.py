"""Chamada invoke_model. Único lugar do Gestão que importa boto3."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from app.domain.gigio.gateway import ChatRequest, ChatResponse, GatewayError
from app.domain.gigio.settings import GigioModelSettings, load_gigio_model_settings

ANTHROPIC_VERSION = "bedrock-2023-05-31"
TIMEOUT_S = 30


class BedrockGateway:
    def __init__(self, *, client: Any | None = None, settings: GigioModelSettings | None = None) -> None:
        self._client = client
        self._settings = settings

    def complete(self, request: ChatRequest) -> ChatResponse:
        settings = self._settings or load_gigio_model_settings()
        client = self._client or self._runtime(settings)
        body = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": min(request.max_tokens, settings.max_tokens),
            "temperature": settings.temperature,
            "system": request.system_prompt,
            "messages": [{"role": turn.role, "content": turn.text} for turn in request.messages],
            "tools": request.tools,
            "tool_choice": {"type": "tool", "name": "sugerir_receita"},
        }
        started = time.perf_counter()
        try:
            response = client.invoke_model(
                modelId=settings.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code") or type(exc).__name__
            raise GatewayError(code, "O Gigio não conseguiu responder agora.") from exc
        latency = int((time.perf_counter() - started) * 1000)
        raw_body = response.get("body")
        if hasattr(raw_body, "read"):
            raw = json.loads(raw_body.read())
        elif isinstance(raw_body, (bytes, bytearray)):
            raw = json.loads(raw_body)
        else:
            raw = dict(raw_body or {})
        texto, ferramentas = _extrair(raw)
        uso = raw.get("usage") or {}
        return ChatResponse(
            text=texto,
            tool_use=ferramentas,
            stop_reason=str(raw.get("stop_reason") or "end_turn"),
            input_tokens=_int(uso, "input_tokens"),
            output_tokens=_int(uso, "output_tokens"),
            latency_ms=latency,
            provider="bedrock",
            model_id=settings.model_id,
            region=settings.region,
        )

    def _runtime(self, settings: GigioModelSettings) -> Any:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise GatewayError("sdk_ausente") from exc
        return boto3.client(
            "bedrock-runtime",
            region_name=settings.region,
            aws_access_key_id=os.environ.get("GESTAO_GIGIO_AWS_ACCESS_KEY_ID", "").strip(),
            aws_secret_access_key=os.environ.get("GESTAO_GIGIO_AWS_SECRET_ACCESS_KEY", "").strip(),
            config=Config(connect_timeout=8, read_timeout=TIMEOUT_S, retries={"max_attempts": 1}),
        )


def _extrair(raw: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    textos: list[str] = []
    ferramentas: list[dict[str, Any]] = []
    for bloco in raw.get("content") or []:
        if not isinstance(bloco, dict):
            continue
        if bloco.get("type") == "text":
            textos.append(str(bloco.get("text") or ""))
        if bloco.get("type") == "tool_use":
            ferramentas.append(
                {"id": bloco.get("id") or "tool", "name": bloco.get("name"), "input": bloco.get("input") or {}}
            )
    return "".join(textos).strip(), ferramentas


def _int(uso: dict[str, Any], chave: str) -> int | None:
    valor = uso.get(chave)
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None
