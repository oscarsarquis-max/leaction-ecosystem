"""Homologação multi-pessoa — sessões nomeadas, eventos e escopo por homologador.

Homologador com escopo_dados=proprio só vê/edita as próprias sessões.
Gestor administrativo da instituição (sem registro homologador, ou escopo=todos)
enxerga todas as sessões da instituição.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from auth_guards import (
    current_gestor,
    require_gestor,
    require_zona,
    resolve_instituicao_id,
    zona_permite,
)
from db import get_conn

bp = Blueprint("homologacao", __name__)

STATUS_OK = frozenset(
    {"preparada", "em_andamento", "pausada", "concluida", "cancelada"}
)
RESULTADOS = frozenset({"passou", "travou", "nao_concluido"})
EVENTO_TIPOS = frozenset(
    {
        "inicio",
        "pausa",
        "retomada",
        "interrupcao",
        "impressao",
        "nota",
        "fim",
        "status",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _session_ids():
    inst = resolve_instituicao_id()
    if isinstance(inst, tuple):
        return inst
    user = current_gestor() or {}
    try:
        gestor_id = uuid.UUID(str(user.get("id") or ""))
        instituicao_id = uuid.UUID(str(inst))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "Sessão inválida", "code": "UNAUTHENTICATED"}), 401
    return instituicao_id, gestor_id


def _load_homologador(cur, *, instituicao_id: uuid.UUID, gestor_id: uuid.UUID):
    cur.execute(
        """
        SELECT id, email, nome, funcao, escopo_dados, ativo
        FROM public.school_homologadores
        WHERE instituicao_id = %s AND gestor_id = %s AND ativo = TRUE
        LIMIT 1
        """,
        (str(instituicao_id), str(gestor_id)),
    )
    return cur.fetchone()


def _can_see_all(user: dict, homologador) -> bool:
    if homologador and str(homologador.get("escopo_dados") or "") == "todos":
        return True
    if homologador and str(homologador.get("escopo_dados") or "") == "proprio":
        return False
    return zona_permite(user.get("zonas") or [], "administrativo")


def _serialize_homologador(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "nome": row["nome"],
        "funcao": row.get("funcao") or "homologador",
        "escopo_dados": row.get("escopo_dados") or "proprio",
        "ativo": bool(row.get("ativo", True)),
        "gestor_id": str(row["gestor_id"]) if row.get("gestor_id") else None,
    }


def _tempo_efetivo_segundos(row: dict) -> int:
    base = int(row.get("tempo_ativo_segundos") or 0)
    if row.get("status") == "em_andamento" and row.get("periodo_ativo_inicio"):
        inicio = row["periodo_ativo_inicio"]
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        delta = int((_now() - inicio).total_seconds())
        if delta > 0:
            base += delta
    return max(0, base)


def _serialize_sessao(row: dict, *, include_progress: dict | None = None) -> dict:
    profissionais = row.get("profissionais") or []
    if isinstance(profissionais, str):
        profissionais = []
    out = {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "homologador_id": str(row["homologador_id"]),
        "gestor_id": str(row["gestor_id"]),
        "codigo": row["codigo"],
        "titulo": row.get("titulo") or "",
        "status": row["status"],
        "profissionais": profissionais,
        "impressoes": row.get("impressoes") or "",
        "resultado_geral": row.get("resultado_geral"),
        "versao_school": row.get("versao_school") or "",
        "versao_inove": row.get("versao_inove") or "",
        "iniciada_em": _iso(row.get("iniciada_em")),
        "encerrada_em": _iso(row.get("encerrada_em")),
        "tempo_ativo_segundos": _tempo_efetivo_segundos(row),
        "periodo_ativo_inicio": _iso(row.get("periodo_ativo_inicio")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "homologador_nome": row.get("homologador_nome"),
        "homologador_email": row.get("homologador_email"),
    }
    if include_progress is not None:
        out["roteiro"] = include_progress
    return out


def _flush_periodo_ativo(cur, row: dict) -> int:
    total = int(row.get("tempo_ativo_segundos") or 0)
    if row.get("periodo_ativo_inicio"):
        inicio = row["periodo_ativo_inicio"]
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        delta = int((_now() - inicio).total_seconds())
        if delta > 0:
            total += delta
    cur.execute(
        """
        UPDATE public.school_homologacao_sessoes
        SET tempo_ativo_segundos = %s,
            periodo_ativo_inicio = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING tempo_ativo_segundos
        """,
        (total, str(row["id"])),
    )
    return int(cur.fetchone()["tempo_ativo_segundos"])


def _insert_evento(
    cur,
    *,
    sessao_id: str,
    tipo: str,
    texto: str | None,
    gestor_id: uuid.UUID,
    meta: dict | None = None,
) -> dict:
    cur.execute(
        """
        INSERT INTO public.school_homologacao_eventos (
            sessao_id, tipo, texto, meta, criado_por_gestor_id
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING id, sessao_id, tipo, texto, meta, criado_por_gestor_id, criado_em
        """,
        (sessao_id, tipo, texto or "", Json(meta or {}), str(gestor_id)),
    )
    return cur.fetchone()


def _fetch_sessao(cur, sessao_id: str, instituicao_id: uuid.UUID):
    cur.execute(
        """
        SELECT s.*,
               h.nome AS homologador_nome,
               h.email AS homologador_email,
               h.escopo_dados AS homologador_escopo
        FROM public.school_homologacao_sessoes s
        JOIN public.school_homologadores h ON h.id = s.homologador_id
        WHERE s.id = %s AND s.instituicao_id = %s
        LIMIT 1
        """,
        (sessao_id, str(instituicao_id)),
    )
    return cur.fetchone()


def _assert_sessao_access(*, user: dict, homologador, sessao: dict):
    if _can_see_all(user, homologador):
        return None
    if not homologador:
        return jsonify({"error": "Sem permissão", "code": "FORBIDDEN"}), 403
    if str(sessao["homologador_id"]) != str(homologador["id"]):
        return (
            jsonify(
                {
                    "error": "Esta sessão pertence a outro homologador.",
                    "code": "FORBIDDEN_SESSAO",
                }
            ),
            403,
        )
    return None


def _slug_codigo(nome: str, email: str) -> str:
    base = (email.split("@")[0] if email else nome or "homolog").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "homolog"
    day = _now().strftime("%Y%m%d")
    return f"HOMOLOG-{day}-{base}"[:80]


def _roteiro_progress(cur, sessao_id: str) -> dict:
    passos = [
        "A.1",
        "A.2",
        "A.3",
        "A.4",
        "A.5",
        "A.6",
        "B.7",
        "B.8",
        "B.9",
        "C.10",
        "C.11",
    ]
    cur.execute(
        """
        SELECT COUNT(*) FILTER (
            WHERE passo_id = ANY(%s) AND concluido IS TRUE
        )::int AS ok
        FROM public.school_roteiro_respostas
        WHERE sessao_id = %s
        """,
        (passos, sessao_id),
    )
    ok = int(cur.fetchone()["ok"] or 0)
    total = len(passos)
    return {
        "passos_concluidos": ok,
        "passos_total": total,
        "percentual": round(100.0 * ok / total) if total else 0,
    }


@bp.get("/api/homologacao/me")
@require_gestor
def me():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )

    return jsonify(
        {
            "ok": True,
            "homologador": (
                {
                    "id": str(h["id"]),
                    "email": h["email"],
                    "nome": h["nome"],
                    "funcao": h["funcao"],
                    "escopo_dados": h["escopo_dados"],
                }
                if h
                else None
            ),
            "pode_ver_todas": _can_see_all(user, h),
            "pode_administrar": zona_permite(
                user.get("zonas") or [], "administrativo"
            ),
        }
    )


@bp.get("/api/homologacao/homologadores")
@require_zona("administrativo")
def list_homologadores():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            if not _can_see_all(user, h):
                cur.execute(
                    """
                    SELECT id, gestor_id, email, nome, funcao, escopo_dados, ativo
                    FROM public.school_homologadores
                    WHERE id = %s
                    """,
                    (str(h["id"]),),
                )
                rows = cur.fetchall()
            else:
                cur.execute(
                    """
                    SELECT id, gestor_id, email, nome, funcao, escopo_dados, ativo
                    FROM public.school_homologadores
                    WHERE instituicao_id = %s
                    ORDER BY nome
                    """,
                    (str(instituicao_id),),
                )
                rows = cur.fetchall()

    return jsonify({"ok": True, "itens": [_serialize_homologador(r) for r in rows]})


@bp.get("/api/homologacao/sessoes")
@require_gestor
def list_sessoes():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}
    status_filter = (request.args.get("status") or "").strip().lower() or None
    if status_filter and status_filter not in STATUS_OK:
        return jsonify({"error": "Status inválido", "code": "INVALID_STATUS"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            see_all = _can_see_all(user, h)
            if not see_all and not h:
                return (
                    jsonify(
                        {
                            "error": "Sem perfil de homologador nem zona administrativa.",
                            "code": "FORBIDDEN",
                        }
                    ),
                    403,
                )

            sql = """
                SELECT s.*,
                       h.nome AS homologador_nome,
                       h.email AS homologador_email
                FROM public.school_homologacao_sessoes s
                JOIN public.school_homologadores h ON h.id = s.homologador_id
                WHERE s.instituicao_id = %s
            """
            params: list[Any] = [str(instituicao_id)]
            if not see_all:
                sql += " AND s.homologador_id = %s"
                params.append(str(h["id"]))
            if status_filter:
                sql += " AND s.status = %s"
                params.append(status_filter)
            sql += " ORDER BY s.updated_at DESC NULLS LAST, s.created_at DESC"

            cur.execute(sql, params)
            rows = cur.fetchall()
            itens = []
            for row in rows:
                progress = _roteiro_progress(cur, str(row["id"]))
                itens.append(_serialize_sessao(row, include_progress=progress))

    return jsonify({"ok": True, "itens": itens, "pode_ver_todas": see_all})


@bp.post("/api/homologacao/sessoes")
@require_gestor
def create_sessao():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            me_h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            see_all = _can_see_all(user, me_h)

            target_homologador_id = body.get("homologador_id")
            if target_homologador_id:
                if not see_all:
                    return (
                        jsonify(
                            {
                                "error": "Só pode criar sessão para o próprio perfil.",
                                "code": "FORBIDDEN",
                            }
                        ),
                        403,
                    )
                cur.execute(
                    """
                    SELECT id, gestor_id, email, nome
                    FROM public.school_homologadores
                    WHERE id = %s AND instituicao_id = %s AND ativo = TRUE
                    """,
                    (str(target_homologador_id), str(instituicao_id)),
                )
                target = cur.fetchone()
            else:
                if not me_h:
                    return (
                        jsonify(
                            {
                                "error": "Cadastre-se como homologador antes de abrir sessão.",
                                "code": "NOT_HOMOLOGADOR",
                            }
                        ),
                        400,
                    )
                cur.execute(
                    """
                    SELECT id, gestor_id, email, nome
                    FROM public.school_homologadores WHERE id = %s
                    """,
                    (str(me_h["id"]),),
                )
                target = cur.fetchone()

            if not target:
                return (
                    jsonify({"error": "Homologador não encontrado", "code": "NOT_FOUND"}),
                    404,
                )

            codigo = str(body.get("codigo") or "").strip()
            if not codigo:
                codigo = _slug_codigo(target["nome"], target["email"])
            titulo = str(
                body.get("titulo") or f"Homologação — {target['nome']}"
            ).strip()
            profissionais = body.get("profissionais")
            if not isinstance(profissionais, list):
                profissionais = [
                    {
                        "nome": target["nome"],
                        "papel": "homologador",
                        "email": target["email"],
                    }
                ]

            try:
                cur.execute(
                    """
                    INSERT INTO public.school_homologacao_sessoes (
                        instituicao_id, homologador_id, gestor_id,
                        codigo, titulo, status, profissionais,
                        versao_school, versao_inove
                    ) VALUES (
                        %s, %s, %s, %s, %s, 'preparada', %s, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        str(instituicao_id),
                        str(target["id"]),
                        str(target["gestor_id"]),
                        codigo[:80],
                        titulo[:200],
                        Json(profissionais),
                        str(body.get("versao_school") or "")[:40] or None,
                        str(body.get("versao_inove") or "")[:40] or None,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                if "uq_school_homologacao_sessoes_codigo" in str(exc):
                    return (
                        jsonify(
                            {
                                "error": f"Já existe sessão com código {codigo}.",
                                "code": "DUPLICATE_CODIGO",
                            }
                        ),
                        409,
                    )
                raise

            row = cur.fetchone()
            _insert_evento(
                cur,
                sessao_id=str(row["id"]),
                tipo="status",
                texto="Sessão criada",
                gestor_id=gestor_id,
                meta={"status": "preparada"},
            )
            row["homologador_nome"] = target["nome"]
            row["homologador_email"] = target["email"]

    return jsonify({"ok": True, "sessao": _serialize_sessao(row)}), 201


@bp.get("/api/homologacao/sessoes/<sessao_id>")
@require_gestor
def get_sessao(sessao_id: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            row = _fetch_sessao(cur, sessao_id, instituicao_id)
            if not row:
                return (
                    jsonify({"error": "Sessão não encontrada", "code": "NOT_FOUND"}),
                    404,
                )
            denied = _assert_sessao_access(user=user, homologador=h, sessao=row)
            if denied:
                return denied
            progress = _roteiro_progress(cur, str(row["id"]))
            cur.execute(
                """
                SELECT id, tipo, texto, meta, criado_por_gestor_id, criado_em
                FROM public.school_homologacao_eventos
                WHERE sessao_id = %s
                ORDER BY criado_em ASC
                """,
                (str(row["id"]),),
            )
            eventos = cur.fetchall()

    return jsonify(
        {
            "ok": True,
            "sessao": _serialize_sessao(row, include_progress=progress),
            "eventos": [
                {
                    "id": str(e["id"]),
                    "tipo": e["tipo"],
                    "texto": e.get("texto") or "",
                    "meta": e.get("meta") or {},
                    "criado_por_gestor_id": (
                        str(e["criado_por_gestor_id"])
                        if e.get("criado_por_gestor_id")
                        else None
                    ),
                    "criado_em": _iso(e.get("criado_em")),
                }
                for e in eventos
            ],
        }
    )


@bp.patch("/api/homologacao/sessoes/<sessao_id>")
@require_gestor
def patch_sessao(sessao_id: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            row = _fetch_sessao(cur, sessao_id, instituicao_id)
            if not row:
                return (
                    jsonify({"error": "Sessão não encontrada", "code": "NOT_FOUND"}),
                    404,
                )
            denied = _assert_sessao_access(user=user, homologador=h, sessao=row)
            if denied:
                return denied

            fields: list[str] = []
            params: list[Any] = []

            if "titulo" in body:
                fields.append("titulo = %s")
                params.append(str(body.get("titulo") or "")[:200])
            if "profissionais" in body:
                if not isinstance(body["profissionais"], list):
                    return (
                        jsonify(
                            {
                                "error": "profissionais deve ser lista",
                                "code": "INVALID",
                            }
                        ),
                        400,
                    )
                fields.append("profissionais = %s")
                params.append(Json(body["profissionais"]))
            if "impressoes" in body:
                fields.append("impressoes = %s")
                params.append(str(body.get("impressoes") or ""))
            if "resultado_geral" in body:
                rg = body.get("resultado_geral")
                if rg is not None and str(rg) not in RESULTADOS:
                    return (
                        jsonify(
                            {
                                "error": "resultado_geral inválido",
                                "code": "INVALID",
                            }
                        ),
                        400,
                    )
                fields.append("resultado_geral = %s")
                params.append(str(rg) if rg is not None else None)
            if "versao_school" in body:
                fields.append("versao_school = %s")
                params.append(str(body.get("versao_school") or "")[:40] or None)
            if "versao_inove" in body:
                fields.append("versao_inove = %s")
                params.append(str(body.get("versao_inove") or "")[:40] or None)

            if not fields:
                return jsonify({"error": "Nada para atualizar", "code": "EMPTY"}), 400

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(str(row["id"]))
            cur.execute(
                f"""
                UPDATE public.school_homologacao_sessoes
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING *
                """,
                params,
            )
            updated = cur.fetchone()
            updated["homologador_nome"] = row["homologador_nome"]
            updated["homologador_email"] = row["homologador_email"]

            if "impressoes" in body and str(body.get("impressoes") or "").strip():
                _insert_evento(
                    cur,
                    sessao_id=str(row["id"]),
                    tipo="impressao",
                    texto=str(body.get("impressoes") or "")[:2000],
                    gestor_id=gestor_id,
                )

    return jsonify({"ok": True, "sessao": _serialize_sessao(updated)})


def _transition(sessao_id: str, *, action: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}
    body = request.get_json(silent=True) or {}
    nota = str(body.get("texto") or body.get("nota") or "").strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            row = _fetch_sessao(cur, sessao_id, instituicao_id)
            if not row:
                return (
                    jsonify({"error": "Sessão não encontrada", "code": "NOT_FOUND"}),
                    404,
                )
            denied = _assert_sessao_access(user=user, homologador=h, sessao=row)
            if denied:
                return denied

            status = row["status"]
            evento_tipo = action
            novo_status = status

            if action == "iniciar":
                if status not in ("preparada", "pausada"):
                    return (
                        jsonify(
                            {
                                "error": f"Não dá para iniciar a partir de '{status}'.",
                                "code": "INVALID_TRANSITION",
                            }
                        ),
                        409,
                    )
                evento_tipo = "retomada" if status == "pausada" else "inicio"
                cur.execute(
                    """
                    UPDATE public.school_homologacao_sessoes
                    SET status = 'em_andamento',
                        iniciada_em = COALESCE(iniciada_em, CURRENT_TIMESTAMP),
                        periodo_ativo_inicio = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (str(row["id"]),),
                )
                novo_status = "em_andamento"
            elif action == "pausar":
                if status != "em_andamento":
                    return (
                        jsonify(
                            {
                                "error": "Só é possível pausar sessão em andamento.",
                                "code": "INVALID_TRANSITION",
                            }
                        ),
                        409,
                    )
                _flush_periodo_ativo(cur, row)
                cur.execute(
                    """
                    UPDATE public.school_homologacao_sessoes
                    SET status = 'pausada', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (str(row["id"]),),
                )
                novo_status = "pausada"
                evento_tipo = "pausa"
            elif action == "retomar":
                if status != "pausada":
                    return (
                        jsonify(
                            {
                                "error": "Só é possível retomar sessão pausada.",
                                "code": "INVALID_TRANSITION",
                            }
                        ),
                        409,
                    )
                cur.execute(
                    """
                    UPDATE public.school_homologacao_sessoes
                    SET status = 'em_andamento',
                        periodo_ativo_inicio = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (str(row["id"]),),
                )
                novo_status = "em_andamento"
                evento_tipo = "retomada"
            elif action == "encerrar":
                if status in ("concluida", "cancelada"):
                    return (
                        jsonify(
                            {
                                "error": "Sessão já encerrada.",
                                "code": "INVALID_TRANSITION",
                            }
                        ),
                        409,
                    )
                if status == "em_andamento":
                    _flush_periodo_ativo(cur, row)
                resultado = body.get("resultado_geral")
                if resultado is not None and str(resultado) not in RESULTADOS:
                    return (
                        jsonify(
                            {
                                "error": "resultado_geral inválido",
                                "code": "INVALID",
                            }
                        ),
                        400,
                    )
                cur.execute(
                    """
                    UPDATE public.school_homologacao_sessoes
                    SET status = 'concluida',
                        encerrada_em = CURRENT_TIMESTAMP,
                        periodo_ativo_inicio = NULL,
                        resultado_geral = COALESCE(%s, resultado_geral),
                        impressoes = CASE
                            WHEN %s IS NOT NULL AND length(%s) > 0 THEN %s
                            ELSE impressoes
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        str(resultado) if resultado is not None else None,
                        nota or None,
                        nota or None,
                        nota or None,
                        str(row["id"]),
                    ),
                )
                novo_status = "concluida"
                evento_tipo = "fim"
            else:
                return jsonify({"error": "Ação inválida", "code": "INVALID"}), 400

            updated = cur.fetchone()
            updated["homologador_nome"] = row["homologador_nome"]
            updated["homologador_email"] = row["homologador_email"]
            _insert_evento(
                cur,
                sessao_id=str(row["id"]),
                tipo=evento_tipo,
                texto=nota or f"Status → {novo_status}",
                gestor_id=gestor_id,
                meta={"status": novo_status, "action": action},
            )

    return jsonify({"ok": True, "sessao": _serialize_sessao(updated)})


@bp.post("/api/homologacao/sessoes/<sessao_id>/iniciar")
@require_gestor
def iniciar(sessao_id: str):
    return _transition(sessao_id, action="iniciar")


@bp.post("/api/homologacao/sessoes/<sessao_id>/pausar")
@require_gestor
def pausar(sessao_id: str):
    return _transition(sessao_id, action="pausar")


@bp.post("/api/homologacao/sessoes/<sessao_id>/retomar")
@require_gestor
def retomar(sessao_id: str):
    return _transition(sessao_id, action="retomar")


@bp.post("/api/homologacao/sessoes/<sessao_id>/encerrar")
@require_gestor
def encerrar(sessao_id: str):
    return _transition(sessao_id, action="encerrar")


@bp.post("/api/homologacao/sessoes/<sessao_id>/eventos")
@require_gestor
def add_evento(sessao_id: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}
    body = request.get_json(silent=True) or {}
    tipo = str(body.get("tipo") or "").strip().lower()
    if tipo not in EVENTO_TIPOS:
        return (
            jsonify(
                {
                    "error": "Tipo de evento inválido.",
                    "code": "INVALID_TIPO",
                    "tipos": sorted(EVENTO_TIPOS),
                }
            ),
            400,
        )
    texto = str(body.get("texto") or "").strip()
    if tipo in ("interrupcao", "impressao", "nota") and not texto:
        return (
            jsonify({"error": "Informe o texto do evento.", "code": "EMPTY_TEXTO"}),
            400,
        )

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            h = _load_homologador(
                cur, instituicao_id=instituicao_id, gestor_id=gestor_id
            )
            row = _fetch_sessao(cur, sessao_id, instituicao_id)
            if not row:
                return (
                    jsonify({"error": "Sessão não encontrada", "code": "NOT_FOUND"}),
                    404,
                )
            denied = _assert_sessao_access(user=user, homologador=h, sessao=row)
            if denied:
                return denied

            ev = _insert_evento(
                cur,
                sessao_id=str(row["id"]),
                tipo=tipo,
                texto=texto,
                gestor_id=gestor_id,
                meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
            )

            if tipo == "impressao" and texto:
                cur.execute(
                    """
                    UPDATE public.school_homologacao_sessoes
                    SET impressoes = CASE
                            WHEN impressoes IS NULL OR impressoes = '' THEN %s
                            ELSE impressoes || E'\\n\\n' || %s
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (texto, texto, str(row["id"])),
                )

    return (
        jsonify(
            {
                "ok": True,
                "evento": {
                    "id": str(ev["id"]),
                    "tipo": ev["tipo"],
                    "texto": ev.get("texto") or "",
                    "meta": ev.get("meta") or {},
                    "criado_em": _iso(ev.get("criado_em")),
                },
            }
        ),
        201,
    )
