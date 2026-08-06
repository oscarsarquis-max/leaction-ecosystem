"""LLM / Bedrock no School (mesmo padrão do inove4us B2C — boto3 Bedrock Runtime).

Isolado: não importa código do B2C. Usa BEDROCK_* / PEI_BEDROCK_* do .env.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any


BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = (
    os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
)
PEI_BEDROCK_MODEL_ID = (os.environ.get("PEI_BEDROCK_MODEL_ID") or "").strip()
PEI_MAX_TOKENS = int(os.environ.get("PEI_BEDROCK_MAX_TOKENS") or "1024")


def _ssl_verify() -> bool:
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def invoke_text(*, system_prompt: str, user_content: str, max_tokens: int | None = None) -> str:
    """Chama Bedrock (Anthropic Messages API) e devolve texto plano."""
    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        return (
            f"[stub IA] Adapte a metodologia com passos curtos, apoios sensoriais "
            f"e checagens de compreensão. Perfil: {user_content[:240]}"
        )

    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "boto3 não instalado no School — pip install boto3 botocore"
        ) from exc

    verify = _ssl_verify()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    model_id = PEI_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=Config(connect_timeout=8, read_timeout=60, retries={"max_attempts": 1}),
    )
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": int(max_tokens or PEI_MAX_TOKENS),
            "temperature": 0.35,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
    )
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    raw = response.get("body")
    payload = json.loads(raw.read() if hasattr(raw, "read") else raw)
    parts = payload.get("content") or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
    text = "\n".join(t.strip() for t in texts if t.strip()).strip()
    if not text:
        raise RuntimeError("Bedrock retornou resposta vazia")
    return text


def gerar_adaptacao_metodologia_pei(
    *,
    metodologia_nome: str,
    necessidades_especificas: str,
) -> str:
    met = (metodologia_nome or "").strip() or "Metodologia"
    necessidades = (necessidades_especificas or "").strip() or "(sem perfil detalhado)"
    system = (
        "Você é um Psicopedagogo Especialista em Educação Inclusiva e DUA. "
        "Gere passos práticos e acionáveis para adaptar uma metodologia escolar "
        "ao perfil de um aluno com PEI. Responda em português, em tópicos claros, "
        "sem prefácio longo."
    )
    user = (
        f"Como adaptar a metodologia {met} para um aluno com o seguinte "
        f"perfil/PEI: {necessidades}?"
    )
    try:
        return invoke_text(system_prompt=system, user_content=user)
    except Exception as exc:
        print(f"[school-llm] falha gerar PEI×metodologia: {exc}", file=sys.stderr, flush=True)
        raise


def mesclar_metodologia_com_sugestao(
    *,
    texto_canonico: str,
    sugestao_professor: str,
) -> str:
    """Mescla canônico + sugestão do professor em texto unificado (curadoria IA)."""
    canonico = (texto_canonico or "").strip() or "(metodologia padrão vazia)"
    sugestao = (sugestao_professor or "").strip() or "(sem sugestão)"
    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        return (
            f"{canonico}\n\n"
            f"— Adaptação da escola (rascunho IA) —\n"
            f"{sugestao}"
        )
    system = (
        "Aja como um pedagogo. Mescle a metodologia padrão a seguir com a "
        "sugestão de melhoria do professor, criando um texto unificado, claro "
        "e prático. Responda em português, sem prefácio longo — apenas o texto "
        "final pronto para uso pelos professores."
    )
    user = (
        f"[Canônico]\n{canonico}\n\n"
        f"[Sugestão]\n{sugestao}"
    )
    try:
        return invoke_text(system_prompt=system, user_content=user, max_tokens=2048)
    except Exception as exc:
        print(f"[school-llm] falha mesclar metodologia: {exc}", file=sys.stderr, flush=True)
        raise


def adaptar_pei_metodologia_com_ia(
    *,
    metodologia_canonica: str,
    aee_texto_escola: str = "",
    aee_campos_experiencia: str = "",
    pei_experiencias_individuais: str = "",
    sugestao_professor: str = "",
    condicao_categoria: str = "",
    # retrocompat
    matriz_pei_ativa: str = "",
) -> str:
    """Cruza metodologia + AEE (texto + campos) + PEI individual + sugestão → adaptação."""
    canonico = (metodologia_canonica or "").strip() or "(metodologia vazia)"
    aee_txt = (aee_texto_escola or matriz_pei_ativa or "").strip() or "(diretriz AEE ausente)"
    aee_campos = (aee_campos_experiencia or "").strip() or "(campos de experiência ausentes)"
    pei_exp = (pei_experiencias_individuais or "").strip() or "(sem adaptação individual informada)"
    sugestao = (sugestao_professor or "").strip() or "(sem sugestão)"
    cond = (condicao_categoria or "").strip() or "condição não especificada"

    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        return (
            f"Adaptação de plano de aula (rascunho IA) — {cond}\n\n"
            f"Diretriz AEE:\n{aee_txt[:300]}\n\n"
            f"Campos de experiência AEE:\n{aee_campos[:300]}\n\n"
            f"PEI — experiências individuais:\n{pei_exp[:300]}\n\n"
            f"Metodologia:\n{canonico[:300]}\n\n"
            f"Sugestão do professor:\n{sugestao}"
        )

    system = (
        "Aja como psicopedagogo. Cruze a Metodologia Canônica com a diretriz da "
        "escola para a condição (texto AEE + campos de experiência metodológica). "
        "Aplique as necessidades do aluno (experiências adaptadas individuais do PEI). "
        "Incorpore a sugestão do professor para criar a adaptação final do plano de aula. "
        "Responda em português, objetivo e acionável, sem prefácio longo."
    )
    user = (
        f"[Metodologia Canônica]\n{canonico}\n\n"
        f"[Condição / AEE]\n{cond}\n\n"
        f"[AEE.texto_escola]\n{aee_txt}\n\n"
        f"[AEE.campos_experiencia_metodologica]\n{aee_campos}\n\n"
        f"[PEI.experiencias_adaptadas_individuais]\n{pei_exp}\n\n"
        f"[Sugestao.texto]\n{sugestao}"
    )
    try:
        return invoke_text(system_prompt=system, user_content=user, max_tokens=2048)
    except Exception as exc:
        print(f"[school-llm] falha adaptar PEI×metodologia: {exc}", file=sys.stderr, flush=True)
        raise
