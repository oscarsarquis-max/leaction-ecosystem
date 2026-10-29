"""Adaptador Bedrock invoke_model (contrato Chamelleon). Único módulo da Loja que importa boto3 para modelo."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from app.domain.gigio.gateway import ChatRequest, ChatResponse, ChatTurn, GatewayError
from app.domain.gigio.settings import GigioModelSettings, load_gigio_model_settings

TRANSIENT = frozenset({"ThrottlingException", "ServiceUnavailableException", "ModelTimeoutException"})
MAX_RETRIES = 2
ANTHROPIC_VERSION = "bedrock-2023-05-31"


class BedrockGigioGateway:
    def __init__(self, *, client: Any | None = None, settings: GigioModelSettings | None = None) -> None:
        self._client = client
        self._settings = settings

    def complete(self, request: ChatRequest) -> ChatResponse:
        from app.core.config import get_settings

        settings = self._settings or load_gigio_model_settings(get_settings())
        client = self._runtime(settings)
        body = invoke_body(request, settings)
        started = time.perf_counter()
        raw = self._invoke(client, settings.model_id, body)
        latency = int((time.perf_counter() - started) * 1000)
        text, tool_use, stop = extract_invoke(raw)
        usage = raw.get("usage") or {}
        return ChatResponse(
            text=text,
            tool_use=tool_use,
            stop_reason=stop,
            input_tokens=_usage_int(usage, "input_tokens", "inputTokens"),
            output_tokens=_usage_int(usage, "output_tokens", "outputTokens"),
            latency_ms=latency,
            provider="bedrock",
            model_id=settings.model_id,
            region=settings.region,
        )

    def _runtime(self, settings: GigioModelSettings) -> Any:
        if self._client is not None:
            client = self._client
        else:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise GatewayError("sdk_ausente") from exc
            from app.core.config import get_settings

            app = get_settings()
            access_key, secret_key = _runtime_credentials(app)
            kwargs: dict[str, Any] = {
                "service_name": "bedrock-runtime",
                "region_name": settings.region,
                "config": Config(
                    connect_timeout=8,
                    read_timeout=_read_timeout(settings.max_tokens),
                    retries={"max_attempts": 2},
                ),
                "verify": settings.ssl_verify,
            }
            if not settings.ssl_verify:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            if access_key and secret_key:
                kwargs["aws_access_key_id"] = access_key
                kwargs["aws_secret_access_key"] = secret_key
            client = boto3.client(**kwargs)
        endpoint = getattr(getattr(client, "meta", None), "endpoint_url", "") or ""
        if "bedrock-mantle" in endpoint:
            raise GatewayError("endpoint_mantle_proibido")
        return client

    def _invoke(self, client: Any, model_id: str, body: dict[str, Any]) -> dict[str, Any]:
        last: GatewayError | None = None
        payload = json.dumps(body)
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=payload,
                )
                raw_body = response.get("body")
                if hasattr(raw_body, "read"):
                    return json.loads(raw_body.read())
                if isinstance(raw_body, (bytes, bytearray)):
                    return json.loads(raw_body)
                if isinstance(raw_body, str):
                    return json.loads(raw_body)
                return dict(raw_body or {})
            except Exception as exc:
                code = getattr(exc, "response", {}).get("Error", {}).get("Code") or type(exc).__name__
                last = GatewayError(code)
                if code not in TRANSIENT or attempt >= MAX_RETRIES:
                    raise last from exc
                time.sleep(0.2 * (attempt + 1))
        raise last or GatewayError("indisponivel")


def invoke_body(request: ChatRequest, settings: GigioModelSettings) -> dict[str, Any]:
    body: dict[str, Any] = {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": min(request.max_tokens, settings.max_tokens),
        "temperature": settings.temperature,
        "system": request.system_prompt,
        "messages": anthropic_messages(request.messages),
    }
    if request.tools:
        body["tools"] = anthropic_tools(request.tools)
    return body


def anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for spec in tools:
        schema = spec.get("input_schema")
        if not isinstance(schema, dict):
            wrapped = spec.get("inputSchema") or {}
            schema = wrapped.get("json") if isinstance(wrapped, dict) else None
        if not isinstance(schema, dict):
            schema = {"type": "object", "properties": {}}
        converted.append(
            {
                "name": spec["name"],
                "description": spec.get("description") or "",
                "input_schema": schema,
            }
        )
    return converted


def anthropic_messages(turns: list[ChatTurn]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in turns:
        if turn.role == "user" and turn.tool_results:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": item.get("id") or "tool",
                            "content": json.dumps(item.get("content") or {}, ensure_ascii=False),
                        }
                        for item in turn.tool_results
                    ],
                }
            )
            continue
        if turn.role == "assistant" and turn.tool_use:
            content: list[dict[str, Any]] = []
            if turn.text:
                content.append({"type": "text", "text": turn.text})
            for item in turn.tool_use:
                content.append(
                    {
                        "type": "tool_use",
                        "id": item.get("id") or "tool",
                        "name": item.get("name"),
                        "input": item.get("input") or {},
                    }
                )
            messages.append({"role": "assistant", "content": content})
            continue
        messages.append({"role": turn.role, "content": turn.text or ""})
    return messages


def extract_invoke(raw: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
    text_parts: list[str] = []
    tools: list[dict[str, Any]] = []
    content = raw.get("content")
    if isinstance(content, str):
        text_parts.append(content)
        content = []
    for block in content or []:
        if isinstance(block, str):
            text_parts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text" or ("text" in block and kind not in {"tool_use", "thinking"}):
            text_parts.append(str(block.get("text") or ""))
        if kind == "tool_use":
            tools.append(
                {
                    "id": block.get("id") or "tool",
                    "name": block.get("name"),
                    "input": block.get("input") or {},
                }
            )
    stop = str(raw.get("stop_reason") or raw.get("stopReason") or "end_turn")
    return "".join(text_parts).strip(), tools, stop


def _runtime_credentials(app: Any) -> tuple[str, str]:
    access = (getattr(app, "aws_access_key_id", "") or "").strip() or os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret = (getattr(app, "aws_secret_access_key", "") or "").strip() or os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    return access, secret


def _read_timeout(max_tokens: int) -> int:
    if max_tokens >= 8000:
        return 180
    if max_tokens >= 4000:
        return 120
    return 45


def _usage_int(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def parse_json_object(value: str) -> dict[str, Any]:
    return json.loads(value)
