"""Configuração Bedrock. Credenciais vêm da cadeia AWS / .env local."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_ROOT / ".env", override=False)


class BedrockSettingsError(ValueError):
    """Configuração Bedrock incompleta ou inválida."""


@dataclass(frozen=True)
class BedrockSettings:
    region: str
    model_id: str
    max_tokens: int
    temperature: float
    guardrail_id: str | None
    guardrail_version: str | None
    structured_output_mode: str


def load_bedrock_settings(environ: dict[str, str] | None = None) -> BedrockSettings:
    env = environ if environ is not None else os.environ
    region = (
        env.get("BEDROCK_REGION")
        or env.get("AWS_REGION")
        or env.get("AWS_DEFAULT_REGION")
        or ""
    ).strip()
    model_id = (env.get("BEDROCK_MODEL_ID") or "").strip()
    if not region:
        raise BedrockSettingsError("AWS_REGION ou BEDROCK_REGION não configurada")
    if not model_id:
        raise BedrockSettingsError("BEDROCK_MODEL_ID não configurado")
    max_tokens = int(env.get("BEDROCK_MAX_TOKENS") or "4096")
    temperature = float(env.get("BEDROCK_TEMPERATURE") or "0")
    if max_tokens <= 0:
        raise BedrockSettingsError("BEDROCK_MAX_TOKENS inválido")
    if temperature < 0 or temperature > 1:
        raise BedrockSettingsError("BEDROCK_TEMPERATURE inválida")
    guardrail_id = (env.get("BEDROCK_GUARDRAIL_ID") or "").strip() or None
    guardrail_version = (env.get("BEDROCK_GUARDRAIL_VERSION") or "").strip() or None
    mode = (env.get("BEDROCK_STRUCTURED_OUTPUT_MODE") or "json_schema").strip()
    if mode not in {"json_schema", "tool_schema", "unsupported"}:
        raise BedrockSettingsError("modo de saída estruturada inválido")
    return BedrockSettings(
        region=region,
        model_id=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
        structured_output_mode=mode,
    )
