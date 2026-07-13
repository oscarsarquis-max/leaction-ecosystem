"""Cliente AWS Bedrock (Claude) — Chamelleon."""

from __future__ import annotations

import json
import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# Claude Sonnet 4 via inference profile AWS Bedrock.
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1")


def _bedrock_ssl_verify_enabled() -> bool:
    return os.getenv("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _read_timeout_for_tokens(max_tokens: int) -> int:
    if max_tokens >= 8000:
        return 180
    if max_tokens >= 4000:
        return 120
    return 45


def get_bedrock_client(*, read_timeout: int = 45):
    """Instancia o cliente Bedrock Runtime com credenciais do ambiente."""
    verify = _bedrock_ssl_verify_enabled()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    config = Config(
        connect_timeout=8,
        read_timeout=read_timeout,
        retries={"max_attempts": 2},
    )

    kwargs: dict = {
        "service_name": "bedrock-runtime",
        "region_name": BEDROCK_REGION,
        "config": config,
        "verify": verify,
    }

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client(**kwargs)


def invoke_claude(
    prompt: str,
    max_tokens: int = 1000,
    *,
    system: str | None = None,
    temperature: float = 0.5,
) -> str:
    """Invoca o Claude via Bedrock e retorna o texto da resposta."""
    read_timeout = _read_timeout_for_tokens(max_tokens)
    client = get_bedrock_client(read_timeout=read_timeout)

    body_obj: dict = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body_obj["system"] = system

    body = json.dumps(body_obj)

    try:
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
    except Exception as exc:
        logger.exception("Falha ao invocar Bedrock (%s): %s", BEDROCK_REGION, exc)
        raise RuntimeError(
            f"Falha na comunicação com AWS Bedrock ({BEDROCK_REGION}): {exc}"
        ) from exc

    payload = json.loads(response["body"].read())
    return str(payload["content"][0]["text"]).strip()
