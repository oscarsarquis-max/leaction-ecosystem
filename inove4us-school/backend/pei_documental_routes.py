"""AEE (matriz por condição) + PEI individual + adaptações metodológicas.

GET  /api/aee/condicoes
GET  /api/aee/matriz?condicao=
GET  /api/aee/matriz/<id>
GET  /api/aee/matrizes/<condicao>/historico
PUT  /api/aee/matriz/<id>
POST /api/aee/matriz/<id>/enviar-aprovacao
POST /api/aee/matriz/assinar/coordenador
POST /api/aee/matriz/assinar/psicopedagogo

GET/POST /api/pei/alunos
GET/PUT  /api/pei/alunos/<id>
GET      /api/pei/alunos/<id>/historico
POST     /api/pei/alunos/<id>/nova-versao
POST     /api/pei/alunos/<id>/assinar/coordenador|psicopedagogo

GET  /api/pei/metodologias
GET  /api/pei/curadoria?metodologia_nome=
POST /api/pei/curadoria/<id>/incorporar
POST /api/pei/metodologia/<id>/adaptar-ia
PUT  /api/pei/metodologia/<id>/versao

GET  /api/aee/<aee_id>/metodologias
PUT  /api/aee/<aee_id>/metodologias/<metodologia_nome>
POST /api/aee/<aee_id>/metodologia/<metodologia_nome>/adaptar-ia
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from aee_canonico import condicao_valida, get_canonico, listar_condicoes
from db import get_conn

bp = Blueprint("pei_documental", __name__)

SESSION_KEY = "school_gestor"


def _instituicao_id() -> str:
    user = session.get(SESSION_KEY) or {}
    return str(
        user.get("instituicao_id")
        or os.getenv("DEV_INSTITUICAO_ID")
        or "a1111111-1111-4111-8111-111111111111"
    ).strip()


def _parse_uuid(value: Any):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _status_str(row: dict[str, Any]) -> str:
    status = row.get("status")
    if hasattr(status, "value"):
        return str(status.value)
    return str(status or "")


def _iso(ts) -> str | None:
    if not ts:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def _serialize_aee(row: dict[str, Any], canon: dict[str, str] | None = None) -> dict[str, Any]:
    cond = row.get("condicao_categoria") or ""
    c = canon or get_canonico(cond) or {}
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "versao": int(row["versao"]),
        "condicao_categoria": cond,
        "texto_escola": row.get("texto_escola") or "",
        "campos_experiencia_metodologica": row.get("campos_experiencia_metodologica")
        or "",
        "texto_canonico": c.get("descricao_base_canonica") or "",
        "campos_experiencia_canonica": c.get("campos_experiencia_metodologica_canonica")
        or "",
        "status": _status_str(row),
        "assinado_coordenador": bool(row.get("assinado_coordenador")),
        "assinado_psicopedagogo": bool(row.get("assinado_psicopedagogo")),
        "data_assinatura_coordenador": _iso(row.get("data_assinatura_coordenador")),
        "data_assinatura_psicopedagogo": _iso(row.get("data_assinatura_psicopedagogo")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _serialize_pei(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("status") or (
        "ativo"
        if row.get("assinado_coordenador") and row.get("assinado_psicopedagogo")
        else "rascunho"
    )
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "aee_matriz_id": str(row["aee_matriz_id"]),
        "aee_versao": row.get("aee_versao"),
        "condicao_categoria": row.get("condicao_categoria") or "",
        "pei_linha_id": str(row["pei_linha_id"]) if row.get("pei_linha_id") else str(row["id"]),
        "versao": int(row["versao"] or 1),
        "status": str(status),
        "nome_completo": row.get("nome_completo") or "",
        "matricula": row.get("matricula") or "",
        "nome_responsavel": row.get("nome_responsavel") or "",
        "perfil_atual_habilidades": row.get("perfil_atual_habilidades") or "",
        "barreiras_identificadas": row.get("barreiras_identificadas") or "",
        "metas_desenvolvimento": row.get("metas_desenvolvimento") or "",
        "recursos_assistivos": row.get("recursos_assistivos") or "",
        "criterios_avaliacao_flexibilizados": row.get(
            "criterios_avaliacao_flexibilizados"
        )
        or "",
        "experiencias_adaptadas_individuais": row.get(
            "experiencias_adaptadas_individuais"
        )
        or "",
        "assinado_coordenador": bool(row.get("assinado_coordenador")),
        "assinado_psicopedagogo": bool(row.get("assinado_psicopedagogo")),
        "valido": bool(row.get("assinado_coordenador"))
        and bool(row.get("assinado_psicopedagogo")),
        "data_assinatura": _iso(row.get("data_assinatura")),
        "data_assinatura_coordenador": _iso(row.get("data_assinatura_coordenador")),
        "data_assinatura_psicopedagogo": _iso(row.get("data_assinatura_psicopedagogo")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _ensure_rascunho(cur, inst: str, condicao: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT * FROM public.school_aee_matrizes
        WHERE instituicao_id = %s AND condicao_categoria = %s
        ORDER BY versao DESC
        LIMIT 1
        """,
        (inst, condicao),
    )
    latest = cur.fetchone()
    if latest:
        return latest

    canon = get_canonico(condicao) or {}
    cur.execute(
        """
        INSERT INTO public.school_aee_matrizes (
            instituicao_id, versao, condicao_categoria,
            texto_escola, campos_experiencia_metodologica, status
        )
        VALUES (%s, 1, %s, %s, %s, 'rascunho')
        RETURNING *
        """,
        (
            inst,
            condicao,
            canon.get("descricao_base_canonica") or "",
            canon.get("campos_experiencia_metodologica_canonica") or "",
        ),
    )
    return cur.fetchone()


def _aee_ativa(cur, inst: str, condicao: str | None = None) -> dict[str, Any] | None:
    if condicao:
        cur.execute(
            """
            SELECT * FROM public.school_aee_matrizes
            WHERE instituicao_id = %s
              AND condicao_categoria = %s
              AND status = 'ativo'
            ORDER BY versao DESC
            LIMIT 1
            """,
            (inst, condicao),
        )
    else:
        cur.execute(
            """
            SELECT * FROM public.school_aee_matrizes
            WHERE instituicao_id = %s AND status = 'ativo'
            ORDER BY updated_at DESC, versao DESC
            LIMIT 1
            """,
            (inst,),
        )
    return cur.fetchone()


def _passos_to_text(passos: Any) -> str:
    if passos is None:
        return ""
    if isinstance(passos, str):
        return passos.strip()
    if not isinstance(passos, list):
        return str(passos).strip()
    lines: list[str] = []
    for p in passos:
        if isinstance(p, str):
            if p.strip():
                lines.append(p.strip())
            continue
        if not isinstance(p, dict):
            continue
        titulo = str(p.get("titulo") or "").strip()
        mec = str(
            p.get("mecanica_passo_a_passo") or p.get("como_executar_detalhado") or ""
        ).strip()
        if titulo and mec and titulo != mec:
            lines.append(f"{titulo}: {mec}")
        else:
            line = titulo or mec
            if line:
                lines.append(line)
    return "\n".join(lines)


def _ensure_aee_met_org_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.school_aee_metodologias_org (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                aee_matriz_id        UUID NOT NULL
                    REFERENCES public.school_aee_matrizes (id) ON DELETE CASCADE,
                metodologia_nome     VARCHAR(255) NOT NULL,
                passos_customizados  TEXT NOT NULL DEFAULT '',
                updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_school_aee_metodologias_org_matriz_met
                    UNIQUE (aee_matriz_id, metodologia_nome)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_school_aee_metodologias_org_matriz
                ON public.school_aee_metodologias_org (aee_matriz_id)
            """
        )


def _get_aee_matriz(cur, aee_id: uuid.UUID, inst: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT * FROM public.school_aee_matrizes
        WHERE id = %s AND instituicao_id = %s
        LIMIT 1
        """,
        (str(aee_id), inst),
    )
    return cur.fetchone()


# ---------------------------------------------------------------------------
# AEE — condições e matriz
# ---------------------------------------------------------------------------


@bp.get("/api/aee/condicoes")
def get_condicoes():
    return jsonify(listar_condicoes())


@bp.get("/api/aee/matriz")
def get_matriz_aee():
    inst = _instituicao_id()
    condicao = str(request.args.get("condicao") or "TEA").strip()
    if not condicao_valida(condicao):
        return jsonify({"error": f"Condição inválida: {condicao}"}), 400
    # normaliza nome canônico
    canon = get_canonico(condicao)
    for nome in (c["condicao_categoria"] for c in listar_condicoes()):
        if nome.lower() == condicao.lower():
            condicao = nome
            break

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT 1 FROM public.school_instituicoes WHERE id = %s", (inst,)
            )
            if not cur.fetchone():
                return jsonify({"error": "Instituição não encontrada"}), 404
            _ensure_rascunho(cur, inst, condicao)
            cur.execute(
                """
                SELECT * FROM public.school_aee_matrizes
                WHERE instituicao_id = %s AND condicao_categoria = %s
                ORDER BY versao DESC
                """,
                (inst, condicao),
            )
            rows = cur.fetchall()

    timeline = [_serialize_aee(r, canon) for r in rows]
    ativa = next((m for m in timeline if m["status"] == "ativo"), None)
    atual = timeline[0] if timeline else None
    editavel = next((m for m in timeline if m["status"] == "rascunho"), None)
    aguardando = next(
        (m for m in timeline if m["status"] == "aguardando_assinaturas"), None
    )
    return jsonify(
        {
            "condicao_categoria": condicao,
            "canonico": {
                "descricao_base_canonica": (canon or {}).get("descricao_base_canonica")
                or "",
                "campos_experiencia_metodologica_canonica": (canon or {}).get(
                    "campos_experiencia_metodologica_canonica"
                )
                or "",
            },
            "atual": atual,
            "ativa": ativa,
            "editavel": editavel,
            "aguardando": aguardando,
            "timeline": timeline,
        }
    )


@bp.put("/api/aee/matriz/<matriz_id>")
def atualizar_matriz_aee(matriz_id: str):
    mid = _parse_uuid(matriz_id)
    if not mid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM public.school_aee_matrizes
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(mid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Matriz AEE não encontrada"}), 404
            if _status_str(row) != "rascunho":
                return jsonify(
                    {"error": "Só é possível editar matrizes em rascunho"}
                ), 409

            texto = body.get("texto_escola")
            campos = body.get("campos_experiencia_metodologica")
            cur.execute(
                """
                UPDATE public.school_aee_matrizes
                SET texto_escola = COALESCE(%s, texto_escola),
                    campos_experiencia_metodologica = COALESCE(%s, campos_experiencia_metodologica),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (
                    str(texto) if texto is not None else None,
                    str(campos) if campos is not None else None,
                    str(mid),
                ),
            )
            updated = cur.fetchone()
    return jsonify(_serialize_aee(updated))


@bp.post("/api/aee/matriz/<matriz_id>/enviar-aprovacao")
def enviar_aprovacao_aee(matriz_id: str):
    mid = _parse_uuid(matriz_id)
    if not mid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM public.school_aee_matrizes
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(mid), inst),
            )
            src = cur.fetchone()
            if not src:
                return jsonify({"error": "Matriz AEE não encontrada"}), 404
            if _status_str(src) != "rascunho":
                return jsonify(
                    {"error": "Envie para aprovação apenas matrizes em rascunho"}
                ), 409

            condicao = src["condicao_categoria"]
            texto = str(
                body.get("texto_escola")
                if body.get("texto_escola") is not None
                else src["texto_escola"] or ""
            ).strip()
            campos = str(
                body.get("campos_experiencia_metodologica")
                if body.get("campos_experiencia_metodologica") is not None
                else src["campos_experiencia_metodologica"] or ""
            ).strip()
            if not texto:
                return jsonify({"error": "Informe o texto da escola antes de enviar"}), 400

            cur.execute(
                """
                SELECT COALESCE(MAX(versao), 0) AS max_v
                FROM public.school_aee_matrizes
                WHERE instituicao_id = %s AND condicao_categoria = %s
                """,
                (inst, condicao),
            )
            next_v = int(cur.fetchone()["max_v"]) + 1

            cur.execute(
                """
                UPDATE public.school_aee_matrizes
                SET status = 'arquivado',
                    texto_escola = %s,
                    campos_experiencia_metodologica = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (texto, campos, str(mid)),
            )

            cur.execute(
                """
                INSERT INTO public.school_aee_matrizes (
                    instituicao_id, versao, condicao_categoria,
                    texto_escola, campos_experiencia_metodologica,
                    status, assinado_coordenador, assinado_psicopedagogo
                )
                VALUES (%s, %s, %s, %s, %s, 'aguardando_assinaturas', FALSE, FALSE)
                RETURNING *
                """,
                (inst, next_v, condicao, texto, campos),
            )
            nova = cur.fetchone()

            cur.execute(
                """
                INSERT INTO public.school_aee_matrizes (
                    instituicao_id, versao, condicao_categoria,
                    texto_escola, campos_experiencia_metodologica, status
                )
                VALUES (%s, %s, %s, %s, %s, 'rascunho')
                """,
                (inst, next_v + 1, condicao, texto, campos),
            )

    return jsonify(
        {
            "message": f"Versão {nova['versao']} ({condicao}) enviada para assinaturas.",
            "matriz": _serialize_aee(nova),
        }
    ), 201


def _assinar_aee(papel: str):
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    mid = _parse_uuid(body.get("matriz_id"))
    condicao = str(body.get("condicao_categoria") or body.get("condicao") or "").strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if mid:
                cur.execute(
                    """
                    SELECT * FROM public.school_aee_matrizes
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (str(mid), inst),
                )
            elif condicao:
                cur.execute(
                    """
                    SELECT * FROM public.school_aee_matrizes
                    WHERE instituicao_id = %s
                      AND condicao_categoria = %s
                      AND status = 'aguardando_assinaturas'
                    ORDER BY versao DESC
                    LIMIT 1
                    """,
                    (inst, condicao),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM public.school_aee_matrizes
                    WHERE instituicao_id = %s
                      AND status = 'aguardando_assinaturas'
                    ORDER BY versao DESC
                    LIMIT 1
                    """,
                    (inst,),
                )
            row = cur.fetchone()
            if not row:
                return jsonify(
                    {"error": "Nenhuma matriz AEE aguardando assinaturas"}
                ), 404
            if _status_str(row) != "aguardando_assinaturas":
                return jsonify(
                    {"error": "Matriz não está aguardando assinaturas"}
                ), 409

            col = (
                "assinado_coordenador"
                if papel == "coordenador"
                else "assinado_psicopedagogo"
            )
            ts_col = (
                "data_assinatura_coordenador"
                if papel == "coordenador"
                else "data_assinatura_psicopedagogo"
            )
            cur.execute(
                f"""
                UPDATE public.school_aee_matrizes
                SET {col} = TRUE,
                    {ts_col} = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (str(row["id"]),),
            )
            updated = cur.fetchone()

            if (
                updated["assinado_coordenador"]
                and updated["assinado_psicopedagogo"]
            ):
                cur.execute(
                    """
                    UPDATE public.school_aee_matrizes
                    SET status = 'arquivado', updated_at = CURRENT_TIMESTAMP
                    WHERE instituicao_id = %s
                      AND condicao_categoria = %s
                      AND status = 'ativo'
                      AND id <> %s
                    """,
                    (
                        inst,
                        updated["condicao_categoria"],
                        str(updated["id"]),
                    ),
                )
                cur.execute(
                    """
                    UPDATE public.school_aee_matrizes
                    SET status = 'ativo', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (str(updated["id"]),),
                )
                updated = cur.fetchone()

    return jsonify(
        {
            "message": (
                "Matriz AEE ativada — versões anteriores da condição arquivadas."
                if _status_str(updated) == "ativo"
                else f"Assinatura de {papel} registrada."
            ),
            "matriz": _serialize_aee(updated),
        }
    )


@bp.post("/api/aee/matriz/assinar/coordenador")
def assinar_aee_coordenador():
    return _assinar_aee("coordenador")


@bp.post("/api/aee/matriz/assinar/psicopedagogo")
def assinar_aee_psicopedagogo():
    return _assinar_aee("psicopedagogo")


@bp.get("/api/aee/matrizes/<path:condicao>/historico")
def historico_aee(condicao: str):
    """Todas as versões (ativas e arquivadas) da condição, versao DESC."""
    inst = _instituicao_id()
    raw = str(condicao or "").strip()
    if not condicao_valida(raw):
        return jsonify({"error": f"Condição inválida: {raw}"}), 400
    canon = get_canonico(raw)
    for nome in (c["condicao_categoria"] for c in listar_condicoes()):
        if nome.lower() == raw.lower():
            raw = nome
            break

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM public.school_aee_matrizes
                WHERE instituicao_id = %s
                  AND condicao_categoria = %s
                ORDER BY versao DESC
                """,
                (inst, raw),
            )
            rows = cur.fetchall()

    versoes = [_serialize_aee(r, canon) for r in rows]
    return jsonify(
        {
            "condicao_categoria": raw,
            "count": len(versoes),
            "versoes": versoes,
        }
    )


@bp.get("/api/aee/matriz/<matriz_id>")
def get_matriz_aee_por_id(matriz_id: str):
    mid = _parse_uuid(matriz_id)
    if not mid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM public.school_aee_matrizes
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(mid), inst),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Matriz AEE não encontrada"}), 404
    return jsonify(_serialize_aee(row))


# ---------------------------------------------------------------------------
# PEI individual
# ---------------------------------------------------------------------------


@bp.get("/api/pei/alunos")
def list_pei_alunos():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.instituicao_id = %s
                  AND p.status <> 'arquivado'
                ORDER BY p.created_at DESC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify([_serialize_pei(r) for r in rows])


@bp.get("/api/pei/alunos/<pei_id>")
def get_pei_aluno(pei_id: str):
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.id = %s AND p.instituicao_id = %s
                """,
                (str(pid), inst),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "PEI não encontrado"}), 404
    return jsonify(_serialize_pei(row))


@bp.get("/api/pei/alunos/<pei_id>/historico")
def historico_pei_aluno(pei_id: str):
    """Todas as versões do PEI daquele aluno (linha), ordenadas por versao DESC."""
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.id = %s AND p.instituicao_id = %s
                """,
                (str(pid), inst),
            )
            base = cur.fetchone()
            if not base:
                return jsonify({"error": "PEI não encontrado"}), 404
            linha = base.get("pei_linha_id") or base["id"]
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.instituicao_id = %s
                  AND p.pei_linha_id = %s
                ORDER BY p.versao DESC
                """,
                (inst, str(linha)),
            )
            rows = cur.fetchall()
    versoes = [_serialize_pei(r) for r in rows]
    return jsonify(
        {
            "pei_linha_id": str(linha),
            "aluno_ref_id": str(pid),
            "nome_completo": base.get("nome_completo") or "",
            "count": len(versoes),
            "versoes": versoes,
        }
    )


@bp.post("/api/pei/alunos")
def criar_pei_aluno():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome_completo") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome completo do aluno"}), 400
    condicao = str(body.get("condicao_categoria") or body.get("condicao") or "").strip()
    if not condicao_valida(condicao):
        return jsonify({"error": "Informe uma condição AEE válida"}), 400
    for nome_c in (c["condicao_categoria"] for c in listar_condicoes()):
        if nome_c.lower() == condicao.lower():
            condicao = nome_c
            break

    linha_ref = _parse_uuid(body.get("pei_linha_id") or body.get("nova_versao_de"))
    matricula = str(body.get("matricula") or "").strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ativa = _aee_ativa(cur, inst, condicao)
            if not ativa:
                return jsonify(
                    {
                        "error": (
                            f"Não há matriz AEE ativa para “{condicao}”. "
                            "Envie e assine a diretriz da condição primeiro."
                        )
                    }
                ), 409

            pei_linha_id = None
            next_v = 1
            if linha_ref:
                cur.execute(
                    """
                    SELECT * FROM public.school_pei_alunos
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (str(linha_ref), inst),
                )
                origem = cur.fetchone()
                if origem:
                    pei_linha_id = origem.get("pei_linha_id") or origem["id"]
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(versao), 0) AS max_v
                        FROM public.school_pei_alunos
                        WHERE pei_linha_id = %s
                        """,
                        (str(pei_linha_id),),
                    )
                    next_v = int(cur.fetchone()["max_v"]) + 1
                    # Arquiva versões ativas anteriores da linha
                    cur.execute(
                        """
                        UPDATE public.school_pei_alunos
                        SET status = 'arquivado', updated_at = CURRENT_TIMESTAMP
                        WHERE pei_linha_id = %s AND status = 'ativo'
                        """,
                        (str(pei_linha_id),),
                    )
                    if not matricula:
                        matricula = origem.get("matricula") or ""
                    if not nome:
                        nome = origem.get("nome_completo") or nome

            if not pei_linha_id:
                pei_linha_id = uuid.uuid4()

            cur.execute(
                """
                INSERT INTO public.school_pei_alunos (
                    instituicao_id, aee_matriz_id, pei_linha_id, versao, status,
                    nome_completo, matricula, nome_responsavel,
                    perfil_atual_habilidades, barreiras_identificadas,
                    metas_desenvolvimento, recursos_assistivos,
                    criterios_avaliacao_flexibilizados,
                    experiencias_adaptadas_individuais
                )
                VALUES (%s, %s, %s, %s, 'rascunho', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    inst,
                    str(ativa["id"]),
                    str(pei_linha_id),
                    next_v,
                    nome,
                    matricula,
                    str(body.get("nome_responsavel") or "").strip(),
                    str(body.get("perfil_atual_habilidades") or "").strip(),
                    str(body.get("barreiras_identificadas") or "").strip(),
                    str(body.get("metas_desenvolvimento") or "").strip(),
                    str(body.get("recursos_assistivos") or "").strip(),
                    str(body.get("criterios_avaliacao_flexibilizados") or "").strip(),
                    str(body.get("experiencias_adaptadas_individuais") or "").strip(),
                ),
            )
            row = cur.fetchone()
            row["aee_versao"] = ativa["versao"]
            row["condicao_categoria"] = ativa["condicao_categoria"]
    return jsonify(_serialize_pei(row)), 201


@bp.post("/api/pei/alunos/<pei_id>/nova-versao")
def nova_versao_pei(pei_id: str):
    """Cria rascunho v+1 copiando campos da versão vigente (arquiva a ativa)."""
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.id = %s AND p.instituicao_id = %s
                """,
                (str(pid), inst),
            )
            origem = cur.fetchone()
            if not origem:
                return jsonify({"error": "PEI não encontrado"}), 404
            linha = origem.get("pei_linha_id") or origem["id"]
            cur.execute(
                """
                SELECT COALESCE(MAX(versao), 0) AS max_v
                FROM public.school_pei_alunos WHERE pei_linha_id = %s
                """,
                (str(linha),),
            )
            next_v = int(cur.fetchone()["max_v"]) + 1
            cur.execute(
                """
                UPDATE public.school_pei_alunos
                SET status = 'arquivado', updated_at = CURRENT_TIMESTAMP
                WHERE pei_linha_id = %s AND status IN ('ativo', 'rascunho')
                  AND id <> %s
                """,
                (str(linha), str(pid)),
            )
            if str(origem.get("status") or "") == "ativo":
                cur.execute(
                    """
                    UPDATE public.school_pei_alunos
                    SET status = 'arquivado', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (str(pid),),
                )
            ativa = _aee_ativa(cur, inst, origem.get("condicao_categoria"))
            aee_id = str(ativa["id"]) if ativa else str(origem["aee_matriz_id"])
            cur.execute(
                """
                INSERT INTO public.school_pei_alunos (
                    instituicao_id, aee_matriz_id, pei_linha_id, versao, status,
                    nome_completo, matricula, nome_responsavel,
                    perfil_atual_habilidades, barreiras_identificadas,
                    metas_desenvolvimento, recursos_assistivos,
                    criterios_avaliacao_flexibilizados,
                    experiencias_adaptadas_individuais
                )
                VALUES (%s, %s, %s, %s, 'rascunho', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    inst,
                    aee_id,
                    str(linha),
                    next_v,
                    origem["nome_completo"],
                    origem.get("matricula") or "",
                    origem.get("nome_responsavel") or "",
                    origem.get("perfil_atual_habilidades") or "",
                    origem.get("barreiras_identificadas") or "",
                    origem.get("metas_desenvolvimento") or "",
                    origem.get("recursos_assistivos") or "",
                    origem.get("criterios_avaliacao_flexibilizados") or "",
                    origem.get("experiencias_adaptadas_individuais") or "",
                ),
            )
            row = cur.fetchone()
            row["aee_versao"] = (ativa or {}).get("versao") or origem.get("aee_versao")
            row["condicao_categoria"] = origem.get("condicao_categoria")
    return jsonify(_serialize_pei(row)), 201


@bp.put("/api/pei/alunos/<pei_id>")
def atualizar_pei_aluno(pei_id: str):
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    fields = [
        "nome_completo",
        "matricula",
        "nome_responsavel",
        "perfil_atual_habilidades",
        "barreiras_identificadas",
        "metas_desenvolvimento",
        "recursos_assistivos",
        "criterios_avaliacao_flexibilizados",
        "experiencias_adaptadas_individuais",
    ]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.id = %s AND p.instituicao_id = %s
                """,
                (str(pid), inst),
            )
            existing = cur.fetchone()
            if not existing:
                return jsonify({"error": "PEI não encontrado"}), 404

            if existing["assinado_coordenador"] and existing["assinado_psicopedagogo"]:
                return jsonify(
                    {
                        "error": "PEI já assinado — use “Nova versão” para alterar."
                    }
                ), 409

            sets = []
            vals: list[Any] = []
            for f in fields:
                if f in body:
                    sets.append(f"{f} = %s")
                    vals.append(str(body.get(f) or "").strip())
            if not sets:
                return jsonify(_serialize_pei(existing))

            sets.append("assinado_coordenador = FALSE")
            sets.append("assinado_psicopedagogo = FALSE")
            sets.append("data_assinatura = NULL")
            sets.append("data_assinatura_coordenador = NULL")
            sets.append("data_assinatura_psicopedagogo = NULL")
            sets.append("status = 'rascunho'")
            sets.append("updated_at = CURRENT_TIMESTAMP")
            vals.append(str(pid))
            cur.execute(
                f"""
                UPDATE public.school_pei_alunos
                SET {", ".join(sets)}
                WHERE id = %s
                RETURNING *
                """,
                vals,
            )
            row = cur.fetchone()
            row["aee_versao"] = existing["aee_versao"]
            row["condicao_categoria"] = existing["condicao_categoria"]
    return jsonify(_serialize_pei(row))


def _assinar_pei(papel: str, pei_id: str):
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.*, m.versao AS aee_versao, m.condicao_categoria
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.id = %s AND p.instituicao_id = %s
                """,
                (str(pid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "PEI não encontrado"}), 404

            col = (
                "assinado_coordenador"
                if papel == "coordenador"
                else "assinado_psicopedagogo"
            )
            ts_col = (
                "data_assinatura_coordenador"
                if papel == "coordenador"
                else "data_assinatura_psicopedagogo"
            )
            cur.execute(
                f"""
                UPDATE public.school_pei_alunos
                SET {col} = TRUE,
                    {ts_col} = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (str(pid),),
            )
            updated = cur.fetchone()
            if (
                updated["assinado_coordenador"]
                and updated["assinado_psicopedagogo"]
            ):
                linha = updated.get("pei_linha_id") or updated["id"]
                cur.execute(
                    """
                    UPDATE public.school_pei_alunos
                    SET status = 'arquivado', updated_at = CURRENT_TIMESTAMP
                    WHERE pei_linha_id = %s
                      AND status = 'ativo'
                      AND id <> %s
                    """,
                    (str(linha), str(pid)),
                )
                cur.execute(
                    """
                    UPDATE public.school_pei_alunos
                    SET status = 'ativo',
                        data_assinatura = COALESCE(data_assinatura, CURRENT_TIMESTAMP),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (str(pid),),
                )
                updated = cur.fetchone()
            updated["aee_versao"] = row["aee_versao"]
            updated["condicao_categoria"] = row["condicao_categoria"]
    return jsonify(_serialize_pei(updated))


@bp.post("/api/pei/alunos/<pei_id>/assinar/coordenador")
def assinar_pei_coordenador(pei_id: str):
    return _assinar_pei("coordenador", pei_id)


@bp.post("/api/pei/alunos/<pei_id>/assinar/psicopedagogo")
def assinar_pei_psicopedagogo(pei_id: str):
    return _assinar_pei("psicopedagogo", pei_id)


# ---------------------------------------------------------------------------
# AEE × Metodologias (adaptações na prática — por condição)
# ---------------------------------------------------------------------------


@bp.get("/api/aee/<aee_id>/metodologias")
def list_aee_metodologias(aee_id: str):
    aid = _parse_uuid(aee_id)
    if not aid:
        return jsonify({"error": "Identificador AEE inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        _ensure_aee_met_org_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            matriz = _get_aee_matriz(cur, aid, inst)
            if not matriz:
                return jsonify({"error": "Matriz AEE não encontrada"}), 404
            campos = (matriz.get("campos_experiencia_metodologica") or "").strip()
            condicao = matriz.get("condicao_categoria") or ""

            cur.execute(
                """
                SELECT
                    c.id AS metodologia_catalogo_id,
                    c.nome,
                    c.categoria,
                    c.descricao,
                    c.passos_execucao,
                    org.passos_customizados AS versao_escola,
                    org.updated_at AS org_updated_at,
                    COALESCE(vet.ativo_dia_a_dia, TRUE) AS disponivel_dia_a_dia,
                    COALESCE(vet.ativo_desafio, TRUE) AS disponivel_desafio,
                    COALESCE(cur.sugestoes_count, 0) AS sugestoes_count
                FROM public.school_metodologias_catalogo c
                LEFT JOIN public.school_aee_metodologias_org org
                    ON org.aee_matriz_id = %s
                   AND LOWER(TRIM(org.metodologia_nome)) = LOWER(TRIM(c.nome))
                LEFT JOIN public.school_metodologias_org vet
                    ON vet.metodologia_id_canonica = c.id
                   AND vet.instituicao_id = %s
                LEFT JOIN (
                    SELECT
                        LOWER(TRIM(metodologia_nome)) AS nome_key,
                        COUNT(*)::int AS sugestoes_count
                    FROM public.school_curadoria_pei
                    WHERE instituicao_id = %s
                      AND status_analise IN ('pendente', 'incorporado')
                    GROUP BY LOWER(TRIM(metodologia_nome))
                ) cur ON cur.nome_key = LOWER(TRIM(c.nome))
                WHERE c.ativo = TRUE AND c.origem = 'padrao'
                ORDER BY c.categoria, c.nome
                """,
                (str(aid), inst, inst),
            )
            rows = cur.fetchall()

    out = []
    for r in rows:
        texto = _passos_to_text(r.get("passos_execucao"))
        versao = (r.get("versao_escola") or "").strip()
        is_custom = bool(versao)
        updated = r.get("org_updated_at")
        count = int(r.get("sugestoes_count") or 0)
        out.append(
            {
                "metodologia_id": str(r["metodologia_catalogo_id"]),
                "nome": r["nome"],
                "familia": r.get("categoria"),
                "descricao": r.get("descricao"),
                "texto_canonico": texto,
                "campos_experiencia_aee": campos,
                "condicao_categoria": condicao,
                "aee_matriz_id": str(aid),
                "versao_escola": versao,
                "is_customizado": is_custom,
                "updated_at": updated.isoformat() if updated else None,
                "disponivel_dia_a_dia": bool(r.get("disponivel_dia_a_dia", True)),
                "disponivel_desafio": bool(r.get("disponivel_desafio", True)),
                "uso_estrelas": 0 if count <= 0 else min(3, count),
                "sugestoes_count": count,
            }
        )
    return jsonify(
        {
            "aee_matriz_id": str(aid),
            "condicao_categoria": condicao,
            "campos_experiencia_aee": campos,
            "items": out,
        }
    )


@bp.put("/api/aee/<aee_id>/metodologias/<path:metodologia_nome>")
def salvar_aee_metodologia(aee_id: str, metodologia_nome: str):
    aid = _parse_uuid(aee_id)
    if not aid:
        return jsonify({"error": "Identificador AEE inválido"}), 400
    nome = str(metodologia_nome or "").strip()
    if not nome:
        return jsonify({"error": "Nome da metodologia obrigatório"}), 400
    body = request.get_json(silent=True) or {}
    texto = str(
        body.get("passos_customizados")
        or body.get("versao_escola")
        or body.get("versao_pei")
        or ""
    ).strip()
    inst = _instituicao_id()

    with get_conn() as conn:
        _ensure_aee_met_org_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            matriz = _get_aee_matriz(cur, aid, inst)
            if not matriz:
                return jsonify({"error": "Matriz AEE não encontrada"}), 404

            cur.execute(
                """
                SELECT id, nome FROM public.school_metodologias_catalogo
                WHERE LOWER(TRIM(nome)) = LOWER(TRIM(%s))
                  AND ativo = TRUE
                LIMIT 1
                """,
                (nome,),
            )
            cat = cur.fetchone()
            if not cat:
                return jsonify({"error": "Metodologia não encontrada no catálogo"}), 404
            nome_canon = cat["nome"]

            cur.execute(
                """
                INSERT INTO public.school_aee_metodologias_org (
                    aee_matriz_id, metodologia_nome, passos_customizados, updated_at
                )
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (aee_matriz_id, metodologia_nome)
                DO UPDATE SET
                    passos_customizados = EXCLUDED.passos_customizados,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (str(aid), nome_canon, texto),
            )
            row = cur.fetchone()

    return jsonify(
        {
            "aee_matriz_id": str(aid),
            "metodologia_id": str(cat["id"]),
            "metodologia_nome": nome_canon,
            "versao_escola": row.get("passos_customizados") or "",
            "passos_customizados": row.get("passos_customizados") or "",
            "is_customizado": bool((row.get("passos_customizados") or "").strip()),
            "updated_at": _iso(row.get("updated_at")),
            "condicao_categoria": matriz.get("condicao_categoria") or "",
        }
    )


@bp.post("/api/aee/<aee_id>/metodologia/<path:metodologia_nome>/adaptar-ia")
def adaptar_aee_metodologia_ia(aee_id: str, metodologia_nome: str):
    aid = _parse_uuid(aee_id)
    if not aid:
        return jsonify({"error": "Identificador AEE inválido"}), 400
    nome = str(metodologia_nome or "").strip()
    if not nome:
        return jsonify({"error": "Nome da metodologia obrigatório"}), 400
    body = request.get_json(silent=True) or {}
    inst = _instituicao_id()

    sugestao = str(body.get("sugestao") or body.get("sugestao_professor") or "").strip()
    sugestoes_raw = body.get("sugestoes") or body.get("sugestoes_aceitas") or []
    if isinstance(sugestoes_raw, str):
        sugestoes_lista = [sugestoes_raw.strip()] if sugestoes_raw.strip() else []
    elif isinstance(sugestoes_raw, list):
        sugestoes_lista = [str(s).strip() for s in sugestoes_raw if str(s or "").strip()]
    else:
        sugestoes_lista = []
    if sugestao and sugestao not in sugestoes_lista:
        sugestoes_lista.append(sugestao)

    with get_conn() as conn:
        _ensure_aee_met_org_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            matriz = _get_aee_matriz(cur, aid, inst)
            if not matriz:
                return jsonify({"error": "Matriz AEE não encontrada"}), 404
            cur.execute(
                """
                SELECT id, nome, passos_execucao
                FROM public.school_metodologias_catalogo
                WHERE LOWER(TRIM(nome)) = LOWER(TRIM(%s))
                  AND ativo = TRUE
                LIMIT 1
                """,
                (nome,),
            )
            cat = cur.fetchone()
            if not cat:
                return jsonify({"error": "Metodologia não encontrada"}), 404

    canonico = str(body.get("texto_canonico") or "").strip() or _passos_to_text(
        cat.get("passos_execucao")
    )
    campos = str(
        body.get("campos_experiencia_aee")
        or body.get("texto_campos_experiencia_aee")
        or matriz.get("campos_experiencia_metodologica")
        or ""
    ).strip()
    condicao = matriz.get("condicao_categoria") or ""

    try:
        from school_llm import sintetizar_adaptacao_aee_metodologia

        versao = sintetizar_adaptacao_aee_metodologia(
            texto_canonico_metodologia=canonico,
            texto_campos_experiencia_aee=campos,
            sugestoes_professores=sugestoes_lista,
            condicao_categoria=condicao,
        )
    except Exception as exc:
        return jsonify({"error": f"Falha na IA: {exc}"}), 502

    return jsonify(
        {
            "success": True,
            "aee_matriz_id": str(aid),
            "metodologia_id": str(cat["id"]),
            "metodologia_nome": cat["nome"],
            "condicao_categoria": condicao,
            "versao_escola": versao,
            "texto_canonico": canonico,
            "campos_experiencia_aee": campos,
            "sugestoes_aceitas": sugestoes_lista,
        }
    )


# ---------------------------------------------------------------------------
# Adaptações metodológicas (prática) — legado /api/pei/*
# ---------------------------------------------------------------------------


@bp.get("/api/pei/metodologias")
def list_pei_metodologias():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    c.id AS metodologia_catalogo_id,
                    c.nome,
                    c.categoria,
                    c.descricao,
                    c.passos_execucao,
                    ad.passos_customizados AS versao_pei,
                    ad.gerado_por_ia,
                    ad.updated_at AS adaptacao_updated_at,
                    COALESCE(org.ativo_dia_a_dia, TRUE) AS disponivel_dia_a_dia,
                    COALESCE(org.ativo_desafio, TRUE) AS disponivel_desafio,
                    COALESCE(cur.sugestoes_count, 0) AS sugestoes_count
                FROM public.school_metodologias_catalogo c
                LEFT JOIN public.school_pei_metodologia_adaptacao ad
                    ON ad.instituicao_id = %s
                   AND ad.pei_aluno_id IS NULL
                   AND LOWER(TRIM(ad.metodologia_nome)) = LOWER(TRIM(c.nome))
                LEFT JOIN public.school_metodologias_org org
                    ON org.metodologia_id_canonica = c.id
                   AND org.instituicao_id = %s
                LEFT JOIN (
                    SELECT
                        LOWER(TRIM(metodologia_nome)) AS nome_key,
                        COUNT(*)::int AS sugestoes_count
                    FROM public.school_curadoria_pei
                    WHERE instituicao_id = %s
                      AND status_analise IN ('pendente', 'incorporado')
                    GROUP BY LOWER(TRIM(metodologia_nome))
                ) cur ON cur.nome_key = LOWER(TRIM(c.nome))
                WHERE c.ativo = TRUE AND c.origem = 'padrao'
                ORDER BY c.categoria, c.nome
                """,
                (inst, inst, inst),
            )
            rows = cur.fetchall()

    out = []
    for r in rows:
        texto = _passos_to_text(r.get("passos_execucao"))
        count = int(r.get("sugestoes_count") or 0)
        estrelas = 0 if count <= 0 else min(3, count)
        versao = (r.get("versao_pei") or "").strip()
        is_custom = bool(versao)
        updated = r.get("adaptacao_updated_at")
        out.append(
            {
                "metodologia_id": str(r["metodologia_catalogo_id"]),
                "nome": r["nome"],
                "familia": r.get("categoria"),
                "descricao": r.get("descricao"),
                "texto_canonico": texto,
                "versao_pei": versao,
                "is_customizado": is_custom,
                "updated_at": updated.isoformat() if updated else None,
                "gerado_por_ia": bool(r.get("gerado_por_ia")),
                "disponivel_dia_a_dia": bool(r.get("disponivel_dia_a_dia", True)),
                "disponivel_desafio": bool(r.get("disponivel_desafio", True)),
                "uso_estrelas": estrelas,
                "sugestoes_count": count,
            }
        )
    return jsonify(out)


@bp.get("/api/pei/curadoria")
def list_curadoria_pei():
    inst = _instituicao_id()
    met = str(request.args.get("metodologia_nome") or "").strip()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if met:
                cur.execute(
                    """
                    SELECT * FROM public.school_curadoria_pei
                    WHERE instituicao_id = %s
                      AND status_analise = 'pendente'
                      AND LOWER(TRIM(metodologia_nome)) = LOWER(TRIM(%s))
                    ORDER BY created_at DESC
                    """,
                    (inst, met),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM public.school_curadoria_pei
                    WHERE instituicao_id = %s
                      AND status_analise = 'pendente'
                    ORDER BY created_at DESC
                    """,
                    (inst,),
                )
            rows = cur.fetchall()

    items = []
    for row in rows:
        sug = row.get("sugestao_professor_json") or {}
        if not isinstance(sug, dict):
            sug = {}
        texto = str(
            sug.get("teacher_adaptation_text")
            or sug.get("pei_adaptation_text")
            or sug.get("texto_sugestao")
            or sug.get("texto")
            or ""
        ).strip()
        items.append(
            {
                "id": str(row["id"]),
                "metodologia_nome": row.get("metodologia_nome") or "",
                "professor_nome": str(
                    sug.get("professor_nome") or sug.get("teacher_name") or ""
                ).strip(),
                "aula_contexto": str(
                    sug.get("aula_contexto")
                    or sug.get("contexto_aula")
                    or sug.get("disciplina")
                    or ""
                ).strip(),
                "teacher_adaptation_text": texto,
                "created_at": row["created_at"].isoformat()
                if row.get("created_at")
                else None,
            }
        )
    return jsonify({"count": len(items), "items": items})


@bp.post("/api/pei/curadoria/<item_id>/incorporar")
def incorporar_curadoria_pei_pratica(item_id: str):
    """Marca sugestão PEI como incorporada (síntese via IA no front — espelho Metodologias)."""
    cid = _parse_uuid(item_id)
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, status_analise, sugestao_professor_json, metodologia_nome
                FROM public.school_curadoria_pei
                WHERE id = %s AND instituicao_id = %s
                LIMIT 1
                """,
                (str(cid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sugestão não encontrada"}), 404
            if row["status_analise"] != "pendente":
                return jsonify(
                    {
                        "error": "Sugestão já analisada",
                        "status_analise": row["status_analise"],
                    }
                ), 409
            sug = row.get("sugestao_professor_json") or {}
            if not isinstance(sug, dict):
                sug = {}
            texto = str(
                sug.get("teacher_adaptation_text")
                or sug.get("pei_adaptation_text")
                or sug.get("texto_sugestao")
                or sug.get("texto")
                or ""
            ).strip()
            if not texto:
                return jsonify({"error": "Sugestão sem texto do professor"}), 400
            cur.execute(
                """
                UPDATE public.school_curadoria_pei
                SET status_analise = 'incorporado',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, status_analise
                """,
                (str(cid),),
            )
            updated = cur.fetchone()
    return jsonify(
        {
            "item": {
                "id": str(updated["id"]),
                "status_analise": updated["status_analise"],
            },
            "message": "Sugestão marcada. Use “Gerar adaptação PEI integrada” para a IA compor o texto.",
        }
    )


@bp.post("/api/pei/metodologia/<metodologia_id>/adaptar-ia")
def adaptar_pei_metodologia_ia(metodologia_id: str):
    mid = _parse_uuid(metodologia_id)
    if not mid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}

    sugestao = str(body.get("sugestao") or body.get("sugestao_professor") or "").strip()
    sugestoes_raw = body.get("sugestoes") or body.get("sugestoes_aceitas") or []
    if isinstance(sugestoes_raw, str):
        sugestoes_lista = [sugestoes_raw.strip()] if sugestoes_raw.strip() else []
    elif isinstance(sugestoes_raw, list):
        sugestoes_lista = [str(s).strip() for s in sugestoes_raw if str(s or "").strip()]
    else:
        sugestoes_lista = []
    if sugestao and sugestao not in sugestoes_lista:
        sugestoes_lista.append(sugestao)
    if not sugestoes_lista:
        return jsonify({"error": "Informe ao menos uma sugestão do professor"}), 400

    adaptacao_pei = str(
        body.get("adaptacao_pei_escola")
        or body.get("observacoes_coordenacao")
        or body.get("adaptacao_pei")
        or ""
    ).strip()

    pei_id = _parse_uuid(body.get("pei_aluno_id") or body.get("pei_id"))
    condicao = str(body.get("condicao_categoria") or body.get("condicao") or "").strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome, passos_execucao
                FROM public.school_metodologias_catalogo
                WHERE id = %s AND ativo = TRUE
                """,
                (str(mid),),
            )
            cat = cur.fetchone()
            if not cat:
                return jsonify({"error": "Metodologia não encontrada"}), 404

            pei_row = None
            aee_row = None
            if pei_id:
                cur.execute(
                    """
                    SELECT p.*, m.texto_escola, m.campos_experiencia_metodologica,
                           m.condicao_categoria
                    FROM public.school_pei_alunos p
                    JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                    WHERE p.id = %s AND p.instituicao_id = %s
                    """,
                    (str(pei_id), inst),
                )
                pei_row = cur.fetchone()
                if pei_row:
                    aee_row = {
                        "texto_escola": pei_row.get("texto_escola"),
                        "campos_experiencia_metodologica": pei_row.get(
                            "campos_experiencia_metodologica"
                        ),
                        "condicao_categoria": pei_row.get("condicao_categoria"),
                    }
                    condicao = pei_row.get("condicao_categoria") or condicao

            if not aee_row:
                aee_row = _aee_ativa(cur, inst, condicao if condicao else None)

    canonico = str(body.get("texto_canonico") or "").strip() or _passos_to_text(
        cat.get("passos_execucao")
    )
    aee_texto = (aee_row or {}).get("texto_escola") or ""
    aee_campos = (aee_row or {}).get("campos_experiencia_metodologica") or ""
    pei_exp = ""
    if pei_row:
        pei_exp = pei_row.get("experiencias_adaptadas_individuais") or ""
    elif body.get("experiencias_adaptadas_individuais"):
        pei_exp = str(body.get("experiencias_adaptadas_individuais") or "")

    try:
        from school_llm import adaptar_pei_metodologia_com_ia

        versao = adaptar_pei_metodologia_com_ia(
            metodologia_canonica=canonico,
            aee_texto_escola=aee_texto,
            aee_campos_experiencia=aee_campos,
            pei_experiencias_individuais=pei_exp,
            sugestoes_aceitas=sugestoes_lista,
            adaptacao_pei_escola=adaptacao_pei,
            condicao_categoria=(aee_row or {}).get("condicao_categoria") or condicao,
        )
    except Exception as exc:
        return jsonify({"error": f"Falha na IA: {exc}"}), 502

    return jsonify(
        {
            "success": True,
            "metodologia_id": str(mid),
            "metodologia_nome": cat["nome"],
            "versao_pei": versao,
            "texto_canonico": canonico,
            "adaptacao_pei_escola": adaptacao_pei,
            "sugestoes_aceitas": sugestoes_lista,
            "contexto": {
                "condicao_categoria": (aee_row or {}).get("condicao_categoria")
                or condicao
                or None,
                "pei_aluno_id": str(pei_id) if pei_id else None,
                "usou_aee": bool(aee_texto or aee_campos),
                "usou_pei": bool(pei_exp),
            },
        }
    )


@bp.put("/api/pei/metodologia/<metodologia_id>/versao")
def salvar_versao_pei_metodologia(metodologia_id: str):
    mid = _parse_uuid(metodologia_id)
    if not mid:
        return jsonify({"error": "Identificador inválido"}), 400
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    versao = str(body.get("versao_pei") or body.get("passos_customizados") or "").strip()
    gerado = bool(body.get("gerado_por_ia", False))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome FROM public.school_metodologias_catalogo
                WHERE id = %s AND ativo = TRUE
                """,
                (str(mid),),
            )
            cat = cur.fetchone()
            if not cat:
                return jsonify({"error": "Metodologia não encontrada"}), 404

            cur.execute(
                """
                SELECT id FROM public.school_pei_metodologia_adaptacao
                WHERE instituicao_id = %s
                  AND pei_aluno_id IS NULL
                  AND LOWER(TRIM(metodologia_nome)) = LOWER(TRIM(%s))
                """,
                (inst, cat["nome"]),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE public.school_pei_metodologia_adaptacao
                    SET passos_customizados = %s,
                        metodologia_catalogo_id = %s,
                        gerado_por_ia = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (versao, str(mid), gerado, str(existing["id"])),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO public.school_pei_metodologia_adaptacao (
                        instituicao_id, pei_aluno_id, metodologia_nome,
                        metodologia_catalogo_id, passos_customizados, gerado_por_ia
                    )
                    VALUES (%s, NULL, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (inst, cat["nome"], str(mid), versao, gerado),
                )
            row = cur.fetchone()

    updated = row.get("updated_at")
    return jsonify(
        {
            "metodologia_id": str(mid),
            "metodologia_nome": cat["nome"],
            "versao_pei": row.get("passos_customizados") or "",
            "gerado_por_ia": bool(row.get("gerado_por_ia")),
            "is_customizado": bool((row.get("passos_customizados") or "").strip()),
            "updated_at": updated.isoformat() if updated else None,
        }
    )


# ---------------------------------------------------------------------------
# Compat: aliases antigos /api/pei/matriz* → redirecionam mentalmente via 410
# Mantidos silenciosos não — removidos. FE novo usa /api/aee/*
# ---------------------------------------------------------------------------
