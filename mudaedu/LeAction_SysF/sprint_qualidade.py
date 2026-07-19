"""Governança de qualidade da Sprint (Vetor 1).

Progresso real = média das notas_qualidade das métricas já avaliadas.
Nota por métrica (regra interna): só texto 40, só documento 40, ambos 100.
DoD = itens binários (concluido); 100% necessário para concluir a sprint.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import psycopg2.extras

from rbac.constants import ROLE_CONSULTOR, ROLE_SYSADMIN
from rbac.context import RbacContext, resolve_rbac_context

# Limiar mínimo da média de qualidade para o Cliente encerrar a Sprint
LIMIAR_QUALIDADE_FECHAMENTO = 80

# Regra interna de nota por presença de evidência (sem LLM):
# só texto → 40; só documento → 40; ambos → 100.
NOTA_EVIDENCIA_TEXTUAL = 40
NOTA_EVIDENCIA_DOCUMENTAL = 40
NOTA_EVIDENCIA_AMBAS = 100

MSG_QUALIDADE_ABAIXO = (
    "A qualidade média das entregas avaliadas pela moderação está abaixo de 80%. "
    "Melhore as entregas pendentes para concluir a Sprint."
)


def calcular_nota_por_evidencia(
    documento_url: str | None,
    depoimento: str | None,
) -> int:
    """Nota automática por tipo de evidência apresentada (regra interna)."""
    tem_doc = bool((documento_url or "").strip())
    tem_dep = bool((depoimento or "").strip())
    if tem_doc and tem_dep:
        return NOTA_EVIDENCIA_AMBAS
    if tem_doc:
        return NOTA_EVIDENCIA_DOCUMENTAL
    if tem_dep:
        return NOTA_EVIDENCIA_TEXTUAL
    raise ValueError("Informe ao menos documento_url ou depoimento.")


def e_moderador(ctx: RbacContext | None = None) -> bool:
    """Moderador = roles consultor ou sysadmin (checks and balances)."""
    ctx = ctx or resolve_rbac_context()
    return ctx.has_role(ROLE_SYSADMIN, ROLE_CONSULTOR)


def e_cliente_execucao(ctx: RbacContext | None = None) -> bool:
    """Cliente executa/encerra; não pontua. Qualquer não-moderador (ex.: led)."""
    return not e_moderador(ctx)


def pode_avaliar_metricas(ctx: RbacContext | None = None) -> bool:
    """Consultor/sysadmin — mas a UI/API só liberam scoragem se houver pedido do Cliente."""
    return e_moderador(ctx)


def pode_revisar_nota_consultor(conn, id_sprn: int, ctx: RbacContext | None = None) -> bool:
    """Exceção: consultor só revisa nota do Modulador se o Cliente solicitou."""
    if not e_moderador(ctx):
        return False
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COALESCE(revisao_consultor_solicitada, FALSE)
            FROM public.ctdi_sprn
            WHERE id_sprn = %s
            """,
            (int(id_sprn),),
        )
        row = cur.fetchone()
        return bool(row and row[0])
    finally:
        cur.close()


def solicitar_revisao_consultor(conn, id_sprn: int, motivo: str | None = None) -> dict:
    motivo_limpo = (motivo or "").strip() or None
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE public.ctdi_sprn
            SET revisao_consultor_solicitada = TRUE,
                revisao_consultor_solicitada_em = NOW(),
                revisao_consultor_motivo = %s
            WHERE id_sprn = %s
            RETURNING id_sprn, revisao_consultor_solicitada, revisao_consultor_solicitada_em,
                      revisao_consultor_motivo
            """,
            (motivo_limpo, int(id_sprn)),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError("Sprint não encontrada.")
        conn.commit()
        return {
            "id_sprn": row["id_sprn"],
            "revisao_consultor_solicitada": True,
            "revisao_consultor_solicitada_em": (
                row["revisao_consultor_solicitada_em"].isoformat()
                if row.get("revisao_consultor_solicitada_em")
                else None
            ),
            "revisao_consultor_motivo": row.get("revisao_consultor_motivo"),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def finalizar_revisao_consultor(conn, id_sprn: int) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE public.ctdi_sprn
            SET revisao_consultor_solicitada = FALSE
            WHERE id_sprn = %s
            RETURNING id_sprn, revisao_consultor_solicitada
            """,
            (int(id_sprn),),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError("Sprint não encontrada.")
        conn.commit()
        return {
            "id_sprn": row["id_sprn"],
            "revisao_consultor_solicitada": False,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def pode_fechar_sprint(ctx: RbacContext | None = None) -> bool:
    return e_cliente_execucao(ctx)


def _chave_texto(texto: str) -> str:
    norm = re.sub(r"\s+", " ", (texto or "").strip().lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def parse_metricas_derv(derv_metr: Any) -> list[str]:
    if not derv_metr:
        return []
    if isinstance(derv_metr, list):
        return [str(m).strip() for m in derv_metr if str(m).strip()]
    raw = str(derv_metr)
    return [p.strip() for p in re.split(r"[;,\n]", raw) if p.strip()]


def parse_dod_criteria(criteria_dod: Any) -> list[dict[str, str]]:
    """Retorna lista de {texto, grupo} a partir de leaf_derv.criteria_dod."""
    if not criteria_dod:
        return []
    try:
        dod = criteria_dod if isinstance(criteria_dod, (dict, list)) else json.loads(criteria_dod)
    except Exception:
        texto = str(criteria_dod).strip()
        return [{"texto": texto, "grupo": "required"}] if texto else []

    itens: list[dict[str, str]] = []
    if isinstance(dod, dict):
        for item in dod.get("required") or []:
            t = str(item).strip()
            if t:
                itens.append({"texto": t, "grupo": "required"})
        for item in dod.get("context_education") or []:
            t = str(item).strip()
            if t:
                itens.append({"texto": t, "grupo": "context_education"})
    elif isinstance(dod, list):
        for item in dod:
            t = str(item).strip()
            if t:
                itens.append({"texto": t, "grupo": "required"})
    return itens


def pode_avaliar_metricas(ctx: RbacContext | None = None) -> bool:
    ctx = ctx or resolve_rbac_context()
    return ctx.has_role(ROLE_SYSADMIN, ROLE_CONSULTOR) or bool(
        (ctx.position or "").upper() in ("MODERADOR", "CONSULTOR", "ADMIN", "GESTOR")
    )


def status_entrega(row: dict) -> str:
    nota = row.get("nota_qualidade")
    if nota is not None:
        return "avaliado"
    doc = (row.get("documento_url") or "").strip()
    dep = (row.get("depoimento") or "").strip()
    if doc or dep:
        return "aguardando_avaliacao"
    return "pendente_envio"


def _serialize_entrega(row: dict) -> dict:
    status = status_entrega(row)
    nota = row.get("nota_qualidade")
    nota_f = float(nota) if nota is not None else None
    return {
        "id": row.get("id"),
        "id_metrica": row.get("id_metrica") or row.get("id"),
        "id_sprn": row.get("id_sprn"),
        "metrica_chave": row.get("metrica_chave"),
        "metrica_rotulo": row.get("metrica_rotulo"),
        "documento_url": row.get("documento_url"),
        "depoimento": row.get("depoimento"),
        "nota_qualidade": nota_f,
        "avaliado_em": row.get("avaliado_em").isoformat() if row.get("avaliado_em") else None,
        "id_moderador": row.get("id_moderador"),
        "status": status,
        "status_label": {
            "pendente_envio": "Pendente de Envio",
            "aguardando_avaliacao": "Aguardando Avaliação",
            "avaliado": (
                f"Nota da Moderação: {int(round(nota_f))}%"
                if nota_f is not None
                else "Avaliado"
            ),
        }.get(status, status),
    }


def sync_entregas_metricas(conn, id_sprn: int, derv_metr: Any) -> list[dict]:
    """Garante uma linha por métrica do entregável e devolve o estado atual."""
    metricas = parse_metricas_derv(derv_metr)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for rotulo in metricas:
            chave = _chave_texto(rotulo)
            cur.execute(
                """
                INSERT INTO public.dx_entregas_metricas (id_sprn, metrica_chave, metrica_rotulo)
                VALUES (%s, %s, %s)
                ON CONFLICT (id_sprn, metrica_chave) DO UPDATE
                    SET metrica_rotulo = EXCLUDED.metrica_rotulo
                """,
                (id_sprn, chave, rotulo),
            )
        cur.execute(
            """
            SELECT *
            FROM public.dx_entregas_metricas
            WHERE id_sprn = %s
            ORDER BY id ASC
            """,
            (id_sprn,),
        )
        rows = cur.fetchall() or []
        conn.commit()
        return [_serialize_entrega(dict(r)) for r in rows]
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def sync_dod_itens(conn, id_sprn: int, criteria_dod: Any) -> list[dict]:
    """Garante itens DoD a partir do catálogo leaf_derv; preserva concluido já marcado."""
    itens = parse_dod_criteria(criteria_dod)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for item in itens:
            chave = _chave_texto(item["texto"])
            cur.execute(
                """
                INSERT INTO public.dx_dod_itens
                    (id_sprn, criterio_chave, criterio_texto, grupo, concluido)
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (id_sprn, criterio_chave) DO UPDATE
                    SET criterio_texto = EXCLUDED.criterio_texto,
                        grupo = EXCLUDED.grupo,
                        atualizado_em = NOW()
                """,
                (id_sprn, chave, item["texto"], item["grupo"]),
            )
        cur.execute(
            """
            SELECT id, id_sprn, criterio_chave, criterio_texto, grupo, concluido, atualizado_em
            FROM public.dx_dod_itens
            WHERE id_sprn = %s
            ORDER BY
                CASE grupo
                    WHEN 'required' THEN 0
                    WHEN 'context_education' THEN 1
                    ELSE 2
                END,
                id ASC
            """,
            (id_sprn,),
        )
        rows = cur.fetchall() or []
        conn.commit()
        out = []
        for r in rows:
            d = dict(r)
            out.append(
                {
                    "id": d["id"],
                    "id_sprn": d["id_sprn"],
                    "criterio_chave": d["criterio_chave"],
                    "criterio_texto": d["criterio_texto"],
                    "grupo": d["grupo"],
                    "concluido": bool(d["concluido"]),
                    "atualizado_em": d["atualizado_em"].isoformat() if d.get("atualizado_em") else None,
                }
            )
        return out
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def recalcular_progresso_sprint(conn, id_sprn: int) -> float:
    """Média das notas de TODAS as métricas da sprint (sem nota = 0); grava em realv_sprn."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT AVG(COALESCE(nota_qualidade, 0))::float
            FROM public.dx_entregas_metricas
            WHERE id_sprn = %s
            """,
            (id_sprn,),
        )
        row = cur.fetchone()
        media = float(row[0]) if row and row[0] is not None else 0.0
        media_int = int(round(media))
        cur.execute(
            """
            UPDATE public.ctdi_sprn
            SET realv_sprn = %s
            WHERE id_sprn = %s
            """,
            (str(media_int), id_sprn),
        )
        conn.commit()
        return float(media_int)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def aplicar_nota_em_metrica(conn, id_metrica: int, nota: float) -> dict:
    """Aplica nota do Modulador a UMA métrica e recalcula o progresso da sprint."""
    try:
        nota_f = float(nota)
    except (TypeError, ValueError) as exc:
        raise ValueError("nota inválida.") from exc
    nota_f = max(0.0, min(100.0, nota_f))

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE public.dx_entregas_metricas
            SET nota_qualidade = %s,
                avaliado_em = NOW(),
                id_moderador = NULL,
                atualizado_em = NOW()
            WHERE id = %s OR id_metrica = %s
            RETURNING *
            """,
            (nota_f, int(id_metrica), int(id_metrica)),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError("Métrica/entrega não encontrada.")
        conn.commit()
        id_sprn = int(row["id_sprn"])
        progresso = recalcular_progresso_sprint(conn, id_sprn)
        return {
            "entrega": _serialize_entrega(dict(row)),
            "progresso_qualidade": progresso,
            "id_sprn": id_sprn,
            "nota_qualidade": float(nota_f),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def comprovar_metrica(
    conn,
    *,
    id_metrica: int,
    documento_url: str | None,
    depoimento: str | None,
) -> dict:
    doc = (documento_url or "").strip() or None
    dep = (depoimento or "").strip() or None
    if not doc and not dep:
        raise ValueError("Informe ao menos documento_url ou depoimento.")

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE public.dx_entregas_metricas
            SET documento_url = COALESCE(%s, documento_url),
                depoimento = COALESCE(%s, depoimento),
                -- Novo envio invalida nota anterior até reavaliação do moderador
                nota_qualidade = CASE
                    WHEN %s IS NOT NULL OR %s IS NOT NULL THEN NULL
                    ELSE nota_qualidade
                END,
                avaliado_em = CASE
                    WHEN %s IS NOT NULL OR %s IS NOT NULL THEN NULL
                    ELSE avaliado_em
                END,
                id_moderador = CASE
                    WHEN %s IS NOT NULL OR %s IS NOT NULL THEN NULL
                    ELSE id_moderador
                END,
                atualizado_em = NOW()
            WHERE id = %s OR id_metrica = %s
            RETURNING *
            """,
            (doc, dep, doc, dep, doc, dep, doc, dep, id_metrica, id_metrica),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError("Métrica/entrega não encontrada.")
        id_sprn = int(row["id_sprn"])
        conn.commit()
        progresso = recalcular_progresso_sprint(conn, id_sprn)
        return {
            "entrega": _serialize_entrega(dict(row)),
            "progresso_qualidade": progresso,
            "id_sprn": id_sprn,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def avaliar_metrica(
    conn,
    *,
    id_metrica: int,
    nota_qualidade: float,
    id_moderador: int | None,
) -> dict:
    if nota_qualidade is None:
        raise ValueError("nota_qualidade é obrigatória.")
    try:
        nota = float(nota_qualidade)
    except (TypeError, ValueError) as exc:
        raise ValueError("nota_qualidade inválida.") from exc
    if nota < 0 or nota > 100:
        raise ValueError("nota_qualidade deve estar entre 0 e 100.")

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT *
            FROM public.dx_entregas_metricas
            WHERE id = %s OR id_metrica = %s
            """,
            (id_metrica, id_metrica),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError("Métrica/entrega não encontrada.")

        doc = (row.get("documento_url") or "").strip()
        dep = (row.get("depoimento") or "").strip()
        if not doc and not dep:
            raise ValueError("Não há comprovação enviada para avaliar.")

        moderador_id = id_moderador
        if moderador_id is not None:
            cur.execute(
                "SELECT 1 FROM public.paneldx_usuarios WHERE id_usuario = %s",
                (moderador_id,),
            )
            if not cur.fetchone():
                moderador_id = None

        cur.execute(
            """
            UPDATE public.dx_entregas_metricas
            SET nota_qualidade = %s,
                avaliado_em = NOW(),
                id_moderador = %s,
                atualizado_em = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (nota, moderador_id, row["id"]),
        )
        updated = cur.fetchone()
        conn.commit()
        id_sprn = int(updated["id_sprn"])
        progresso = recalcular_progresso_sprint(conn, id_sprn)
        return {
            "entrega": _serialize_entrega(dict(updated)),
            "progresso_qualidade": progresso,
            "id_sprn": id_sprn,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def atualizar_dod_checklist(conn, id_sprn: int, itens: list[dict]) -> list[dict]:
    """Atualiza flags concluido. Cada item: {id?} ou {criterio_chave} + concluido."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for item in itens or []:
            concluido = bool(item.get("concluido"))
            item_id = item.get("id")
            chave = item.get("criterio_chave")
            if item_id:
                cur.execute(
                    """
                    UPDATE public.dx_dod_itens
                    SET concluido = %s, atualizado_em = NOW()
                    WHERE id = %s AND id_sprn = %s
                    """,
                    (concluido, int(item_id), id_sprn),
                )
            elif chave:
                cur.execute(
                    """
                    UPDATE public.dx_dod_itens
                    SET concluido = %s, atualizado_em = NOW()
                    WHERE criterio_chave = %s AND id_sprn = %s
                    """,
                    (concluido, chave, id_sprn),
                )
        conn.commit()
        return _list_dod(conn, id_sprn)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def _list_dod(conn, id_sprn: int) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, id_sprn, criterio_chave, criterio_texto, grupo, concluido, atualizado_em
            FROM public.dx_dod_itens
            WHERE id_sprn = %s
            ORDER BY
                CASE grupo
                    WHEN 'required' THEN 0
                    WHEN 'context_education' THEN 1
                    ELSE 2
                END,
                id ASC
            """,
            (id_sprn,),
        )
        rows = cur.fetchall() or []
        return [
            {
                "id": r["id"],
                "id_sprn": r["id_sprn"],
                "criterio_chave": r["criterio_chave"],
                "criterio_texto": r["criterio_texto"],
                "grupo": r["grupo"],
                "concluido": bool(r["concluido"]),
                "atualizado_em": r["atualizado_em"].isoformat() if r.get("atualizado_em") else None,
            }
            for r in rows
        ]
    finally:
        cur.close()


def dod_100_porcento(conn, id_sprn: int) -> tuple[bool, int, int]:
    """Retorna (completo, total, concluidos). Sem itens cadastrados => não completo."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*)::int,
                   COUNT(*) FILTER (WHERE concluido IS TRUE)::int
            FROM public.dx_dod_itens
            WHERE id_sprn = %s
            """,
            (id_sprn,),
        )
        total, ok = cur.fetchone()
        total = int(total or 0)
        ok = int(ok or 0)
        return (total > 0 and total == ok), total, ok
    finally:
        cur.close()


def validar_prontidao_fechamento(conn, id_sprn: int) -> dict:
    """
    Checks and balances para encerrar:
    a) DoD 100% concluído
    b) média das notas do moderador >= 80
    """
    progresso = recalcular_progresso_sprint(conn, int(id_sprn))
    completo, total, ok = dod_100_porcento(conn, int(id_sprn))
    qualidade_ok = progresso >= LIMIAR_QUALIDADE_FECHAMENTO

    erros: list[str] = []
    codigo = None
    if not completo:
        codigo = "dod_incompleto"
        erros.append(
            f"Para concluir a Sprint, 100% dos critérios DoD precisam estar marcados. "
            f"Situação atual: {ok}/{total}."
        )
    if not qualidade_ok:
        codigo = codigo or "qualidade_abaixo"
        erros.append(MSG_QUALIDADE_ABAIXO)

    return {
        "ok": completo and qualidade_ok,
        "codigo": None if (completo and qualidade_ok) else (codigo if len(erros) == 1 else "requisitos_pendentes"),
        "erros": erros,
        "mensagem": erros[0] if len(erros) == 1 else (" ".join(erros) if erros else None),
        "progresso_qualidade": progresso,
        "dod_completo": completo,
        "dod_resumo": {"total": total, "concluidos": ok},
        "limiar_qualidade": LIMIAR_QUALIDADE_FECHAMENTO,
        "qualidade_ok": qualidade_ok,
    }


def enriquecer_sprint_details(conn, payload: dict) -> dict:
    """Anexa entregas, DoD e progresso calculado ao payload de sprint_details."""
    id_sprn = int(payload["id_sprn"])
    entregas = sync_entregas_metricas(conn, id_sprn, payload.get("derv_metr"))
    dod = sync_dod_itens(conn, id_sprn, payload.get("criteria_dod"))
    prontidao = validar_prontidao_fechamento(conn, id_sprn)
    payload["entregas_metricas"] = entregas
    payload["dod_itens"] = dod
    payload["progresso_qualidade"] = prontidao["progresso_qualidade"]
    payload["dod_completo"] = prontidao["dod_completo"]
    payload["dod_resumo"] = prontidao["dod_resumo"]
    payload["prontidao_fechamento"] = prontidao
    payload["limiar_qualidade_fechamento"] = LIMIAR_QUALIDADE_FECHAMENTO
    payload["revisao_consultor_solicitada"] = bool(payload.get("revisao_consultor_solicitada"))
    payload["revisao_consultor_motivo"] = payload.get("revisao_consultor_motivo")
    # realv_sprn alinhado ao progresso recalculado
    payload["realv_sprn"] = str(int(prontidao["progresso_qualidade"]))
    return payload
