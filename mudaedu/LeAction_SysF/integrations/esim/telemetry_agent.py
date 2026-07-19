"""Agente IA — hipóteses de negócio a partir de telemetria eSIM."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import boto3
from botocore.config import Config

from integrations.esim.observability import esim_log_bedrock_dead_letter, esim_log_bedrock_sucesso
from integrations.esim.schemas import EsimTelemetryPayload

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_BOTO_CONFIG = Config(
    connect_timeout=8,
    read_timeout=45,
    retries={"max_attempts": 1},
)


def _esim_formatar_blocos_para_prompt(blocos: list[str]) -> str:
    return ", ".join(f'"{b}"' for b in blocos)


def _esim_system_prompt_telemetria(
    *,
    codigo_evento: str,
    dimensao_fixada: str,
    dominio_fixado: str,
    descricao_evento: str,
    blocos_candidatos_restritos: list[str],
) -> str:
    blocos_fmt = _esim_formatar_blocos_para_prompt(blocos_candidatos_restritos)
    return (
        "Aja como IA Master Executiva do MudaEdu. "
        f"O evento {codigo_evento} ocorreu no domínio {dominio_fixado} "
        f"da dimensão {dimensao_fixada}. "
        f"Detalhes técnicos: {descricao_evento}. "
        "Formule uma hipótese de negócio sobre o impacto operacional e financeiro "
        "na instituição de ensino e sugira 3 subtasks de investigação.\n\n"
        "REGRA CRÍTICA: Você deve classificar este incidente obrigatoriamente escolhendo "
        "UM, e apenas um, dos seguintes blocos de atuação autorizados: "
        f"{blocos_fmt}. Não invente nomes de blocos fora desta lista.\n\n"
        'Retorne um JSON restrito às chaves: "hipotese", "subtasks" e "bloco_escolhido".'
    )


def _esim_extrair_json_resposta(texto: str) -> dict[str, Any]:
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


def _esim_resolver_bloco_escolhido(
    bloco_informado: str,
    blocos_permitidos: list[str],
) -> str:
    if not blocos_permitidos:
        return bloco_informado.strip()

    bloco = (bloco_informado or "").strip()
    if bloco in blocos_permitidos:
        return bloco

    bloco_lower = bloco.lower()
    for candidato in blocos_permitidos:
        if candidato.lower() == bloco_lower:
            return candidato
        if bloco_lower and (bloco_lower in candidato.lower() or candidato.lower() in bloco_lower):
            return candidato

    return blocos_permitidos[0]


def _esim_fallback_analise(
    payload: EsimTelemetryPayload,
    *,
    codigo_evento: str,
    dimensao_fixada: str,
    dominio_fixado: str,
    blocos_candidatos_restritos: list[str],
    catalog_id: int | None = None,
) -> dict[str, Any]:
    bloco_escolhido = blocos_candidatos_restritos[0] if blocos_candidatos_restritos else ""
    trafego = (
        f" (tráfego 7d: {payload.trafego_mb_7dias} MB)"
        if payload.trafego_mb_7dias is not None
        else ""
    )
    hipotese = (
        f"[{codigo_evento}] Incidente no domínio {dominio_fixado} ({dimensao_fixada}): "
        f"{payload.descricao_evento} "
        f"Impacto operacional e financeiro provável para o grupo {payload.grupo_acesso} "
        f"em {payload.dominio_acessado}{trafego}. "
        f"Bloco CTDI sugerido: {bloco_escolhido}."
    )
    return {
        "hipotese_negocio": hipotese,
        "hipotese": hipotese,
        "subtasks_investigacao": [
            f"Validar conectividade eSIM/dispositivos do grupo {payload.grupo_acesso}.",
            f"Correlacionar incidente com o bloco '{bloco_escolhido}' e {payload.dominio_acessado}.",
            "Acionar squad responsável para plano de contenção em até 24h.",
        ],
        "subtasks": [
            f"Validar conectividade eSIM/dispositivos do grupo {payload.grupo_acesso}.",
            f"Correlacionar incidente com o bloco '{bloco_escolhido}' e {payload.dominio_acessado}.",
            "Acionar squad responsável para plano de contenção em até 24h.",
        ],
        "bloco_escolhido": bloco_escolhido,
        "codigo_evento_padrao": codigo_evento,
        "dimensao_fixada": dimensao_fixada,
        "dominio_fixado": dominio_fixado,
        "blocos_candidatos_restritos": blocos_candidatos_restritos,
        "catalog_id": catalog_id,
        "fallback": True,
    }


def _esim_normalizar_resposta_ia(
    parsed: dict[str, Any],
    *,
    blocos_candidatos_restritos: list[str],
    codigo_evento: str,
    dimensao_fixada: str,
    dominio_fixado: str,
    catalog_id: int | None = None,
) -> dict[str, Any]:
    hipotese = (
        parsed.get("hipotese")
        or parsed.get("hipotese_negocio")
        or parsed.get("hipotese_de_negocio")
        or ""
    ).strip()

    subtasks_raw = (
        parsed.get("subtasks")
        or parsed.get("subtasks_investigacao")
        or parsed.get("investigacao")
        or []
    )
    subtasks: list[str] = []
    if isinstance(subtasks_raw, list):
        subtasks = [str(s).strip() for s in subtasks_raw if str(s).strip()][:3]
    elif isinstance(subtasks_raw, str) and subtasks_raw.strip():
        subtasks = [subtasks_raw.strip()]

    while len(subtasks) < 3:
        subtasks.append(f"Subtask de investigação #{len(subtasks) + 1} (completar no Kanban).")

    bloco_escolhido = _esim_resolver_bloco_escolhido(
        str(parsed.get("bloco_escolhido") or ""),
        blocos_candidatos_restritos,
    )

    return {
        "hipotese_negocio": hipotese or "Impacto operacional e financeiro a confirmar com telemetria complementar.",
        "subtasks_investigacao": subtasks[:3],
        "hipotese": hipotese,
        "subtasks": subtasks[:3],
        "bloco_escolhido": bloco_escolhido,
        "codigo_evento_padrao": codigo_evento,
        "dimensao_fixada": dimensao_fixada,
        "dominio_fixado": dominio_fixado,
        "blocos_candidatos_restritos": blocos_candidatos_restritos,
        "catalog_id": catalog_id,
        "raw": parsed,
    }


def esim_analisar_anomalia_telemetria(
    payload: EsimTelemetryPayload,
    *,
    codigo_evento: str,
    dimensao_fixada: str,
    dominio_fixado: str,
    blocos_candidatos_restritos: list[str],
    interpretacao_leaction: str | None = None,
    catalog_id: int | None = None,
) -> dict[str, Any]:
    """Invoca Claude via Bedrock com contexto LeAction e retorna hipótese + subtasks + bloco."""
    blocos = list(blocos_candidatos_restritos)
    system_prompt = _esim_system_prompt_telemetria(
        codigo_evento=codigo_evento,
        dimensao_fixada=dimensao_fixada,
        dominio_fixado=dominio_fixado,
        descricao_evento=payload.descricao_evento,
        blocos_candidatos_restritos=blocos,
    )
    user_content = json.dumps(
        {
            "cliente_id": payload.cliente_id,
            "codigo_evento_padrao": codigo_evento,
            "grupo_acesso": payload.grupo_acesso,
            "dominio_acessado": payload.dominio_acessado,
            "titulo_alerta": payload.titulo_alerta,
            "descricao_evento": payload.descricao_evento,
            "status_anomalia": payload.status_anomalia,
            "trafego_mb_7dias": payload.trafego_mb_7dias,
            "variacao_percentual": payload.variacao_percentual,
            "dimensao_fixada": dimensao_fixada,
            "dominio_fixado": dominio_fixado,
            "blocos_candidatos_restritos": blocos,
            "interpretacao_leaction": interpretacao_leaction or "",
        },
        ensure_ascii=False,
    )

    try:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=BEDROCK_REGION,
            config=BEDROCK_BOTO_CONFIG,
        )
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1200,
                "temperature": 0.4,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}],
            }
        )
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        texto_ia = json.loads(response["body"].read())["content"][0]["text"].strip()
        parsed = _esim_extrair_json_resposta(texto_ia)
        result = _esim_normalizar_resposta_ia(
            parsed,
            blocos_candidatos_restritos=blocos,
            codigo_evento=codigo_evento,
            dimensao_fixada=dimensao_fixada,
            dominio_fixado=dominio_fixado,
            catalog_id=catalog_id,
        )
        result["fallback"] = False
        esim_log_bedrock_sucesso(
            {
                "codigo_evento": codigo_evento,
                "bloco_escolhido": result.get("bloco_escolhido"),
                "dominio_fixado": dominio_fixado,
            }
        )
        return result
    except Exception as err:
        print(f"⚠️ [eSIM IA] Fallback local: {err}", file=sys.stderr)
        fb = _esim_fallback_analise(
            payload,
            codigo_evento=codigo_evento,
            dimensao_fixada=dimensao_fixada,
            dominio_fixado=dominio_fixado,
            blocos_candidatos_restritos=blocos,
            catalog_id=catalog_id,
        )
        fb["erro_ia"] = str(err)
        esim_log_bedrock_dead_letter(
            codigo_evento=codigo_evento,
            erro=str(err),
            contexto={
                "cliente_id": payload.cliente_id,
                "dominio_fixado": dominio_fixado,
                "dimensao_fixada": dimensao_fixada,
            },
            bloco_fallback=fb.get("bloco_escolhido"),
        )
        return fb


analisar_anomalia_telemetria = esim_analisar_anomalia_telemetria
