"""Configuração Bedrock do Gigio. Credenciais só na cadeia AWS / env do servidor."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config import Settings


class GigioSettingsError(ValueError):
    """Configuração do modelo incompleta."""


# Região e operação continuam as do Chamelleon (invoke_model, us-east-1).
# Claude Sonnet 4 (20250514) chegou ao fim da vida em 14/10/2026 e a AWS
# responde ResourceNotFoundException. O sucessor ativo da mesma família,
# no mesmo perfil geográfico US, é Claude Sonnet 4.6.
CHAMELLEON_BEDROCK_REGION = "us-east-1"
CHAMELLEON_BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


@dataclass(frozen=True)
class GigioModelSettings:
    region: str
    model_id: str
    max_tokens: int
    temperature: float
    ssl_verify: bool
    guardrail_id: str | None
    guardrail_version: str | None


def load_gigio_model_settings(
    settings: Settings, environ: dict[str, str] | None = None
) -> GigioModelSettings:
    env = environ if environ is not None else os.environ
    region = (
        settings.bedrock_region.strip()
        or env.get("BEDROCK_REGION", "").strip()
        or CHAMELLEON_BEDROCK_REGION
    )
    model_id = (
        settings.bedrock_model_id.strip()
        or env.get("BEDROCK_MODEL_ID", "").strip()
        or CHAMELLEON_BEDROCK_MODEL_ID
    )
    if not region:
        raise GigioSettingsError("região Bedrock não configurada")
    if not model_id:
        raise GigioSettingsError("modelo Bedrock não configurado")
    max_tokens = int(settings.bedrock_max_tokens or env.get("BEDROCK_MAX_TOKENS") or 1024)
    temperature = float(
        settings.bedrock_temperature
        if settings.bedrock_temperature is not None
        else env.get("BEDROCK_TEMPERATURE") or 0.4
    )
    if max_tokens <= 0 or max_tokens > 2048:
        raise GigioSettingsError("BEDROCK_MAX_TOKENS inválido")
    if temperature < 0 or temperature > 1:
        raise GigioSettingsError("BEDROCK_TEMPERATURE inválida")
    guardrail_id = settings.bedrock_guardrail_id.strip() or env.get("BEDROCK_GUARDRAIL_ID", "").strip() or None
    guardrail_version = (
        settings.bedrock_guardrail_version.strip()
        or env.get("BEDROCK_GUARDRAIL_VERSION", "").strip()
        or None
    )
    ssl_raw = env.get("BEDROCK_SSL_VERIFY")
    if ssl_raw is None or not str(ssl_raw).strip():
        ssl_verify = bool(settings.bedrock_ssl_verify)
    else:
        ssl_verify = str(ssl_raw).strip().lower() not in {"0", "false", "no"}
    return GigioModelSettings(
        region=region,
        model_id=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        ssl_verify=ssl_verify,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
    )


def public_model_family(model_id: str) -> str:
    lowered = model_id.lower()
    if "claude" in lowered:
        return "claude"
    if "nova" in lowered:
        return "nova"
    return "bedrock"
