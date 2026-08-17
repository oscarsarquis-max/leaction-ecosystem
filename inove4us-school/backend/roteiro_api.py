"""Roteiro Guiado — respostas gravadas (homologação / treinamento).

Homologação com sessão nomeada: respostas isoladas por sessao_id.
Treinamento (e homologação legada sem sessão): escopo instituicao+gestor+tipo.
"""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import (
    current_gestor,
    require_gestor,
    require_zona,
    resolve_instituicao_id,
    zona_permite,
)
from db import get_conn

bp = Blueprint("roteiro_guiado", __name__)

TIPOS = frozenset({"homologacao", "treinamento"})
PASSOS_NUMERADOS = (
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
)
PASSOS_PERSISTIVEIS = frozenset(
    PASSOS_NUMERADOS
    + (
        "A.checkpoint",
        "B.checkpoint",
        "C.checkpoint",
        "feedback.entendi",
        "feedback.travou",
        "feedback.termo_estranho",
        "feedback.falta_para_usar",
        "feedback.impacto",
        "feedback.notas_livres",
    )
)
TOTAL_PASSOS = len(PASSOS_NUMERADOS)


def _parse_tipo(raw: Any, *, default: str = "homologacao") -> str | tuple:
    tipo = str(raw or default).strip().lower() or default
    if tipo not in TIPOS:
        return (
            jsonify(
                {
                    "error": "Tipo inválido. Use homologacao ou treinamento.",
                    "code": "INVALID_TIPO",
                }
            ),
            400,
        )
    return tipo


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


def _parse_sessao_id(raw: Any) -> uuid.UUID | None | tuple:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return uuid.UUID(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return (
            jsonify({"error": "sessao_id inválido", "code": "INVALID_SESSAO"}),
            400,
        )


def _assert_sessao_access(
    cur,
    *,
    sessao_id: uuid.UUID,
    instituicao_id: uuid.UUID,
    gestor_id: uuid.UUID,
    user: dict,
    for_write: bool,
) -> dict | tuple:
    cur.execute(
        """
        SELECT s.id, s.gestor_id, s.homologador_id, s.status, s.codigo,
               h.escopo_dados, h.gestor_id AS homologador_gestor_id
        FROM public.school_homologacao_sessoes s
        JOIN public.school_homologadores h ON h.id = s.homologador_id
        WHERE s.id = %s AND s.instituicao_id = %s
        LIMIT 1
        """,
        (str(sessao_id), str(instituicao_id)),
    )
    row = cur.fetchone()
    if not row:
        return (
            jsonify(
                {
                    "error": "Sessão de homologação não encontrada",
                    "code": "NOT_FOUND",
                }
            ),
            404,
        )

    cur.execute(
        """
        SELECT escopo_dados FROM public.school_homologadores
        WHERE instituicao_id = %s AND gestor_id = %s AND ativo = TRUE
        LIMIT 1
        """,
        (str(instituicao_id), str(gestor_id)),
    )
    me_h = cur.fetchone()
    owner = str(row["gestor_id"]) == str(gestor_id)
    if me_h and str(me_h.get("escopo_dados") or "") == "proprio" and not owner:
        return (
            jsonify(
                {
                    "error": "Roteiro desta sessão é de outro homologador.",
                    "code": "FORBIDDEN_SESSAO",
                }
            ),
            403,
        )
    if not owner:
        admin = zona_permite(user.get("zonas") or [], "administrativo")
        todos = (me_h and str(me_h.get("escopo_dados")) == "todos") or (
            str(row.get("escopo_dados") or "") == "todos"
        )
        if not (admin or todos):
            return (
                jsonify({"error": "Sem permissão nesta sessão", "code": "FORBIDDEN"}),
                403,
            )

    if for_write and row["status"] in ("concluida", "cancelada"):
        return (
            jsonify(
                {
                    "error": "Sessão encerrada — roteiro somente leitura.",
                    "code": "SESSAO_ENCERRADA",
                }
            ),
            409,
        )
    return row


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "passo_id": row["passo_id"],
        "concluido": bool(row.get("concluido")),
        "observacao": row.get("observacao") or "",
        "atualizado_em": row["atualizado_em"].isoformat()
        if row.get("atualizado_em")
        else None,
    }


@bp.get("/api/roteiro-guiado/historico")
@require_zona("administrativo")
def historico():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed

    tipo_raw = request.args.get("tipo")
    tipo_filter = None
    if tipo_raw is not None and str(tipo_raw).strip():
        tipo = _parse_tipo(tipo_raw)
        if isinstance(tipo, tuple):
            return tipo
        tipo_filter = tipo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, escopo_dados FROM public.school_homologadores
                WHERE instituicao_id = %s AND gestor_id = %s AND ativo = TRUE
                LIMIT 1
                """,
                (str(instituicao_id), str(gestor_id)),
            )
            me_h = cur.fetchone()
            only_mine = bool(
                me_h and str(me_h.get("escopo_dados") or "") == "proprio"
            )

            sql = """
                SELECT
                    g.id AS gestor_id,
                    g.nome AS gestor_nome,
                    g.email AS gestor_email,
                    i.razao_social AS instituicao,
                    r.tipo,
                    r.sessao_id,
                    s.codigo AS sessao_codigo,
                    COUNT(*) FILTER (
                        WHERE r.passo_id = ANY(%s) AND r.concluido IS TRUE
                    )::int AS passos_concluidos,
                    MAX(r.atualizado_em) AS atualizado_em
                FROM public.school_roteiro_respostas r
                JOIN public.school_gestores g ON g.id = r.gestor_id
                JOIN public.school_instituicoes i ON i.id = r.instituicao_id
                LEFT JOIN public.school_homologacao_sessoes s ON s.id = r.sessao_id
                WHERE r.instituicao_id = %s
            """
            params: list[Any] = [list(PASSOS_NUMERADOS), str(instituicao_id)]
            if tipo_filter:
                sql += " AND r.tipo = %s"
                params.append(tipo_filter)
            if only_mine:
                sql += " AND r.gestor_id = %s"
                params.append(str(gestor_id))
            sql += """
                GROUP BY g.id, g.nome, g.email, i.razao_social,
                         r.tipo, r.sessao_id, s.codigo
                ORDER BY atualizado_em DESC NULLS LAST, g.nome
            """
            cur.execute(sql, params)
            rows = cur.fetchall()

    itens = []
    for row in rows:
        concluidos = int(row.get("passos_concluidos") or 0)
        itens.append(
            {
                "gestor_id": str(row["gestor_id"]),
                "gestor": row["gestor_nome"],
                "email": row["gestor_email"],
                "instituicao": row["instituicao"],
                "tipo": row["tipo"],
                "sessao_id": str(row["sessao_id"]) if row.get("sessao_id") else None,
                "sessao_codigo": row.get("sessao_codigo"),
                "passos_concluidos": concluidos,
                "passos_total": TOTAL_PASSOS,
                "percentual": round(100.0 * concluidos / TOTAL_PASSOS)
                if TOTAL_PASSOS
                else 0,
                "atualizado_em": row["atualizado_em"].isoformat()
                if row.get("atualizado_em")
                else None,
            }
        )
    return jsonify({"ok": True, "itens": itens})


@bp.get("/api/roteiro-guiado")
@require_gestor
def get_estado():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}

    tipo = _parse_tipo(request.args.get("tipo"), default="homologacao")
    if isinstance(tipo, tuple):
        return tipo

    sessao = _parse_sessao_id(request.args.get("sessao_id"))
    if isinstance(sessao, tuple):
        return sessao

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if sessao:
                check = _assert_sessao_access(
                    cur,
                    sessao_id=sessao,
                    instituicao_id=instituicao_id,
                    gestor_id=gestor_id,
                    user=user,
                    for_write=False,
                )
                if isinstance(check, tuple):
                    return check
                cur.execute(
                    """
                    SELECT passo_id, concluido, observacao, atualizado_em
                    FROM public.school_roteiro_respostas
                    WHERE sessao_id = %s
                    ORDER BY passo_id
                    """,
                    (str(sessao),),
                )
            else:
                cur.execute(
                    """
                    SELECT passo_id, concluido, observacao, atualizado_em
                    FROM public.school_roteiro_respostas
                    WHERE instituicao_id = %s
                      AND gestor_id = %s
                      AND tipo = %s
                      AND sessao_id IS NULL
                    ORDER BY passo_id
                    """,
                    (str(instituicao_id), str(gestor_id), tipo),
                )
            rows = cur.fetchall()

    respostas = {row["passo_id"]: _serialize_row(row) for row in rows}
    return jsonify(
        {
            "ok": True,
            "tipo": tipo,
            "sessao_id": str(sessao) if sessao else None,
            "respostas": respostas,
        }
    )


@bp.patch("/api/roteiro-guiado/<passo_id>")
@require_gestor
def patch_passo(passo_id: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed
    user = current_gestor() or {}

    pid = str(passo_id or "").strip()
    if pid not in PASSOS_PERSISTIVEIS:
        return jsonify({"error": "Passo inválido", "code": "INVALID_PASSO"}), 400

    body = request.get_json(silent=True) or {}
    tipo = _parse_tipo(body.get("tipo"), default="homologacao")
    if isinstance(tipo, tuple):
        return tipo

    sessao = _parse_sessao_id(body.get("sessao_id"))
    if isinstance(sessao, tuple):
        return sessao

    if tipo == "homologacao" and sessao is None:
        return (
            jsonify(
                {
                    "error": (
                        "Homologação exige sessao_id. "
                        "Abra /homologacao e vincule a sessão."
                    ),
                    "code": "SESSAO_REQUIRED",
                }
            ),
            400,
        )

    concluido = bool(body.get("concluido"))
    observacao = body.get("observacao")
    if observacao is None:
        observacao = ""
    else:
        observacao = str(observacao)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if sessao:
                check = _assert_sessao_access(
                    cur,
                    sessao_id=sessao,
                    instituicao_id=instituicao_id,
                    gestor_id=gestor_id,
                    user=user,
                    for_write=True,
                )
                if isinstance(check, tuple):
                    return check
                cur.execute(
                    """
                    SELECT id FROM public.school_roteiro_respostas
                    WHERE sessao_id = %s AND passo_id = %s
                    LIMIT 1
                    """,
                    (str(sessao), pid),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE public.school_roteiro_respostas
                        SET concluido = %s,
                            observacao = %s,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING passo_id, concluido, observacao, atualizado_em
                        """,
                        (concluido, observacao, str(existing["id"])),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO public.school_roteiro_respostas (
                            instituicao_id, gestor_id, tipo, passo_id,
                            concluido, observacao, sessao_id, atualizado_em
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING passo_id, concluido, observacao, atualizado_em
                        """,
                        (
                            str(instituicao_id),
                            str(gestor_id),
                            tipo,
                            pid,
                            concluido,
                            observacao,
                            str(sessao),
                        ),
                    )
            else:
                cur.execute(
                    """
                    SELECT id FROM public.school_roteiro_respostas
                    WHERE instituicao_id = %s
                      AND gestor_id = %s
                      AND tipo = %s
                      AND passo_id = %s
                      AND sessao_id IS NULL
                    LIMIT 1
                    """,
                    (str(instituicao_id), str(gestor_id), tipo, pid),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE public.school_roteiro_respostas
                        SET concluido = %s,
                            observacao = %s,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING passo_id, concluido, observacao, atualizado_em
                        """,
                        (concluido, observacao, str(existing["id"])),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO public.school_roteiro_respostas (
                            instituicao_id, gestor_id, tipo, passo_id,
                            concluido, observacao, atualizado_em
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING passo_id, concluido, observacao, atualizado_em
                        """,
                        (
                            str(instituicao_id),
                            str(gestor_id),
                            tipo,
                            pid,
                            concluido,
                            observacao,
                        ),
                    )
            row = cur.fetchone()

    return jsonify(
        {
            "ok": True,
            "tipo": tipo,
            "sessao_id": str(sessao) if sessao else None,
            "resposta": _serialize_row(row),
        }
    )
