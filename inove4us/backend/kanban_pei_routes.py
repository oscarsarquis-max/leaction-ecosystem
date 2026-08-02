"""
Adaptação Inclusiva (PEI) — Subcards do Kanban.

POST /api/kanban/adaptar-pei
  Gera adaptação via Bedrock (mesmo contrato do SYSTEM PROMPT de psicopedagogia)
  e persiste subcard em inove_kanban_cards (+ espelho em kanban_state JSONB quando houver id_evento).
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime
from typing import Any

import boto3
from botocore.config import Config
from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from db import consumir_credito_ia, get_conn, get_creditos_ia
from prompts.pei_adaptacao import build_pei_system_prompt, build_pei_user_content

kanban_pei_bp = Blueprint("kanban_pei", __name__)

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
PEI_BEDROCK_MODEL_ID = (os.environ.get("PEI_BEDROCK_MODEL_ID") or "").strip()
PEI_MAX_TOKENS = int(os.environ.get("PEI_BEDROCK_MAX_TOKENS") or "512")

_ensured = False


def _require_user() -> dict | None:
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    return user


def _clip(value: Any, limit: int) -> str:
    return str(value or "")[:limit].strip()


def _norm_perfil(raw: str) -> str | None:
    text = _clip(raw, 64)
    if not text:
        return None
    # Aceita rótulos livres curtos; normaliza espaços.
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned


def _bedrock_ssl_verify_enabled() -> bool:
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _get_bedrock_runtime_client():
    verify = _bedrock_ssl_verify_enabled()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=Config(connect_timeout=8, read_timeout=45, retries={"max_attempts": 1}),
    )


def _invoke_pei_bedrock(*, system_prompt: str, user_content: str) -> str:
    """Chama Bedrock e devolve texto plano (2–3 frases de adaptação)."""
    model_id = PEI_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    bedrock = _get_bedrock_runtime_client()
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": PEI_MAX_TOKENS,
            "temperature": 0.3,
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
    body_json = json.loads(response.get("body").read())
    parts = body_json.get("content") or []
    texto = ""
    if parts and isinstance(parts[0], dict):
        texto = str(parts[0].get("text") or "").strip()
    stop_reason = body_json.get("stop_reason")
    usage = body_json.get("usage") or {}
    print(
        f"[pei] model={model_id} stop={stop_reason} "
        f"out_tokens={usage.get('output_tokens')} in_tokens={usage.get('input_tokens')}",
        file=sys.stderr,
    )
    if not texto:
        raise ValueError("Resposta vazia do modelo de adaptação PEI.")
    # Limpa cercas markdown acidentais
    texto = re.sub(r"^```(?:\w+)?\s*", "", texto)
    texto = re.sub(r"\s*```$", "", texto).strip()
    return texto


def _ensure_kanban_cards_table(conn) -> None:
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_kanban_cards (
                id                 BIGSERIAL PRIMARY KEY,
                id_clie            INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                id_evento          INTEGER
                    REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE CASCADE,
                desafio_id         UUID,
                card_key           VARCHAR(120) NOT NULL,
                parent_card_id     BIGINT
                    REFERENCES public.inove_kanban_cards (id) ON DELETE CASCADE,
                parent_card_key    VARCHAR(120),
                titulo             TEXT NOT NULL DEFAULT '',
                descricao          TEXT NOT NULL DEFAULT '',
                coluna             VARCHAR(32) NOT NULL DEFAULT 'para_fazer',
                perfil_inclusao    VARCHAR(64),
                meta_json          JSONB,
                created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_kanban_cards_evento_key
                ON public.inove_kanban_cards (id_evento, card_key)
                WHERE id_evento IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_clie
                ON public.inove_kanban_cards (id_clie, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_parent
                ON public.inove_kanban_cards (parent_card_id)
                WHERE parent_card_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_parent_key
                ON public.inove_kanban_cards (id_evento, parent_card_key)
                WHERE parent_card_key IS NOT NULL;
            """
        )
    _ensured = True


def _json_field(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, memoryview)):
        value = bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _tarefas_from_kanban(kanban_state: Any) -> list[dict]:
    data = _json_field(kanban_state)
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        tarefas = data.get("tarefas")
        if isinstance(tarefas, list):
            return [t for t in tarefas if isinstance(t, dict)]
    return []


def _serialize_card(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "card_key": row.get("card_key") or "",
        "id_clie": int(row["id_clie"]),
        "id_evento": int(row["id_evento"]) if row.get("id_evento") is not None else None,
        "desafio_id": str(row["desafio_id"]) if row.get("desafio_id") else None,
        "parent_card_id": int(row["parent_card_id"])
        if row.get("parent_card_id") is not None
        else None,
        "parent_card_key": row.get("parent_card_key"),
        "titulo": row.get("titulo") or "",
        "descricao": row.get("descricao") or "",
        "coluna": row.get("coluna") or "para_fazer",
        "perfil_inclusao": row.get("perfil_inclusao"),
        "meta_json": _json_field(row.get("meta_json")),
        "created_at": row["created_at"].isoformat()
        if hasattr(row.get("created_at"), "isoformat")
        else row.get("created_at"),
        "updated_at": row["updated_at"].isoformat()
        if hasattr(row.get("updated_at"), "isoformat")
        else row.get("updated_at"),
    }


def _append_subcard_to_kanban(
    cur,
    *,
    id_evento: int,
    id_clie: int,
    subcard_json: dict,
) -> dict | None:
    """Espelha o subcard em kanban_state.tarefas do evento (board ao vivo)."""
    cur.execute(
        """
        SELECT id_evento, id_clie, id_clie_responsavel, kanban_state
          FROM public.inove_agenda_eventos
         WHERE id_evento = %s
        """,
        (int(id_evento),),
    )
    ev = cur.fetchone()
    if not ev:
        return None
    owner = int(ev.get("id_clie_responsavel") or ev.get("id_clie") or 0)
    if owner != int(id_clie):
        return None

    tarefas = _tarefas_from_kanban(ev.get("kanban_state"))
    # evita duplicar mesmo card_key
    key = str(subcard_json.get("id") or "")
    tarefas = [t for t in tarefas if str(t.get("id") or "") != key]
    tarefas.append(subcard_json)
    kanban = {"tarefas": tarefas}
    cur.execute(
        """
        UPDATE public.inove_agenda_eventos
           SET kanban_state = %s::jsonb
         WHERE id_evento = %s
     RETURNING kanban_state
        """,
        (json.dumps(kanban, ensure_ascii=False), int(id_evento)),
    )
    updated = cur.fetchone()
    return _json_field(updated.get("kanban_state")) if updated else kanban


@kanban_pei_bp.post("/api/kanban/adaptar-pei")
def adaptar_pei():
    """
    Gera Subcard PEI via IA e persiste em inove_kanban_cards.

    Payload:
      card_id, titulo_card, descricao_card, perfil_selecionado
      id_evento? (espelha no kanban_state), desafio_id?
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"success": False, "error": "JSON inválido no body"}), 400

    id_clie = int(user["id_clie"])
    card_id = _clip(data.get("card_id"), 120)
    titulo_card = _clip(data.get("titulo_card"), 500)
    descricao_card = _clip(data.get("descricao_card"), 8000)
    perfil = _norm_perfil(str(data.get("perfil_selecionado") or ""))

    if not card_id:
        return jsonify({"success": False, "error": "card_id é obrigatório"}), 400
    if not titulo_card:
        return jsonify({"success": False, "error": "titulo_card é obrigatório"}), 400
    if not perfil:
        return jsonify({"success": False, "error": "perfil_selecionado é obrigatório"}), 400

    id_evento = data.get("id_evento")
    try:
        id_evento_int = int(id_evento) if id_evento is not None and str(id_evento).strip() else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "id_evento inválido"}), 400

    desafio_raw = data.get("desafio_id")
    desafio_id = str(desafio_raw).strip() if desafio_raw else None
    if desafio_id == "":
        desafio_id = None

    saldo = get_creditos_ia(id_clie)
    if saldo <= 0:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Sem créditos de IA para gerar adaptação PEI",
                    "creditos_ia": 0,
                }
            ),
            402,
        )

    system_prompt = build_pei_system_prompt(
        perfil_selecionado=perfil,
        titulo_card=titulo_card,
        descricao_card=descricao_card or titulo_card,
    )
    user_content = build_pei_user_content(
        perfil_selecionado=perfil,
        titulo_card=titulo_card,
        descricao_card=descricao_card or titulo_card,
    )

    try:
        adaptacao = _invoke_pei_bedrock(
            system_prompt=system_prompt,
            user_content=user_content,
        )
    except Exception as exc:
        print(f"[pei] bedrock: {exc}", file=sys.stderr)
        return (
            jsonify({"success": False, "error": "Falha ao gerar adaptação com IA"}),
            502,
        )

    titulo_sub = f"Adaptação PEI: {titulo_card}"[:500]
    slug_perfil = re.sub(r"[^a-z0-9]+", "-", perfil.lower()).strip("-")[:40] or "pei"
    card_key = f"{card_id}-pei-{slug_perfil}-{uuid.uuid4().hex[:8]}"

    row = None
    kanban_state = None
    try:
        with get_conn() as conn:
            _ensure_kanban_cards_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                parent_db_id = None
                if id_evento_int is not None:
                    cur.execute(
                        """
                        SELECT id
                          FROM public.inove_kanban_cards
                         WHERE id_evento = %s
                           AND card_key = %s
                           AND id_clie = %s
                         LIMIT 1
                        """,
                        (id_evento_int, card_id, id_clie),
                    )
                    parent = cur.fetchone()
                    if parent:
                        parent_db_id = int(parent["id"])

                meta = {
                    "origem": "adaptar_pei",
                    "perfil_selecionado": perfil,
                    "atividade_original": {
                        "card_id": card_id,
                        "titulo": titulo_card,
                        "descricao": descricao_card,
                    },
                    "gerado_em": datetime.utcnow().isoformat() + "Z",
                }

                cur.execute(
                    """
                    INSERT INTO public.inove_kanban_cards
                        (id_clie, id_evento, desafio_id, card_key,
                         parent_card_id, parent_card_key,
                         titulo, descricao, coluna, perfil_inclusao, meta_json)
                    VALUES
                        (%s, %s, %s, %s,
                         %s, %s,
                         %s, %s, 'para_fazer', %s, %s::jsonb)
                    RETURNING *
                    """,
                    (
                        id_clie,
                        id_evento_int,
                        desafio_id,
                        card_key,
                        parent_db_id,
                        card_id,
                        titulo_sub,
                        adaptacao,
                        perfil,
                        json.dumps(meta, ensure_ascii=False),
                    ),
                )
                row = dict(cur.fetchone())

                if id_evento_int is not None:
                    sub_json = {
                        "id": card_key,
                        "titulo": titulo_sub,
                        "descricao": adaptacao,
                        "coluna": "para_fazer",
                        "parent_card_id": card_id,
                        "perfil_inclusao": perfil,
                        "cor": "#FDE68A",
                        "historico": [],
                        "ultima_observacao": f"Adaptação PEI · {perfil}",
                        "aula_id": id_evento_int,
                        "aula_ids": [id_evento_int],
                        "db_id": int(row["id"]),
                    }
                    kanban_state = _append_subcard_to_kanban(
                        cur,
                        id_evento=id_evento_int,
                        id_clie=id_clie,
                        subcard_json=sub_json,
                    )
    except pg_errors.UndefinedTable:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Tabela inove_kanban_cards ausente — aplique migration 020",
                    "code": "schema_pending",
                }
            ),
            503,
        )
    except Exception as exc:
        print(f"[pei] persist: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao salvar subcard PEI"}), 500

    novo_saldo = consumir_credito_ia(id_clie)
    if novo_saldo is None:
        # Geração ok, mas crédito sumiu em condição de corrida — ainda devolve o subcard.
        novo_saldo = get_creditos_ia(id_clie)

    return jsonify(
        {
            "success": True,
            "subcard": _serialize_card(row),
            "kanban_task": {
                "id": card_key,
                "titulo": titulo_sub,
                "descricao": adaptacao,
                "coluna": "para_fazer",
                "parent_card_id": card_id,
                "perfil_inclusao": perfil,
                "cor": "#FDE68A",
            },
            "kanban_state": kanban_state,
            "creditos_ia": novo_saldo,
        }
    )
