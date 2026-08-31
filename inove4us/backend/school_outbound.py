"""Outbound S2S inove4us B2C → inove4us-school (JWT HS256).

Assina com iss='inove4us' e POST no webhook do School.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

import jwt
import requests
from psycopg2.extras import RealDictCursor

from contribuicao_metodologica import resumo_aula_contribuicao
from db import get_conn

ISSUER_B2C = "inove4us"


def _shared_secret() -> str:
    return (os.environ.get("SCHOOL_B2C_SHARED_SECRET") or "").strip()


def school_webhook_url() -> str:
    return (
        os.getenv("INOVE4US_SCHOOL_WEBHOOK_URL")
        or os.getenv("SCHOOL_WEBHOOK_URL")
        or (
            (os.getenv("INOVE4US_SCHOOL_API_URL") or "http://127.0.0.1:5012").rstrip("/")
            + "/api/webhooks/b2c"
        )
    ).strip()


def sign_bridge_jwt(
    *,
    event_type: str,
    payload: dict[str, Any],
    expires_sec: int = 3600,
) -> str:
    secret = _shared_secret()
    if not secret:
        raise RuntimeError("SCHOOL_B2C_SHARED_SECRET não configurado")
    now = int(time.time())
    return jwt.encode(
        {
            "iss": ISSUER_B2C,
            "event_type": event_type,
            "payload": payload or {},
            "iat": now,
            "exp": now + max(60, int(expires_sec)),
        },
        secret,
        algorithm="HS256",
    )


def dispatch_event_to_school(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = str(event_type or "").strip()
    body_payload = payload if isinstance(payload, dict) else {}
    if not event:
        return {"ok": False, "error": "event_type vazio"}
    try:
        token = sign_bridge_jwt(event_type=event, payload=body_payload)
    except RuntimeError as exc:
        print(f"[b2c->school] config: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc)}

    url = school_webhook_url()
    body = {
        "event_type": event,
        "app_id": ISSUER_B2C,
        "payload": body_payload,
        "token": token,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "X-School-B2C-Signature": token,
        "Content-Type": "application/json",
        "X-School-Event-Type": event,
    }
    try:
        res = requests.post(url, json=body, headers=headers, timeout=5.0)
        ok = 200 <= res.status_code < 300
        # ASCII only: console Windows (cp1252) quebra com setas Unicode no print.
        print(f"[b2c->school] {event} -> {url} http={res.status_code}", flush=True)
        return {
            "ok": ok,
            "status_code": res.status_code,
            "event_type": event,
            "response": (res.text or "")[:300],
        }
    except requests.RequestException as exc:
        print(f"[b2c->school] falha de rede {event}: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc), "event_type": event}


def _cliente_bridge_context(id_clie: int) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, nome_clie, mail_clie, instituicao_b2b_id, institutional_name
                FROM public.ctdi_clie
                WHERE id_clie = %s
                LIMIT 1
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
    return dict(row) if row else {}


def _metodologia_nome_from_evento(evento: dict[str, Any]) -> str:
    meta = evento.get("meta_json") if isinstance(evento.get("meta_json"), dict) else {}
    plan = evento.get("plan_data") if isinstance(evento.get("plan_data"), dict) else {}
    for src in (meta, plan, evento):
        for key in (
            "metodologia_nome",
            "metodologia",
            "metodologia_usada",
            "nome_metodologia",
        ):
            val = str(src.get(key) or "").strip()
            if val:
                return val
    tipo = str(evento.get("tipo") or "").strip()
    if "eduscrum" in tipo.lower():
        return "Método inove4us"
    if "pbl" in tipo.lower():
        return "Aprendizagem baseada em problemas (PBL)"
    return tipo or "Metodologia"


def _aula_contexto_from_evento(
    evento: dict[str, Any],
    *,
    metodologia: str,
    aula_contexto: str | None = None,
) -> str:
    explicit = (aula_contexto or "").strip()
    if explicit:
        return explicit
    meta = evento.get("meta_json") if isinstance(evento.get("meta_json"), dict) else {}
    disc = str(
        meta.get("disciplina_nome")
        or evento.get("disciplina_nome")
        or ""
    ).strip()
    titulo = str(evento.get("titulo") or "").strip()
    parts = [p for p in (metodologia, disc, titulo) if p]
    return " · ".join(parts) or metodologia or "Aula"


def _tarefas_from_kanban(kanban_state: Any) -> list[dict[str, Any]]:
    if isinstance(kanban_state, list):
        return [t for t in kanban_state if isinstance(t, dict)]
    if isinstance(kanban_state, dict):
        tarefas = kanban_state.get("tarefas")
        if isinstance(tarefas, list):
            return [t for t in tarefas if isinstance(t, dict)]
    return []


def _cards_snapshot_from_evento(evento: dict[str, Any]) -> list[dict[str, Any]]:
    """Snapshot enxuto dos cards (com historico) para o espelho School."""
    ks = evento.get("kanban_state")
    if isinstance(ks, str) and ks.strip():
        try:
            import json

            ks = json.loads(ks)
        except Exception:
            ks = None
    cards_out: list[dict[str, Any]] = []
    for t in _tarefas_from_kanban(ks):
        cards_out.append(
            {
                "id": t.get("id"),
                "titulo": t.get("titulo") or t.get("titulo_do_card"),
                "coluna": t.get("coluna") or "para_fazer",
                "cor": t.get("cor"),
                "duracao_minutos": t.get("duracao_minutos"),
                "objetivo": t.get("objetivo"),
                "como_executar_detalhado": t.get("como_executar_detalhado")
                or t.get("mecanica_passo_a_passo")
                or t.get("descricao"),
                "dica_de_facilitacao": t.get("dica_de_facilitacao"),
                "ultima_observacao": t.get("ultima_observacao"),
                "historico": t.get("historico") if isinstance(t.get("historico"), list) else [],
                "perfil_inclusao": t.get("perfil_inclusao"),
                "parent_card_id": t.get("parent_card_id"),
                "pei_concluido": t.get("pei_concluido"),
                "aula_id": t.get("aula_id"),
                "origem_card": t.get("origem_card"),
                "editado": bool(t.get("editado")),
            }
        )
    return cards_out


def _iso_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) >= 10 and text[4] == "-":
        return text[:10]
    return None


def _as_int_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ocorrencia_link_rows(evento: dict[str, Any]) -> dict[str, Any]:
    """Completa datas/títulos das aulas linkadas (junção / continuação)."""
    ev_id = _as_int_id(evento.get("id_evento"))
    wanted = {
        _as_int_id(evento.get("juncao_destino_id")),
        _as_int_id(evento.get("continuacao_origem_id")),
        _as_int_id(evento.get("juncao_origem_id")),
        _as_int_id(evento.get("continuacao_destino_id")),
        ev_id,
    }
    wanted.discard(None)
    by_id: dict[int, dict[str, Any]] = {}
    reverse_juncao = None
    reverse_cont = None
    if not wanted and ev_id is None:
        return {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if wanted:
                    cur.execute(
                        """
                        SELECT id_evento, data_evento, titulo
                        FROM public.inove_agenda_eventos
                        WHERE id_evento = ANY(%s)
                        """,
                        (list(wanted),),
                    )
                    for row in cur.fetchall():
                        by_id[int(row["id_evento"])] = dict(row)
                if ev_id is not None:
                    cur.execute(
                        """
                        SELECT id_evento, data_evento, titulo
                        FROM public.inove_agenda_eventos
                        WHERE juncao_destino_id = %s
                        ORDER BY data_evento DESC, id_evento DESC
                        LIMIT 1
                        """,
                        (ev_id,),
                    )
                    reverse_juncao = cur.fetchone()
                    cur.execute(
                        """
                        SELECT id_evento, data_evento, titulo
                        FROM public.inove_agenda_eventos
                        WHERE continuacao_origem_id = %s
                        ORDER BY data_evento DESC, id_evento DESC
                        LIMIT 1
                        """,
                        (ev_id,),
                    )
                    reverse_cont = cur.fetchone()
    except Exception as exc:
        print(f"[b2c->school] ocorrencia links: {exc}", file=sys.stderr, flush=True)
        return {}

    def pack(row: dict[str, Any] | None) -> tuple[int | None, str | None, str | None]:
        if not row:
            return None, None, None
        return (
            _as_int_id(row.get("id_evento")),
            _iso_date(row.get("data_evento")),
            str(row.get("titulo") or "").strip() or None,
        )

    dest_id = _as_int_id(evento.get("juncao_destino_id"))
    dest_data = _iso_date(evento.get("juncao_destino_data"))
    dest_titulo = str(evento.get("juncao_destino_titulo") or "").strip() or None
    if dest_id and dest_id in by_id:
        _, dest_data, dest_titulo = pack(by_id[dest_id])

    orig_j_id = _as_int_id(evento.get("juncao_origem_id"))
    orig_j_data = _iso_date(evento.get("juncao_origem_data"))
    orig_j_titulo = str(evento.get("juncao_origem_titulo") or "").strip() or None
    if orig_j_id and orig_j_id in by_id:
        _, orig_j_data, orig_j_titulo = pack(by_id[orig_j_id])
    elif reverse_juncao:
        orig_j_id, orig_j_data, orig_j_titulo = pack(dict(reverse_juncao))

    cont_orig_id = _as_int_id(evento.get("continuacao_origem_id"))
    cont_orig_data = _iso_date(evento.get("continuacao_origem_data"))
    cont_orig_titulo = str(evento.get("continuacao_origem_titulo") or "").strip() or None
    if cont_orig_id and cont_orig_id in by_id:
        _, cont_orig_data, cont_orig_titulo = pack(by_id[cont_orig_id])

    cont_dest_id = _as_int_id(evento.get("continuacao_destino_id"))
    cont_dest_data = _iso_date(evento.get("continuacao_destino_data"))
    cont_dest_titulo = str(evento.get("continuacao_destino_titulo") or "").strip() or None
    if cont_dest_id and cont_dest_id in by_id:
        _, cont_dest_data, cont_dest_titulo = pack(by_id[cont_dest_id])
    elif reverse_cont:
        cont_dest_id, cont_dest_data, cont_dest_titulo = pack(dict(reverse_cont))

    return {
        "juncao_destino_id": dest_id,
        "juncao_destino_data": dest_data,
        "juncao_destino_titulo": dest_titulo,
        "juncao_origem_id": orig_j_id,
        "juncao_origem_data": orig_j_data,
        "juncao_origem_titulo": orig_j_titulo,
        "continuacao_origem_id": cont_orig_id,
        "continuacao_origem_data": cont_orig_data,
        "continuacao_origem_titulo": cont_orig_titulo,
        "continuacao_destino_id": cont_dest_id,
        "continuacao_destino_data": cont_dest_data,
        "continuacao_destino_titulo": cont_dest_titulo,
    }


def _mesa_ocorrencia(evento: dict[str, Any]) -> dict[str, Any]:
    links = _ocorrencia_link_rows(evento)
    resolucao = str(evento.get("ocorrencia_resolucao") or "").strip() or None
    status = (
        str(evento.get("ocorrencia_status") or "").strip()
        or resolucao
        or "normal"
    )
    unida = resolucao == "concluida_via_juncao" or bool(
        links.get("juncao_destino_id") or links.get("juncao_origem_id")
    )
    return {
        "tipo": evento.get("ocorrencia_tipo"),
        "nota": evento.get("ocorrencia_nota") or "",
        "resolucao": resolucao,
        "status": status,
        "aguardando_continuacao": bool(evento.get("aguardando_continuacao"))
        or resolucao == "aguardando_continuacao",
        "unida": unida,
        **links,
    }


def dispatch_lesson_record_sync(
    *,
    id_clie: int,
    evento: dict[str, Any],
    has_teacher_adaptations: bool,
    teacher_adaptation_text: str | None = None,
    metodologia_usada: str | None = None,
    aula_contexto: str | None = None,
    professor_nome: str | None = None,
    has_pei_adaptations: bool = False,
    pei_adaptation_text: str | None = None,
    pei_aluno_id: str | None = None,
    aluno_nome: str | None = None,
    school_status: str | None = None,
) -> dict[str, Any]:
    """Empurra LESSON_RECORD_SYNC ao School (curadoria bottom-up se houver adaptação)."""
    cliente = _cliente_bridge_context(id_clie)
    instituicao_id = cliente.get("instituicao_b2b_id")
    if not instituicao_id:
        return {"ok": False, "skipped": True, "reason": "sem_instituicao_b2b"}

    met_nome = (metodologia_usada or "").strip() or _metodologia_nome_from_evento(evento)
    adapt_text = (teacher_adaptation_text or "").strip() or None
    # Curadoria só com texto concreto no fechamento (flag sozinha não basta).
    has_adapt = bool(adapt_text)
    pei_text = (pei_adaptation_text or "").strip() or None
    has_pei = bool(has_pei_adaptations) and bool(pei_text)

    prof_nome = (
        (professor_nome or "").strip()
        or str(cliente.get("nome_clie") or "").strip()
        or None
    )
    contexto = _aula_contexto_from_evento(
        evento, metodologia=met_nome, aula_contexto=aula_contexto
    )

    origem = None
    raw_origem = evento.get("desafio_id") or evento.get("id_evento")
    if raw_origem is not None:
        origem = str(raw_origem)

    ev_status = str(evento.get("status") or "").strip().lower()
    mesa_status = ev_status or "concluido"
    # Status no School: aprovado só no fechamento; em andamento → pendente.
    if school_status:
        payload_status = school_status
    elif has_adapt or mesa_status in ("concluido", "concluído", "done"):
        payload_status = "aprovado"
    else:
        payload_status = "pendente"

    cards = _cards_snapshot_from_evento(evento)
    contribuicao = resumo_aula_contribuicao(cards)

    # Cadeia School: desafio exige desafio_grupo_id; aula avulsa/Dia a Dia não.
    raw_desafio = evento.get("desafio_id") or evento.get("desafio_grupo_id")
    desafio_grupo_id = None
    if raw_desafio not in (None, ""):
        desafio_grupo_id = str(raw_desafio).strip() or None
    tipo_aula = "desafio" if desafio_grupo_id else "dia_a_dia"

    mesa = {
        "id": str(evento.get("id_evento") or ""),
        "titulo": evento.get("titulo") or "",
        "tipo_aula": tipo_aula,
        "status": mesa_status,
        "metodologia_nome": met_nome,
        "semana_referencia": str(evento.get("data_evento") or "")[:10] or None,
        "has_teacher_adaptations": has_adapt,
        "teacher_adaptation_text": adapt_text,
        "texto_sugestao": adapt_text,
        "aula_contexto": contexto,
        "adaptations": {"texto": adapt_text} if adapt_text else None,
        "has_pei_adaptations": has_pei,
        "pei_adaptation_text": pei_text,
        "pei_aluno_id": pei_aluno_id,
        "aluno_nome": aluno_nome,
        "aluno_id": evento.get("aluno_id"),
        "pei_override_versao_aplicada": evento.get("pei_override_versao_aplicada"),
        "relato_sala": evento.get("relato_sala"),
        "participantes": evento.get("participantes"),
        "ocorrencia": _mesa_ocorrencia(evento),
        "professor_id": str(id_clie),
        "professor_nome": prof_nome,
        "desafio_grupo_id": desafio_grupo_id,
        "cards": cards,
        "kanban_cards": cards,
        "contribuicao": contribuicao,
    }

    payload = {
        "instituicao_id": str(instituicao_id),
        "origem_plano_b2c_id": origem,
        "professor_email": cliente.get("mail_clie"),
        "email": cliente.get("mail_clie"),
        "professor_b2c_id": str(id_clie),
        "professor_id": str(id_clie),
        "professor_nome": prof_nome,
        "aula_contexto": contexto,
        "texto_sugestao": adapt_text,
        "metodologia_nome": met_nome,
        "metodologia_usada": met_nome,
        "semana_referencia": mesa["semana_referencia"],
        "tipo_aula": tipo_aula,
        "desafio_grupo_id": desafio_grupo_id,
        "status": payload_status,
        "conteudo_resumo": evento.get("titulo") or met_nome,
        "has_teacher_adaptations": has_adapt,
        "teacher_adaptation_text": adapt_text,
        "adaptations": {"texto": adapt_text} if adapt_text else None,
        "has_pei_adaptations": has_pei,
        "pei_adaptation_text": pei_text,
        "pei_aluno_id": pei_aluno_id,
        "aluno_nome": aluno_nome,
        "mesa": mesa,
        "contribuicao": contribuicao,
    }
    return dispatch_event_to_school("LESSON_RECORD_SYNC", payload)
