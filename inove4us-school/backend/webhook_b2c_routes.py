"""Webhook S2S inove4us B2C → inove4us-school (ponte interna JWT).

POST /api/webhooks/b2c — sem sessão de gestor / RBAC.
Sempre HTTP 200 após JWT válido (ACK outbox).
"""
from __future__ import annotations

import sys
import uuid
from datetime import date, datetime
from typing import Any

from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from db import get_conn
from school_b2c_jwt import require_b2c_bridge_jwt

bp = Blueprint("b2c_webhooks", __name__)


def _event_payload(decoded: dict, body: dict) -> tuple[str, dict]:
    event_type = str(
        decoded.get("event_type")
        or body.get("event_type")
        or request.headers.get("X-School-Event-Type")
        or ""
    ).strip()
    inner = decoded.get("payload")
    if inner is None:
        inner = decoded.get("payload_json")
    if inner is None:
        inner = body.get("payload")
    if inner is None:
        inner = body.get("payload_json")
    if not isinstance(inner, dict):
        inner = {}
    return event_type, inner


def _log(msg: str) -> None:
    print(f"[b2c-webhook] {msg}", flush=True)


def _as_uuid(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = str(value or "").strip()[:10]
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return date.today()


def _map_status(raw: Any) -> str:
    s = str(raw or "pendente").strip().lower()
    if s in ("aprovado",):
        return "aprovado"
    if s in ("reprovado",):
        return "reprovado"
    if s in ("concluido", "concluído", "done", "finalizado", "executado"):
        return "aprovado"
    # Em andamento / planejado permanece pendente no espelho School
    if s in ("em_andamento", "em_execucao", "executando", "planejado", "pendente"):
        return "pendente"
    return "pendente"


def _map_tipo_aula(raw: Any, mesa: dict) -> str:
    s = str(raw or mesa.get("tipo_aula") or mesa.get("vetor") or "dia_a_dia").strip().lower()
    if s in ("desafio", "challenge"):
        return "desafio"
    return "dia_a_dia"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in ("1", "true", "yes", "sim")


def _resolve_professor(cur: Any, instituicao_id: str, payload: dict) -> str | None:
    vinculo = _as_uuid(payload.get("professor_vinculo_id"))
    if vinculo:
        cur.execute(
            """
            SELECT id FROM public.school_professores_vinculo
            WHERE id = %s AND instituicao_id = %s
            """,
            (vinculo, instituicao_id),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"])

    email = str(
        payload.get("professor_email")
        or payload.get("email_convite")
        or payload.get("email")
        or ""
    ).strip().lower()
    if email:
        cur.execute(
            """
            SELECT id FROM public.school_professores_vinculo
            WHERE instituicao_id = %s
              AND lower(coalesce(email_convite, '')) = %s
            LIMIT 1
            """,
            (instituicao_id, email),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"])

    professor_b2c = None
    raw_b2c = payload.get("professor_b2c_id")
    if raw_b2c is not None and str(raw_b2c).strip() != "":
        try:
            professor_b2c = int(raw_b2c)
        except (TypeError, ValueError):
            professor_b2c = None
    if professor_b2c is not None:
        cur.execute(
            """
            SELECT id FROM public.school_professores_vinculo
            WHERE instituicao_id = %s AND professor_b2c_id = %s
            LIMIT 1
            """,
            (instituicao_id, professor_b2c),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"])

    cur.execute(
        """
        SELECT id FROM public.school_professores_vinculo
        WHERE instituicao_id = %s
        ORDER BY created_at ASC NULLS LAST
        LIMIT 1
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    return str(row["id"]) if row else None


def _resolve_turma(cur: Any, instituicao_id: str, payload: dict) -> str | None:
    turma = _as_uuid(payload.get("turma_id"))
    if turma:
        cur.execute(
            """
            SELECT id FROM public.school_turmas
            WHERE id = %s AND instituicao_id = %s
            """,
            (turma, instituicao_id),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"])

    cur.execute(
        """
        SELECT id FROM public.school_turmas
        WHERE instituicao_id = %s
        ORDER BY created_at ASC NULLS LAST
        LIMIT 1
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    return str(row["id"]) if row else None


def _resolve_metodologia(
    cur: Any, instituicao_id: str, payload: dict, mesa: dict
) -> tuple[str | None, str]:
    nome = str(
        payload.get("metodologia_nome")
        or mesa.get("metodologia_nome")
        or mesa.get("metodologia")
        or ""
    ).strip()
    met_id = _as_uuid(
        payload.get("metodologia_catalogo_id") or mesa.get("metodologia_catalogo_id")
    )
    if met_id:
        cur.execute(
            """
            SELECT id, nome FROM public.school_metodologias_catalogo
            WHERE id = %s AND ativo IS TRUE
            """,
            (met_id,),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"]), str(row["nome"] or nome)

    if nome:
        # Catálogo seed usa origem='padrao' (não 'inove4us').
        cur.execute(
            """
            SELECT id, nome FROM public.school_metodologias_catalogo
            WHERE ativo IS TRUE
              AND lower(nome) = lower(%s)
              AND (
                    COALESCE(origem, '') IN (
                        'inove4us', 'padrao', 'referencia_inove4us', 'escola'
                    )
                 OR instituicao_origem_id = %s::uuid
              )
            ORDER BY CASE WHEN origem = 'escola' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (nome, instituicao_id),
        )
        row = cur.fetchone()
        if row:
            return str(row["id"]), str(row["nome"] or nome)
        # Fallback: match por codigo (ex.: agil_minute_paper)
        codigo = str(
            payload.get("metodologia_codigo")
            or payload.get("metodologia_key")
            or mesa.get("metodologia_codigo")
            or mesa.get("metodologia_key")
            or ""
        ).strip()
        if codigo:
            cur.execute(
                """
                SELECT id, nome FROM public.school_metodologias_catalogo
                WHERE ativo IS TRUE AND lower(codigo) = lower(%s)
                LIMIT 1
                """,
                (codigo,),
            )
            row = cur.fetchone()
            if row:
                return str(row["id"]), str(row["nome"] or nome)

    cur.execute(
        """
        SELECT id, nome FROM public.school_metodologias_catalogo
        WHERE ativo IS TRUE
          AND (
                COALESCE(origem, '') IN (
                    'inove4us', 'padrao', 'referencia_inove4us', 'escola'
                )
             OR instituicao_origem_id = %s::uuid
          )
        ORDER BY nome ASC
        LIMIT 1
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"]), str(row["nome"] or nome or "Metodologia")
    return None, nome or "Metodologia"


def _handle_lesson_record_sync(payload: dict) -> dict:
    instituicao_id = _as_uuid(payload.get("instituicao_id"))
    if not instituicao_id:
        return {"handled": False, "error": "instituicao_id obrigatório"}

    mesa = payload.get("mesa") or payload.get("mesa_json") or payload.get("desk")
    if not isinstance(mesa, dict):
        mesa = payload if isinstance(payload, dict) else {}

    origem = _as_uuid(
        payload.get("origem_plano_b2c_id")
        or payload.get("plano_b2c_id")
        or mesa.get("id")
        or mesa.get("plano_id")
    )
    if not origem:
        # Garante chave de UPSERT estável mesmo sem UUID explícito do B2C.
        origem = str(uuid.uuid5(uuid.NAMESPACE_URL, f"lesson:{instituicao_id}:{str(mesa)[:200]}"))

    semana = _as_date(
        payload.get("semana_referencia")
        or mesa.get("semana_referencia")
        or mesa.get("data")
        or mesa.get("data_aula")
    )
    tipo_aula = _map_tipo_aula(payload.get("tipo_aula"), mesa)
    status = _map_status(payload.get("status") or mesa.get("status"))
    resumo = str(
        payload.get("conteudo_resumo")
        or mesa.get("conteudo_resumo")
        or mesa.get("titulo")
        or mesa.get("title")
        or ""
    ).strip() or None
    has_adapt = _truthy(
        payload.get("has_teacher_adaptations")
        or mesa.get("has_teacher_adaptations")
    )
    # Texto isolado no fechamento também dispara curadoria (sem depender só da flag).
    teacher_text_preview = str(
        payload.get("texto_sugestao")
        or payload.get("teacher_adaptation_text")
        or payload.get("sugestao_coordenacao")
        or mesa.get("texto_sugestao")
        or mesa.get("teacher_adaptation_text")
        or ""
    ).strip()
    if teacher_text_preview:
        has_adapt = True
    desafio_grupo = _as_uuid(payload.get("desafio_grupo_id") or mesa.get("desafio_grupo_id"))
    # chk_school_planos_aula_desafio_cadeia: desafio <=> desafio_grupo_id NOT NULL
    if tipo_aula == "desafio" and not desafio_grupo:
        tipo_aula = "dia_a_dia"
    if tipo_aula == "dia_a_dia":
        desafio_grupo = None
    desafio_titulo = str(
        payload.get("desafio_titulo") or mesa.get("desafio_titulo") or ""
    ).strip() or None
    desafio_seq = payload.get("desafio_sequencia")
    if desafio_seq is not None:
        try:
            desafio_seq = int(desafio_seq)
        except (TypeError, ValueError):
            desafio_seq = None
    if tipo_aula != "desafio":
        desafio_titulo = None
        desafio_seq = None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
                (instituicao_id,),
            )
            if not cur.fetchone():
                return {"handled": False, "error": "instituição não encontrada"}

            professor_id = _resolve_professor(cur, instituicao_id, payload)
            if not professor_id:
                return {
                    "handled": False,
                    "error": "nenhum professor_vinculo para a instituição",
                }

            turma_id = _resolve_turma(cur, instituicao_id, payload)
            if not turma_id:
                return {
                    "handled": False,
                    "error": "nenhuma turma para a instituição",
                }

            met_id, met_nome = _resolve_metodologia(
                cur, instituicao_id, payload, mesa
            )
            if not met_id:
                return {
                    "handled": False,
                    "error": "nenhuma metodologia no catálogo",
                }

            cur.execute(
                """
                INSERT INTO public.school_planos_aula_espelhados (
                    instituicao_id,
                    professor_vinculo_id,
                    turma_id,
                    metodologia_catalogo_id,
                    semana_referencia,
                    conteudo_resumo,
                    status,
                    origem_plano_b2c_id,
                    tipo_aula,
                    mesa_payload_json,
                    desafio_grupo_id,
                    desafio_titulo,
                    desafio_sequencia
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (instituicao_id, origem_plano_b2c_id)
                    WHERE origem_plano_b2c_id IS NOT NULL
                DO UPDATE SET
                    professor_vinculo_id = EXCLUDED.professor_vinculo_id,
                    turma_id = EXCLUDED.turma_id,
                    metodologia_catalogo_id = EXCLUDED.metodologia_catalogo_id,
                    semana_referencia = EXCLUDED.semana_referencia,
                    conteudo_resumo = EXCLUDED.conteudo_resumo,
                    status = EXCLUDED.status,
                    tipo_aula = EXCLUDED.tipo_aula,
                    mesa_payload_json = EXCLUDED.mesa_payload_json,
                    desafio_grupo_id = EXCLUDED.desafio_grupo_id,
                    desafio_titulo = EXCLUDED.desafio_titulo,
                    desafio_sequencia = EXCLUDED.desafio_sequencia,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    instituicao_id,
                    professor_id,
                    turma_id,
                    met_id,
                    semana,
                    resumo,
                    status,
                    origem,
                    tipo_aula,
                    Json(mesa),
                    desafio_grupo,
                    desafio_titulo,
                    desafio_seq,
                ),
            )
            plano = cur.fetchone()
            plano_id = str(plano["id"]) if plano else None

            curadoria_id = None
            curadoria_pei_id = None
            has_pei_adapt = False
            if has_adapt and plano_id:
                teacher_text = str(
                    payload.get("texto_sugestao")
                    or payload.get("teacher_adaptation_text")
                    or payload.get("sugestao_coordenacao")
                    or mesa.get("texto_sugestao")
                    or mesa.get("teacher_adaptation_text")
                    or ""
                ).strip() or None
                adaptations = (
                    payload.get("adaptations")
                    or mesa.get("adaptations")
                    or mesa.get("teacher_adaptations")
                )
                if teacher_text and not adaptations:
                    adaptations = {"texto": teacher_text}
                met_usada = str(
                    payload.get("metodologia_usada")
                    or payload.get("metodologia_nome")
                    or mesa.get("metodologia_nome")
                    or met_nome
                    or ""
                ).strip()
                aula_contexto = str(
                    payload.get("aula_contexto")
                    or mesa.get("aula_contexto")
                    or mesa.get("titulo")
                    or resumo
                    or met_usada
                    or ""
                ).strip()
                professor_nome = str(
                    payload.get("professor_nome")
                    or mesa.get("professor_nome")
                    or ""
                ).strip() or None
                professor_id_payload = str(
                    payload.get("professor_id")
                    or payload.get("professor_b2c_id")
                    or mesa.get("professor_id")
                    or ""
                ).strip() or None
                sugestao = {
                    "professor_id": professor_id_payload or professor_id,
                    "professor_nome": professor_nome,
                    "aula_contexto": aula_contexto,
                    "texto_sugestao": teacher_text,
                    "mesa": mesa,
                    "metodologia_usada": met_usada,
                    "teacher_adaptation_text": teacher_text,
                    "adaptations": adaptations,
                    "synced_at": datetime.utcnow().isoformat() + "Z",
                }
                cur.execute(
                    """
                    SELECT id FROM public.school_curadoria_metodologias
                    WHERE plano_espelhado_id = %s
                      AND status_analise = 'pendente'
                    LIMIT 1
                    """,
                    (plano_id,),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE public.school_curadoria_metodologias
                        SET sugestao_professor_json = %s,
                            metodologia_nome = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id
                        """,
                        (Json(sugestao), met_nome, str(existing["id"])),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO public.school_curadoria_metodologias (
                            instituicao_id,
                            metodologia_nome,
                            plano_espelhado_id,
                            sugestao_professor_json,
                            status_analise
                        )
                        VALUES (%s, %s, %s, %s, 'pendente')
                        RETURNING id
                        """,
                        (instituicao_id, met_nome, plano_id, Json(sugestao)),
                    )
                cur_row = cur.fetchone()
                curadoria_id = str(cur_row["id"]) if cur_row else None

            # --- Curadoria PEI (trincheira) ---
            has_pei_adapt = _truthy(
                payload.get("has_pei_adaptations")
                or mesa.get("has_pei_adaptations")
            )
            if has_pei_adapt and plano_id:
                pei_text = str(
                    payload.get("pei_adaptation_text")
                    or mesa.get("pei_adaptation_text")
                    or ""
                ).strip()
                pei_aluno = _as_uuid(
                    payload.get("pei_aluno_id")
                    or payload.get("pei_individualizado_id")
                    or mesa.get("pei_aluno_id")
                )
                # Se não veio ID, tenta match por nome do aluno no PEI documental.
                if not pei_aluno:
                    aluno_nome = str(
                        payload.get("aluno_nome")
                        or mesa.get("aluno_nome")
                        or ""
                    ).strip()
                    if aluno_nome:
                        cur.execute(
                            """
                            SELECT p.id
                            FROM public.school_pei_alunos p
                            JOIN public.school_alunos a ON a.id = p.aluno_id
                            WHERE p.instituicao_id = %s
                              AND p.status = 'ativo'
                              AND LOWER(TRIM(a.nome)) = LOWER(TRIM(%s))
                            ORDER BY p.versao DESC
                            LIMIT 1
                            """,
                            (instituicao_id, aluno_nome),
                        )
                        hit = cur.fetchone()
                        if hit:
                            pei_aluno = str(hit["id"])

                # Garante tabela (idempotente se migration ainda não rodou).
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.school_curadoria_pei (
                        id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        instituicao_id          UUID NOT NULL
                            REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
                        pei_aluno_id            UUID
                            REFERENCES public.school_pei_alunos (id)
                            ON DELETE SET NULL,
                        metodologia_nome        TEXT NOT NULL DEFAULT '',
                        sugestao_professor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        status_analise          VARCHAR(32) NOT NULL DEFAULT 'pendente',
                        plano_espelhado_id      UUID
                            REFERENCES public.school_planos_aula_espelhados (id)
                            ON DELETE SET NULL,
                        created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                sug_pei = {
                    "professor_id": str(
                        payload.get("professor_id")
                        or payload.get("professor_b2c_id")
                        or mesa.get("professor_id")
                        or professor_id
                        or ""
                    ).strip()
                    or None,
                    "professor_nome": str(
                        payload.get("professor_nome") or mesa.get("professor_nome") or ""
                    ).strip()
                    or None,
                    "aula_contexto": str(
                        payload.get("aula_contexto")
                        or mesa.get("aula_contexto")
                        or mesa.get("titulo")
                        or resumo
                        or met_nome
                        or ""
                    ).strip(),
                    "texto_sugestao": pei_text,
                    "pei_adaptation_text": pei_text,
                    "metodologia_nome": met_nome,
                    "mesa": mesa,
                    "synced_at": datetime.utcnow().isoformat() + "Z",
                }
                cur.execute(
                    """
                    INSERT INTO public.school_curadoria_pei (
                        instituicao_id,
                        pei_aluno_id,
                        metodologia_nome,
                        sugestao_professor_json,
                        status_analise,
                        plano_espelhado_id
                    )
                    VALUES (%s, %s, %s, %s, 'pendente', %s)
                    RETURNING id
                    """,
                    (
                        instituicao_id,
                        pei_aluno,
                        met_nome,
                        Json(sug_pei),
                        plano_id,
                    ),
                )
                pei_row = cur.fetchone()
                curadoria_pei_id = str(pei_row["id"]) if pei_row else None

    _log(
        f"LESSON_RECORD_SYNC instituicao={instituicao_id} "
        f"plano={plano_id} origem={origem} curadoria={curadoria_id} "
        f"curadoria_pei={curadoria_pei_id} adapt={has_adapt} pei_adapt={has_pei_adapt}"
    )
    return {
        "handled": True,
        "event": "LESSON_RECORD_SYNC",
        "plano_espelhado_id": plano_id,
        "origem_plano_b2c_id": origem,
        "curadoria_id": curadoria_id,
        "curadoria_pei_id": curadoria_pei_id,
        "has_teacher_adaptations": has_adapt,
        "has_pei_adaptations": bool(has_pei_adapt),
    }


def _handle_teacher_invite_accepted(payload: dict) -> dict:
    """B2C confirma aceite: grava id_clie real e promove vínculo pendente → ativo."""
    body = payload if isinstance(payload, dict) else {}
    email = str(body.get("professor_email") or body.get("email") or "").strip().lower()
    instituicao_id = _as_uuid(body.get("instituicao_id"))
    vinculo_id = _as_uuid(body.get("vinculo_id"))
    raw_b2c = body.get("professor_b2c_id")
    try:
        professor_b2c_id = int(raw_b2c)
    except (TypeError, ValueError):
        professor_b2c_id = None
    if not professor_b2c_id or professor_b2c_id <= 0:
        return {
            "handled": False,
            "reason": "professor_b2c_id inválido",
            "event": "TEACHER_INVITE_ACCEPTED",
        }
    if not instituicao_id and not vinculo_id and not email:
        return {
            "handled": False,
            "reason": "instituicao_id/vinculo_id/email obrigatórios",
            "event": "TEACHER_INVITE_ACCEPTED",
        }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = None
            if vinculo_id:
                cur.execute(
                    """
                    SELECT id, instituicao_id, email_convite, professor_b2c_id, status_vinculo
                    FROM public.school_professores_vinculo
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (vinculo_id,),
                )
                row = cur.fetchone()
            if not row and instituicao_id and email:
                cur.execute(
                    """
                    SELECT id, instituicao_id, email_convite, professor_b2c_id, status_vinculo
                    FROM public.school_professores_vinculo
                    WHERE instituicao_id = %s
                      AND LOWER(TRIM(email_convite)) = %s
                      AND status_vinculo IN ('pendente', 'ativo')
                    ORDER BY
                      CASE WHEN status_vinculo = 'pendente' THEN 0 ELSE 1 END,
                      created_at DESC
                    LIMIT 1
                    """,
                    (instituicao_id, email),
                )
                row = cur.fetchone()
            if not row and email:
                cur.execute(
                    """
                    SELECT id, instituicao_id, email_convite, professor_b2c_id, status_vinculo
                    FROM public.school_professores_vinculo
                    WHERE LOWER(TRIM(email_convite)) = %s
                      AND status_vinculo IN ('pendente', 'ativo')
                    ORDER BY
                      CASE WHEN status_vinculo = 'pendente' THEN 0 ELSE 1 END,
                      created_at DESC
                    LIMIT 1
                    """,
                    (email,),
                )
                row = cur.fetchone()
            if not row:
                return {
                    "handled": False,
                    "reason": "vinculo_not_found",
                    "event": "TEACHER_INVITE_ACCEPTED",
                }

            status = str(row.get("status_vinculo") or "")
            current_id = row.get("professor_b2c_id")
            try:
                current_id_int = int(current_id) if current_id is not None else None
            except (TypeError, ValueError):
                current_id_int = None

            if status == "ativo" and current_id_int == professor_b2c_id:
                _log(
                    f"TEACHER_INVITE_ACCEPTED idempotente vinculo={row['id']} "
                    f"id_clie={professor_b2c_id}"
                )
                return {
                    "handled": True,
                    "event": "TEACHER_INVITE_ACCEPTED",
                    "idempotent": True,
                    "vinculo_id": str(row["id"]),
                    "professor_b2c_id": professor_b2c_id,
                    "status_vinculo": "ativo",
                }

            if status == "revogado":
                return {
                    "handled": False,
                    "reason": "vinculo_revogado",
                    "event": "TEACHER_INVITE_ACCEPTED",
                    "vinculo_id": str(row["id"]),
                }

            cur.execute(
                """
                UPDATE public.school_professores_vinculo
                   SET professor_b2c_id = %s,
                       status_vinculo = 'ativo',
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                RETURNING id, status_vinculo, professor_b2c_id
                """,
                (professor_b2c_id, str(row["id"])),
            )
            updated = cur.fetchone()

    _log(
        f"TEACHER_INVITE_ACCEPTED vinculo={updated['id']} "
        f"id_clie={professor_b2c_id} status=ativo"
    )
    return {
        "handled": True,
        "event": "TEACHER_INVITE_ACCEPTED",
        "vinculo_id": str(updated["id"]),
        "professor_b2c_id": professor_b2c_id,
        "status_vinculo": "ativo",
        "instituicao_id": str(row["instituicao_id"]),
    }


@bp.post("/api/webhooks/b2c")
@require_b2c_bridge_jwt
def b2c_webhook():
    """Receptor School ← B2C. Gatekeeper S2S — sem login de gestor."""
    body = request.get_json(silent=True) or {}
    decoded = getattr(g, "bridge_jwt", {}) or {}
    event_type, payload = _event_payload(decoded, body)

    try:
        if event_type == "LESSON_RECORD_SYNC":
            result = _handle_lesson_record_sync(payload)
        elif event_type == "TEACHER_INVITE_ACCEPTED":
            result = _handle_teacher_invite_accepted(payload)
        else:
            _log(f"event_type desconhecido: {event_type or '(vazio)'}")
            print(
                f"[b2c-webhook] payload preview: {str(payload)[:300]}",
                file=sys.stderr,
                flush=True,
            )
            result = {
                "handled": False,
                "reason": "unknown_event",
                "event_type": event_type,
            }
    except Exception as exc:
        # ACK outbox mesmo com falha de processamento (evita retry infinito).
        _log(f"erro processando {event_type}: {exc}")
        print(f"[b2c-webhook] {exc}", file=sys.stderr, flush=True)
        result = {"handled": False, "error": str(exc), "event_type": event_type}

    return (
        jsonify(
            {
                "status": "received",
                "app": "inove4us-school",
                "event_type": event_type,
                "result": result,
            }
        ),
        200,
    )
