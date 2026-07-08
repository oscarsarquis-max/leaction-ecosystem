"""Cliente AWS Bedrock — mesmo contrato do PanelDX, sem dependência de código externo."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from botocore.config import Config

# Mesmo inference profile usado no PanelDX (Claude 3.5 Sonnet 20240620 foi descontinuado).
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_BOTO_CONFIG = Config(
    connect_timeout=8,
    read_timeout=45,
    retries={"max_attempts": 1},
)
ANTHROPIC_VERSION = "bedrock-2023-05-31"


def _bedrock_ssl_verify_enabled() -> bool:
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def get_bedrock_runtime_client():
    verify = _bedrock_ssl_verify_enabled()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=BEDROCK_BOTO_CONFIG,
    )


def extrair_json_resposta(texto: str) -> dict[str, Any]:
    if not texto:
        raise ValueError("Resposta vazia do modelo.")
    limpo = texto.strip()
    cerca = re.match(r"^```(?:json)?\s*(.*?)\s*```$", limpo, re.DOTALL | re.IGNORECASE)
    if cerca:
        limpo = cerca.group(1).strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find("{")
        fim = limpo.rfind("}")
        if inicio != -1 and fim > inicio:
            return json.loads(limpo[inicio : fim + 1])
        raise


def invocar_claude(
    *,
    user_content: str,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """Invoca Claude via Bedrock e devolve o texto da resposta."""
    body: dict[str, Any] = {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_content}],
    }
    if system:
        body["system"] = system

    bedrock = get_bedrock_runtime_client()
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(response["body"].read())
    return str(payload["content"][0]["text"] or "").strip()


def testar_conexao() -> dict[str, Any]:
    """Ping mínimo ao Bedrock (útil para diagnóstico local)."""
    texto = invocar_claude(user_content="Responda apenas: ok", max_tokens=10)
    return {
        "ok": True,
        "model_id": BEDROCK_MODEL_ID,
        "region": BEDROCK_REGION,
        "resposta": texto,
    }
