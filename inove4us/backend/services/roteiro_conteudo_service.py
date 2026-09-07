"""Conteúdo sugerido da disciplina — 1 geração IA por tema×nível, depois cache.

Metodologia e AEE NÃO passam por aqui (são retrieval em outro endpoint).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from typing import Any

import boto3
from botocore.config import Config
from psycopg2.extras import RealDictCursor

from db import get_conn
from prompts.roteiro_conteudo import build_system_prompt, build_user_prompt

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
ROTEIRO_MAX_TOKENS = int(os.environ.get("ROTEIRO_BEDROCK_MAX_TOKENS") or "2048")

_ensured = False


def cache_key(*, fonte: str, identidade: str, nivel_turma: str) -> str:
    raw = f"{(fonte or '').strip().lower()}|{(identidade or '').strip().lower()}|{(nivel_turma or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def identidade_tema(*, fonte: str, habilidade_codigo: str, tema: str) -> str:
    if (fonte or "").strip().lower() == "bncc" and (habilidade_codigo or "").strip():
        return habilidade_codigo.strip().upper()
    return re.sub(r"\s+", " ", (tema or "").strip())


def montar_texto(conteudo: dict[str, Any]) -> str:
    linhas: list[str] = []

    def bloco(titulo: str, valor: Any) -> None:
        if isinstance(valor, list):
            itens = [str(x).strip() for x in valor if str(x).strip()]
            if not itens:
                return
            linhas.append(titulo)
            for it in itens:
                linhas.append(f"• {it}")
            linhas.append("")
            return
        txt = str(valor or "").strip()
        if not txt:
            return
        linhas.append(titulo)
        linhas.append(txt)
        linhas.append("")

    bloco("Pontos-chave", conteudo.get("pontos_chave"))
    bloco("Vocabulário", conteudo.get("vocabulario"))
    bloco("Equívoco comum a evitar", conteudo.get("equivoco_comum"))
    bloco("Analogia (idade/ano da turma)", conteudo.get("analogia"))
    bloco("Pergunta de abertura", conteudo.get("pergunta_abertura"))
    perguntas = conteudo.get("perguntas_alunos") or []
    if isinstance(perguntas, list) and perguntas:
        linhas.append("Perguntas prováveis dos alunos")
        for p in perguntas:
            if not isinstance(p, dict):
                continue
            q = str(p.get("pergunta") or "").strip()
            a = str(p.get("resposta") or "").strip()
            if q:
                linhas.append(f"• {q}")
            if a:
                linhas.append(f"  → {a}")
        linhas.append("")
    bloco("Checklist de material", conteudo.get("checklist_material"))
    return "\n".join(linhas).strip()


def montar_passos_com_conteudo(passos: list[dict], conteudo: dict[str, Any] | None) -> list[dict]:
    """Montagem de texto (zero IA): ancora o 1º passo no conteúdo já gerado."""
    data = conteudo if isinstance(conteudo, dict) else {}
    notas = []
    if data.get("analogia"):
        notas.append(f"Analogia deste tema: {data['analogia']}")
    if data.get("pergunta_abertura"):
        notas.append(f"Abertura: {data['pergunta_abertura']}")
    note = " ".join(notas)
    out = []
    for i, passo in enumerate(passos or []):
        if not isinstance(passo, dict):
            continue
        item = dict(passo)
        if i == 0 and note:
            item["neste_tema"] = note
        out.append(item)
    return out


def ensure_cache_table(conn) -> None:
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_roteiro_conteudo_cache (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                cache_key           VARCHAR(64) NOT NULL,
                fonte               VARCHAR(16) NOT NULL,
                habilidade_codigo   VARCHAR(32),
                tema                TEXT NOT NULL,
                disciplina_nome     VARCHAR(160),
                nivel_turma         VARCHAR(64) NOT NULL,
                conteudo_json       JSONB NOT NULL,
                texto_montado       TEXT NOT NULL,
                created_by          INTEGER,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_inove_roteiro_conteudo_cache_key UNIQUE (cache_key)
            );
            """
        )
    conn.commit()
    _ensured = True


def buscar_cache(key: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        ensure_cache_table(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT cache_key, fonte, habilidade_codigo, tema, disciplina_nome,
                       nivel_turma, conteudo_json, texto_montado, created_at
                  FROM public.inove_roteiro_conteudo_cache
                 WHERE cache_key = %s
                """,
                (key,),
            )
            row = cur.fetchone()
    if not row:
        return None
    data = dict(row)
    raw = data.get("conteudo_json")
    if isinstance(raw, str):
        try:
            data["conteudo_json"] = json.loads(raw)
        except json.JSONDecodeError:
            data["conteudo_json"] = {}
    return data


def gravar_cache(
    *,
    key: str,
    fonte: str,
    habilidade_codigo: str | None,
    tema: str,
    disciplina_nome: str,
    nivel_turma: str,
    conteudo: dict[str, Any],
    texto: str,
    created_by: int | None,
) -> None:
    with get_conn() as conn:
        ensure_cache_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.inove_roteiro_conteudo_cache (
                    id, cache_key, fonte, habilidade_codigo, tema, disciplina_nome,
                    nivel_turma, conteudo_json, texto_montado, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (cache_key) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    key,
                    fonte,
                    (habilidade_codigo or None),
                    tema,
                    disciplina_nome or None,
                    nivel_turma,
                    json.dumps(conteudo, ensure_ascii=False),
                    texto,
                    created_by,
                ),
            )
        conn.commit()


def _parse_json_resposta(texto: str) -> dict[str, Any]:
    raw = (texto or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Resposta da IA sem JSON.")
    data = json.loads(raw[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON da IA não é objeto.")
    return data


def _get_bedrock():
    verify = os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=Config(connect_timeout=8, read_timeout=60, retries={"max_attempts": 1}),
    )


def gerar_conteudo_ia(
    *,
    tema: str,
    nivel_turma: str,
    disciplina: str = "",
    habilidade_codigo: str = "",
    texto_oficial: str = "",
    fonte: str = "bncc",
) -> dict[str, Any]:
    model_id = BEDROCK_MODEL_ID
    bedrock = _get_bedrock()
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": ROTEIRO_MAX_TOKENS,
            "temperature": 0.3,
            "system": build_system_prompt(),
            "messages": [
                {
                    "role": "user",
                    "content": build_user_prompt(
                        tema=tema,
                        nivel_turma=nivel_turma,
                        disciplina=disciplina,
                        habilidade_codigo=habilidade_codigo,
                        texto_oficial=texto_oficial,
                        fonte=fonte,
                    ),
                }
            ],
        }
    )
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    body_json = json.loads(response.get("body").read())
    parts = body_json.get("content") or []
    texto = ""
    if parts and isinstance(parts[0], dict):
        texto = str(parts[0].get("text") or "").strip()
    usage = body_json.get("usage") or {}
    print(
        f"[roteiro] bedrock_ok model={model_id} stop={body_json.get('stop_reason')} "
        f"in_tokens={usage.get('input_tokens')} out_tokens={usage.get('output_tokens')}",
        file=sys.stderr,
        flush=True,
    )
    if not texto:
        raise ValueError("Resposta vazia do modelo de conteúdo.")
    return _parse_json_resposta(texto)
