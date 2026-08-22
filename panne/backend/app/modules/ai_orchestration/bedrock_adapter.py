"""Adaptador Bedrock Claude. Único módulo autorizado a importar boto3."""

from __future__ import annotations

import json
import time
from typing import Any

from app.modules.ai_orchestration.gateway import GatewayError, ModelRequest, ModelResponse
from app.modules.ai_orchestration.settings import BedrockSettings, load_bedrock_settings

TRANSIENT_CODES = frozenset(
    {"ThrottlingException", "ServiceUnavailableException", "ModelTimeoutException"}
)
MAX_TRANSIENT_RETRIES = 2


class BedrockClaudeGateway:
    def __init__(
        self,
        *,
        client: Any | None = None,
        settings: BedrockSettings | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._client = client
        self._settings = settings
        self._sleep = sleep

    def _settings_or_load(self) -> BedrockSettings:
        return self._settings or load_bedrock_settings()

    def _runtime_client(self, settings: BedrockSettings) -> Any:
        if self._client is not None:
            client = self._client
        else:
            try:
                import boto3
            except ImportError as exc:
                raise GatewayError("sdk_ausente") from exc
            client = boto3.client("bedrock-runtime", region_name=settings.region)
        endpoint = getattr(getattr(client, "meta", None), "endpoint_url", "") or ""
        if "bedrock-mantle" in endpoint:
            raise GatewayError("endpoint_mantle_proibido")
        return client

    def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings_or_load()
        if settings.structured_output_mode == "unsupported":
            raise GatewayError("structured_output_unsupported")
        client = self._runtime_client(settings)
        kwargs = self._converse_kwargs(request, settings)
        started = time.perf_counter()
        raw = self._converse_with_retry(client, kwargs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        content = self._extract_json(raw)
        usage = raw.get("usage") or {}
        return ModelResponse(
            content=content,
            provider="bedrock",
            model_id=settings.model_id,
            region=settings.region,
            input_token_count=usage.get("inputTokens"),
            output_token_count=usage.get("outputTokens"),
            stop_reason=str(raw.get("stopReason") or "unknown"),
            latency_ms=latency_ms,
            structured_output_mode=settings.structured_output_mode,
        )

    def _converse_kwargs(self, request: ModelRequest, settings: BedrockSettings) -> dict[str, Any]:
        payload = json.dumps(request.user_payload, ensure_ascii=False, sort_keys=True)
        kwargs: dict[str, Any] = {
            "modelId": settings.model_id,
            "system": [{"text": request.system_prompt}],
            "messages": [{"role": "user", "content": [{"text": payload}]}],
            "inferenceConfig": {
                "maxTokens": settings.max_tokens,
                "temperature": settings.temperature,
            },
        }
        if settings.guardrail_id:
            kwargs["guardrailConfig"] = {
                "guardrailIdentifier": settings.guardrail_id,
                "guardrailVersion": settings.guardrail_version or "DRAFT",
            }
        schema = json.dumps(request.output_schema, ensure_ascii=False)
        if settings.structured_output_mode == "json_schema":
            kwargs["outputConfig"] = {
                "textFormat": {
                    "type": "json_schema",
                    "structure": {
                        "jsonSchema": {
                            "schema": schema,
                            "name": request.schema_name,
                            "description": "Contrato estruturado da Panne",
                        }
                    },
                }
            }
        elif settings.structured_output_mode == "tool_schema":
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": request.schema_name,
                            "description": "Devolver a proposta no schema da Panne",
                            "inputSchema": {"json": request.output_schema},
                            "strict": True,
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": request.schema_name}},
            }
        return kwargs

    def _converse_with_retry(self, client: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
        last_error: GatewayError | None = None
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                return client.converse(**kwargs)
            except Exception as exc:
                mapped = _map_bedrock_error(exc)
                if mapped.error_code in TRANSIENT_CODES and attempt < MAX_TRANSIENT_RETRIES:
                    last_error = mapped
                    self._sleep(0.1 * (3**attempt))
                    continue
                raise mapped from exc
        raise last_error or GatewayError("falha_transiente")

    def _extract_json(self, raw: dict[str, Any]) -> dict[str, Any]:
        stop = str(raw.get("stopReason") or "")
        if stop == "max_tokens":
            raise GatewayError("saida_truncada")
        output = raw.get("output") or {}
        message = output.get("message") or {}
        blocks = message.get("content") or []
        for block in blocks:
            if "toolUse" in block:
                tool_input = block["toolUse"].get("input")
                if isinstance(tool_input, dict):
                    return tool_input
                raise GatewayError("schema_invalido")
            text = block.get("text")
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise GatewayError("schema_invalido") from exc
            if not isinstance(parsed, dict):
                raise GatewayError("schema_invalido")
            return parsed
        raise GatewayError("resposta_vazia")


class _MappedError(GatewayError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.error_code = code


def _map_bedrock_error(exc: Exception) -> _MappedError:
    name = exc.__class__.__name__
    text = str(exc)
    if "AccessDenied" in name or "AccessDenied" in text:
        return _MappedError("AccessDeniedException")
    if "Throttl" in name or "Throttl" in text:
        return _MappedError("ThrottlingException")
    if "Timeout" in name or "timeout" in text.lower():
        return _MappedError("ModelTimeoutException")
    if "Validation" in name or "Validation" in text:
        return _MappedError("ValidationException")
    if "NotReady" in name or "unavailable" in text.lower():
        return _MappedError("ServiceUnavailableException")
    return _MappedError(name or "bedrock_error")
