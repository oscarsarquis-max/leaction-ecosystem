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
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
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


def kanban_task_from_pei_row(row: dict) -> dict:
    """Espelha uma linha de inove_kanban_cards no formato do kanban_state.tarefas."""
    meta = _json_field(row.get("meta_json")) or {}
    if not isinstance(meta, dict):
        meta = {}
    parent = row.get("parent_card_key")
    if not parent and row.get("parent_card_id") is not None:
        parent = str(row.get("parent_card_id"))
    aula_id = row.get("id_evento")
    try:
        aula_id = int(aula_id) if aula_id is not None else None
    except (TypeError, ValueError):
        aula_id = None
    return {
        "id": row.get("card_key") or str(row.get("id") or ""),
        "titulo": row.get("titulo") or "",
        "descricao": row.get("descricao") or "",
        "como_executar_detalhado": row.get("descricao") or "",
        "coluna": row.get("coluna") or "para_fazer",
        "parent_card_id": str(parent) if parent else None,
        "perfil_inclusao": row.get("perfil_inclusao"),
        "aluno_nome": meta.get("aluno_nome"),
        "escola_override": meta.get("escola_override"),
        "pei_override_versao_aplicada": meta.get("pei_override_versao_aplicada"),
        "pei_concluido": bool(meta.get("pei_concluido")),
        "pei_apendice": meta.get("pei_apendice"),
        "passos_adaptados": meta.get("passos_adaptados"),
        "fonte_pei": meta.get("fonte") or meta.get("origem"),
        "cor": "#FDE68A",
        "historico": [],
        "aula_id": aula_id,
        "aula_ids": [aula_id] if aula_id is not None else [],
        "db_id": int(row["id"]) if row.get("id") is not None else None,
    }


def merge_pei_tasks(tarefas: list[dict], pei_tasks: list[dict]) -> list[dict]:
    """Rehidrata subcards PEI no board sem duplicar card_key já presente."""
    out: list[dict] = []
    by_id: dict[str, dict] = {}
    for t in tarefas or []:
        if not isinstance(t, dict):
            continue
        item = dict(t)
        tid = str(item.get("id") or "").strip()
        if tid:
            by_id[tid] = item
        out.append(item)
    for p in pei_tasks or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        if pid in by_id:
            cur = by_id[pid]
            if not cur.get("parent_card_id") and p.get("parent_card_id"):
                cur["parent_card_id"] = p["parent_card_id"]
            if not cur.get("perfil_inclusao") and p.get("perfil_inclusao"):
                cur["perfil_inclusao"] = p["perfil_inclusao"]
            if not cur.get("aluno_nome") and p.get("aluno_nome"):
                cur["aluno_nome"] = p["aluno_nome"]
            if not cur.get("escola_override") and p.get("escola_override"):
                cur["escola_override"] = p["escola_override"]
            if not cur.get("pei_apendice") and p.get("pei_apendice"):
                cur["pei_apendice"] = p["pei_apendice"]
            continue
        item = dict(p)
        by_id[pid] = item
        out.append(item)
    return out


def fetch_pei_subcard_tasks(
    cur,
    *,
    desafio_id: Any = None,
    id_eventos: list[int] | None = None,
) -> list[dict]:
    """Lê subcards PEI persistidos. Fail-soft se a tabela 020 ainda não existir."""
    ids = []
    for x in id_eventos or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    did = str(desafio_id).strip() if desafio_id else ""
    if did in ("", "None"):
        did = ""
    if not did and not ids:
        return []

    clauses: list[str] = []
    params: list[Any] = []
    if did:
        clauses.append("desafio_id = %s::uuid")
        params.append(did)
    if ids:
        clauses.append("id_evento = ANY(%s)")
        params.append(ids)

    sql = f"""
        SELECT id, card_key, parent_card_id, parent_card_key, titulo, descricao,
               coluna, perfil_inclusao, meta_json, id_evento, desafio_id
          FROM public.inove_kanban_cards
         WHERE ({" OR ".join(clauses)})
           AND (
                parent_card_key IS NOT NULL
                OR parent_card_id IS NOT NULL
                OR perfil_inclusao IS NOT NULL
           )
    """
    try:
        cur.execute("SAVEPOINT pei_subcards_fetch")
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.execute("RELEASE SAVEPOINT pei_subcards_fetch")
    except Exception as exc:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT pei_subcards_fetch")
        except Exception:
            pass
        print(f"[pei] fetch subcards: {exc}", file=sys.stderr)
        return []
    return [kanban_task_from_pei_row(dict(r)) for r in rows]


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


def apendice_pei_individual(pei_ctx: dict | None) -> str:
    """Texto direto do PEI já cadastrado — retrieval, sem gerar."""
    indiv = (pei_ctx or {}).get("individual") or {}
    part = str(indiv.get("particularidades") or "").strip()
    if not part:
        return ""
    nome = str(indiv.get("aluno_nome") or "").strip() or "o aluno"
    return f"PEI individual de {nome}:\n{part}"


def montar_texto_subcard_pei(*, passos: str, apendice: str = "") -> str:
    """Justapõe canônico + particularidades. Não funde os textos."""
    base = str(passos or "").strip()
    extra = str(apendice or "").strip()
    if not extra:
        return base
    if not base:
        return extra
    return f"{base}\n\n— PEI individual —\n{extra}"


def metodologia_id_do_desafio(desafio_id: str | None) -> str:
    """Lê id_metodologia persistido no plano (fallback se o front não enviar)."""
    did = str(desafio_id or "").strip()
    if not did:
        return ""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT plan_data FROM public.inove_desafios WHERE id = %s::uuid",
                    (did,),
                )
                row = cur.fetchone()
        plan = _json_field(row[0] if row else None) or {}
        if not isinstance(plan, dict):
            return ""
        for blob in (plan, plan.get("plano"), plan.get("plano_eduscrum")):
            if not isinstance(blob, dict):
                continue
            mid = str(blob.get("id_metodologia") or blob.get("metodologia_id") or "").strip()
            if mid:
                return mid
    except Exception as exc:
        print(f"[pei] metodologia_id do desafio: {exc}", file=sys.stderr)
    return ""


@kanban_pei_bp.post("/api/kanban/adaptar-pei")
def adaptar_pei():
    """
    Subcard PEI: retrieval do card canônico 79/81; IA só se não houver canônico.

    Payload:
      card_id, titulo_card, descricao_card, perfil_selecionado
      metodologia_id? (id do catálogo 39), aluno_nome?
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
    aluno_nome = _clip(data.get("aluno_nome"), 200)

    if not card_id:
        return jsonify({"success": False, "error": "card_id é obrigatório"}), 400
    if not titulo_card:
        return jsonify({"success": False, "error": "titulo_card é obrigatório"}), 400
    if not perfil:
        return jsonify({"success": False, "error": "perfil_selecionado é obrigatório"}), 400

    # Overrides da escola (fail-soft) — base por condição + individual por nome
    pei_ctx: dict[str, Any] = {}
    try:
        from services.pei_override_service import resolve_context_for_professor

        pei_ctx = resolve_context_for_professor(
            id_clie, condicao=perfil, aluno_nome=aluno_nome or None
        )
    except Exception as exc:
        print(f"[pei] override resolve: {exc}", file=sys.stderr)
        pei_ctx = {}

    id_evento = data.get("id_evento")
    try:
        id_evento_int = int(id_evento) if id_evento is not None and str(id_evento).strip() else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "id_evento inválido"}), 400

    desafio_raw = data.get("desafio_id")
    desafio_id = str(desafio_raw).strip() if desafio_raw else None
    if desafio_id == "":
        desafio_id = None

    coluna_raw = str(data.get("coluna") or "para_fazer").strip()
    coluna = coluna_raw if coluna_raw in ("para_fazer", "fazendo", "pronto") else "para_fazer"

    metodologia_id = _clip(
        data.get("metodologia_id") or data.get("id_metodologia"), 120
    )
    if not metodologia_id:
        metodologia_id = metodologia_id_do_desafio(desafio_id)

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                did = desafio_id
                if not did and id_evento_int is not None:
                    cur.execute(
                        """
                        SELECT desafio_id::text AS desafio_id
                          FROM public.inove_agenda_eventos
                         WHERE id_evento = %s
                        """,
                        (id_evento_int,),
                    )
                    ev_row = cur.fetchone()
                    if ev_row and ev_row.get("desafio_id"):
                        did = str(ev_row["desafio_id"])
                if did:
                    from desafios_routes import (
                        _encerramento_por_desafio_id,
                        _resposta_desafio_encerrado,
                    )

                    enc = _encerramento_por_desafio_id(cur, did)
                    if enc.get("encerrado"):
                        return _resposta_desafio_encerrado(enc)
    except Exception as exc:
        print(f"[pei] encerramento check: {exc}", file=sys.stderr)

    apendice = apendice_pei_individual(pei_ctx)
    passos_canonico = ""
    fonte = "bedrock_fallback"
    ia_called = False

    if metodologia_id:
        try:
            from services.pei_override_service import (
                get_professor_instituicao_b2b_id,
                normalize_condicao,
            )
            from school_outbound import fetch_aee_card_modificado

            cond = normalize_condicao(perfil) or perfil
            inst = get_professor_instituicao_b2b_id(id_clie) or ""
            fetched = fetch_aee_card_modificado(
                metodologia_codigo=metodologia_id,
                condicao=cond,
                instituicao_id=inst,
            )
            item = (fetched or {}).get("item") if isinstance(fetched, dict) else None
            if isinstance(item, dict):
                passos_canonico = str(item.get("passos_adaptados") or "").strip()
        except Exception as exc:
            print(f"[pei] retrieval canonico: {exc}", file=sys.stderr)
            passos_canonico = ""

    if passos_canonico:
        adaptacao = montar_texto_subcard_pei(passos=passos_canonico, apendice=apendice)
        fonte = "card_modificado_79_81"
        print(
            f"[pei] retrieval ok metodologia={metodologia_id} condicao={perfil} "
            f"apendice={bool(apendice)}",
            file=sys.stderr,
        )
    else:
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
        bloco_escola = str(pei_ctx.get("bloco_prompt") or "").strip()
        if bloco_escola:
            system_prompt = (
                system_prompt
                + "\n\nDIRETRIZES OBRIGATÓRIAS DA ESCOLA (respeite sem contradizer):\n"
                + bloco_escola
            )
        user_content = build_pei_user_content(
            perfil_selecionado=perfil,
            titulo_card=titulo_card,
            descricao_card=descricao_card or titulo_card,
        )
        if aluno_nome:
            user_content += f"\nAluno (identificação do professor): {aluno_nome}\n"
        try:
            bruto = _invoke_pei_bedrock(
                system_prompt=system_prompt,
                user_content=user_content,
            )
        except Exception as exc:
            print(f"[pei] bedrock: {exc}", file=sys.stderr)
            return (
                jsonify({"success": False, "error": "Falha ao gerar adaptação com IA"}),
                502,
            )
        adaptacao = montar_texto_subcard_pei(passos=bruto, apendice=apendice)
        fonte = "bedrock_fallback"
        ia_called = True

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
                    "fonte": fonte,
                    "ia_called": ia_called,
                    "metodologia_id": metodologia_id or None,
                    "perfil_selecionado": perfil,
                    "aluno_nome": aluno_nome or None,
                    "passos_adaptados": passos_canonico or None,
                    "pei_apendice": apendice or None,
                    "atividade_original": {
                        "card_id": card_id,
                        "titulo": titulo_card,
                        "descricao": descricao_card,
                    },
                    "gerado_em": datetime.utcnow().isoformat() + "Z",
                    "pei_override_versao_aplicada": pei_ctx.get(
                        "pei_override_versao_aplicada"
                    ),
                    "escola_override": {
                        "ativa": bool(pei_ctx.get("bloco_prompt")),
                        "mensagem": pei_ctx.get("mensagem_ui"),
                        "base": pei_ctx.get("base"),
                        "individual": pei_ctx.get("individual"),
                    }
                    if pei_ctx.get("bloco_prompt")
                    else None,
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
                         %s, %s, %s, %s, %s::jsonb)
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
                        coluna,
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
                        "coluna": coluna,
                        "parent_card_id": card_id,
                        "perfil_inclusao": perfil,
                        "aluno_nome": aluno_nome or None,
                        "escola_override": meta.get("escola_override"),
                        "pei_apendice": apendice or None,
                        "fonte_pei": fonte,
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

    novo_saldo = get_creditos_ia(id_clie)
    if ia_called:
        debitado = consumir_credito_ia(id_clie)
        if debitado is not None:
            novo_saldo = debitado
        else:
            print(
                f"[pei] aviso: fallback IA ok mas não debitou id_clie={id_clie}",
                file=sys.stderr,
            )

    escola_ov = None
    if pei_ctx.get("bloco_prompt"):
        escola_ov = {
            "ativa": True,
            "mensagem": pei_ctx.get("mensagem_ui"),
            "base": pei_ctx.get("base"),
            "individual": pei_ctx.get("individual"),
            "pei_override_versao_aplicada": pei_ctx.get(
                "pei_override_versao_aplicada"
            ),
        }

    return jsonify(
        {
            "success": True,
            "ia_called": ia_called,
            "fonte": fonte,
            "subcard": _serialize_card(row),
            "kanban_task": {
                "id": card_key,
                "titulo": titulo_sub,
                "descricao": adaptacao,
                "coluna": coluna,
                "parent_card_id": card_id,
                "perfil_inclusao": perfil,
                "cor": "#FDE68A",
                "aluno_nome": aluno_nome or None,
                "escola_override": escola_ov,
                "pei_apendice": apendice or None,
                "fonte_pei": fonte,
                "pei_override_versao_aplicada": pei_ctx.get(
                    "pei_override_versao_aplicada"
                ),
            },
            "kanban_state": kanban_state,
            "creditos_ia": novo_saldo,
            "escola_override": escola_ov,
            "pei_override_versao_aplicada": pei_ctx.get(
                "pei_override_versao_aplicada"
            ),
        }
    )


@kanban_pei_bp.get("/api/pei-overrides")
def list_pei_overrides():
    """Overrides PEI ativos da instituição do professor (transparência / debug)."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        from services.pei_override_service import list_overrides_for_professor

        data = list_overrides_for_professor(int(user["id_clie"]))
        return jsonify(
            {
                "success": True,
                "base": data.get("base") or [],
                "individual": data.get("individual") or [],
            }
        )
    except Exception as exc:
        print(f"[pei] list overrides: {exc}", file=sys.stderr)
        return jsonify({"success": True, "base": [], "individual": []})
