"""Integração IA — AWS Bedrock (Claude), alinhada ao padrão PanelDX."""

from ai.bedrock_client import (
    BEDROCK_MODEL_ID,
    BEDROCK_REGION,
    extrair_json_resposta,
    get_bedrock_runtime_client,
    invocar_claude,
)

__all__ = [
    "BEDROCK_MODEL_ID",
    "BEDROCK_REGION",
    "extrair_json_resposta",
    "get_bedrock_runtime_client",
    "invocar_claude",
]
