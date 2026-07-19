"""Observabilidade eSIM — logs estruturados + CloudWatch."""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

_CLOUDWATCH_ENABLED = os.environ.get("ESIM_CLOUDWATCH_ENABLED", os.environ.get("BASEMOBILE_CLOUDWATCH_ENABLED", "1")).lower() in (
    "1",
    "true",
    "yes",
)
_LOG_GROUP = os.environ.get("ESIM_CW_LOG_GROUP", os.environ.get("BASEMOBILE_CW_LOG_GROUP", "/paneldx/esim"))
_REGION = os.environ.get("ESIM_CW_REGION") or os.environ.get("AWS_REGION", "us-east-1")
_cw_client = None
_cw_sequence_tokens: dict[str, str | None] = {}


def _esim_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _esim_emit_structured(level: str, event: str, payload: dict[str, Any]) -> None:
    entry = {
        "ts": _esim_utc_now(),
        "level": level,
        "event": event,
        "service": "esim",
        **payload,
    }
    print(json.dumps(entry, ensure_ascii=False), file=sys.stderr)


def _esim_get_cw_client():
    global _cw_client
    if _cw_client is None:
        import boto3

        _cw_client = boto3.client("logs", region_name=_REGION)
    return _cw_client


def _esim_put_cloudwatch(stream: str, message: dict[str, Any]) -> None:
    if not _CLOUDWATCH_ENABLED:
        return
    try:
        client = _esim_get_cw_client()
        try:
            client.create_log_group(logGroupName=_LOG_GROUP)
        except client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception:
            pass

        try:
            client.create_log_stream(logGroupName=_LOG_GROUP, logStreamName=stream)
        except client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception:
            pass

        token = _cw_sequence_tokens.get(stream)
        if token is None:
            try:
                resp = client.describe_log_streams(
                    logGroupName=_LOG_GROUP,
                    logStreamNamePrefix=stream,
                    limit=1,
                )
                streams = resp.get("logStreams") or []
                if streams and streams[0].get("logStreamName") == stream:
                    token = streams[0].get("uploadSequenceToken")
            except Exception:
                token = None

        kwargs: dict[str, Any] = {
            "logGroupName": _LOG_GROUP,
            "logStreamName": stream,
            "logEvents": [
                {
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "message": json.dumps(message, ensure_ascii=False),
                }
            ],
        }
        if token:
            kwargs["sequenceToken"] = token

        resp = client.put_log_events(**kwargs)
        _cw_sequence_tokens[stream] = resp.get("nextSequenceToken")
    except Exception as err:
        _esim_emit_structured(
            "WARN",
            "cloudwatch_put_failed",
            {"stream": stream, "erro": str(err)},
        )


def esim_log_webhook_recebido(payload_resumo: dict[str, Any]) -> None:
    _esim_emit_structured("INFO", "webhook_recebido", payload_resumo)


def esim_log_webhook_processado(resultado: dict[str, Any]) -> None:
    _esim_emit_structured("INFO", "webhook_processado", resultado)
    stream = f"webhook/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    _esim_put_cloudwatch(stream, {"event": "webhook_processado", **resultado})


def esim_log_evento_nao_classificado(
    *,
    id_evento: int,
    codigo_evento: str,
    cliente_id: int,
) -> None:
    payload = {
        "id_evento": id_evento,
        "codigo_evento": codigo_evento,
        "cliente_id": cliente_id,
        "classificacao_status": "nao_classificado",
    }
    _esim_emit_structured("WARN", "evento_nao_classificado", payload)
    stream = f"webhook/nao-classificado/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    _esim_put_cloudwatch(stream, {"event": "evento_nao_classificado", **payload})


def esim_log_webhook_rate_limited(client_key: str, retry_after: int) -> None:
    payload = {"client_key": client_key, "retry_after_s": retry_after}
    _esim_emit_structured("WARN", "webhook_rate_limited", payload)
    _esim_put_cloudwatch("webhook/rate-limit", {"event": "webhook_rate_limited", **payload})


def esim_log_bedrock_sucesso(contexto: dict[str, Any]) -> None:
    _esim_emit_structured("INFO", "bedrock_sucesso", contexto)
    stream = f"bedrock/success/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    _esim_put_cloudwatch(stream, {"event": "bedrock_sucesso", **contexto})


def esim_log_bedrock_dead_letter(
    *,
    codigo_evento: str,
    erro: str,
    contexto: dict[str, Any] | None = None,
    bloco_fallback: str | None = None,
) -> None:
    payload = {
        "codigo_evento": codigo_evento,
        "erro": erro,
        "bloco_fallback": bloco_fallback,
        "contexto": contexto or {},
        "stack": traceback.format_exc() if sys.exc_info()[0] else None,
    }
    _esim_emit_structured("ERROR", "bedrock_dead_letter", payload)
    stream = f"bedrock/dead-letter/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    _esim_put_cloudwatch(stream, {"event": "bedrock_dead_letter", **payload})


# Aliases legados
log_webhook_recebido = esim_log_webhook_recebido
log_webhook_processado = esim_log_webhook_processado
log_webhook_rate_limited = esim_log_webhook_rate_limited
log_bedrock_sucesso = esim_log_bedrock_sucesso
log_bedrock_dead_letter = esim_log_bedrock_dead_letter
