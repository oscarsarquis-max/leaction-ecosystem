"""Overrides PEI School → B2C (2 níveis: aee_base + individual).

Fail-soft: qualquer falha devolve None/[] — freemium e fluxo da mesa intactos.
Identidade do aluno no B2C: best-effort por nome (não há entidade aluno completa).
Condição (TEA/TDAH…) alinha ao perfil_inclusao do Kanban PEI.
"""

from __future__ import annotations

import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from psycopg2.extras import RealDictCursor

from db import get_conn

_TABLE_ENSURED = False

# Alinha rótulos School (aee_canonico) ↔ B2C (KanbanPeiMenu.PEI_PERFIS)
_CONDICAO_ALIASES: dict[str, str] = {
    "tea": "TEA",
    "espectro autista": "TEA",
    "transtorno do espectro autista": "TEA",
    "tdah": "TDAH",
    "deficit de atencao": "TDAH",
    "déficit de atenção": "TDAH",
    "dislexia": "Dislexia",
    "deficiencia visual": "Deficiência Visual",
    "deficiência visual": "Deficiência Visual",
    "altas habilidades": "Altas Habilidades",
    "deficiencia intelectual": "Deficiência Intelectual",
    "deficiência intelectual": "Deficiência Intelectual",
    "deficiencia auditiva": "Deficiência Auditiva",
    "deficiência auditiva": "Deficiência Auditiva",
    "deficiencia fisica": "Deficiência Física",
    "deficiência física": "Deficiência Física",
    "outras dificuldades severas": "Outras Dificuldades Severas",
}


def _log(msg: str) -> None:
    print(f"[pei-override] {msg}", file=sys.stderr, flush=True)


def _norm_key(texto: str) -> str:
    raw = unicodedata.normalize("NFKD", texto or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(raw.lower().split())


def normalize_condicao(raw: str | None) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    key = _norm_key(text)
    if key in _CONDICAO_ALIASES:
        return _CONDICAO_ALIASES[key]
    # Mantém capitalização School se já for rótulo conhecido
    for canon in _CONDICAO_ALIASES.values():
        if _norm_key(canon) == key:
            return canon
    return text


def normalize_aluno_nome(raw: str | None) -> str:
    return " ".join(str(raw or "").strip().split())


def _parse_atualizado_em(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    text = str(raw or "").strip()
    if text:
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _parse_versao(raw: Any, atualizado_em: datetime) -> int:
    try:
        if raw is not None and str(raw).strip() != "":
            return int(raw)
    except (TypeError, ValueError):
        pass
    return int(atualizado_em.timestamp())


def _valid_uuid(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (TypeError, ValueError):
        return None


def ensure_pei_overrides_tables(cur: Any | None = None) -> None:
    global _TABLE_ENSURED
    if _TABLE_ENSURED and cur is None:
        return
    sql = """
        CREATE TABLE IF NOT EXISTS public.inove_pei_overrides_base (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instituicao_b2b_id      UUID NOT NULL,
            condicao                TEXT NOT NULL,
            diretriz                TEXT NOT NULL DEFAULT '',
            versao                  BIGINT NOT NULL DEFAULT 0,
            atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            aee_matriz_id_origem    UUID,
            is_active               BOOLEAN NOT NULL DEFAULT TRUE,
            synced_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_inove_pei_overrides_base_inst_cond
                UNIQUE (instituicao_b2b_id, condicao)
        );
        CREATE INDEX IF NOT EXISTS idx_inove_pei_overrides_base_inst
            ON public.inove_pei_overrides_base (instituicao_b2b_id)
            WHERE is_active = TRUE;

        CREATE TABLE IF NOT EXISTS public.inove_pei_overrides_individual (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instituicao_b2b_id      UUID NOT NULL,
            aluno_id                UUID NOT NULL,
            aluno_nome              TEXT NOT NULL DEFAULT '',
            condicao                TEXT NOT NULL DEFAULT '',
            particularidades        TEXT NOT NULL DEFAULT '',
            versao                  BIGINT NOT NULL DEFAULT 0,
            atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            pei_aluno_id_origem     UUID,
            aee_matriz_id_base      UUID,
            is_active               BOOLEAN NOT NULL DEFAULT TRUE,
            synced_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_inove_pei_overrides_indiv_inst_aluno
                UNIQUE (instituicao_b2b_id, aluno_id)
        );
        CREATE INDEX IF NOT EXISTS idx_inove_pei_overrides_indiv_inst
            ON public.inove_pei_overrides_individual (instituicao_b2b_id)
            WHERE is_active = TRUE;
    """
    if cur is not None:
        cur.execute(sql)
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute(sql)
        _TABLE_ENSURED = True
    except Exception as exc:
        _log(f"ensure_table falhou: {exc}")


def get_professor_instituicao_b2b_id(id_clie: int | None) -> str | None:
    if not id_clie:
        return None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT instituicao_b2b_id
                    FROM public.ctdi_clie
                    WHERE id_clie = %s
                    """,
                    (int(id_clie),),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return None
                return str(row[0])
    except Exception as exc:
        _log(f"get_instituicao: {exc}")
        return None


def _row_base(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    atualizado = row.get("atualizado_em")
    return {
        "nivel": "aee_base",
        "id": str(row["id"]) if row.get("id") else None,
        "instituicao_b2b_id": str(row["instituicao_b2b_id"])
        if row.get("instituicao_b2b_id")
        else None,
        "condicao": row.get("condicao"),
        "diretriz": row.get("diretriz") or "",
        "versao": int(row.get("versao") or 0),
        "atualizado_em": atualizado.isoformat() if atualizado else None,
        "aee_matriz_id_origem": str(row["aee_matriz_id_origem"])
        if row.get("aee_matriz_id_origem")
        else None,
        "is_active": bool(row.get("is_active", True)),
        "mensagem": _mensagem_base(row),
    }


def _row_indiv(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    atualizado = row.get("atualizado_em")
    return {
        "nivel": "individual",
        "id": str(row["id"]) if row.get("id") else None,
        "instituicao_b2b_id": str(row["instituicao_b2b_id"])
        if row.get("instituicao_b2b_id")
        else None,
        "aluno_id": str(row["aluno_id"]) if row.get("aluno_id") else None,
        "aluno_nome": row.get("aluno_nome") or "",
        "condicao": row.get("condicao") or "",
        "particularidades": row.get("particularidades") or "",
        "versao": int(row.get("versao") or 0),
        "atualizado_em": atualizado.isoformat() if atualizado else None,
        "pei_aluno_id_origem": str(row["pei_aluno_id_origem"])
        if row.get("pei_aluno_id_origem")
        else None,
        "aee_matriz_id_base": str(row["aee_matriz_id_base"])
        if row.get("aee_matriz_id_base")
        else None,
        "is_active": bool(row.get("is_active", True)),
        "mensagem": _mensagem_indiv(row),
    }


def _mensagem_base(row: dict[str, Any]) -> str | None:
    diretriz = str(row.get("diretriz") or "").strip()
    cond = str(row.get("condicao") or "esta condição")
    if not diretriz:
        return None
    resumo = diretriz if len(diretriz) <= 220 else diretriz[:217] + "…"
    return f"Sua escola definiu uma diretriz AEE para {cond}: {resumo}"


def _mensagem_indiv(row: dict[str, Any]) -> str | None:
    part = str(row.get("particularidades") or "").strip()
    nome = str(row.get("aluno_nome") or "o aluno")
    if not part:
        return None
    resumo = part if len(part) <= 220 else part[:217] + "…"
    return f"PEI individual de {nome} em vigor: {resumo}"


def upsert_pei_override(payload: dict[str, Any]) -> dict[str, Any]:
    """Persiste conforme payload.nivel (aee_base | individual)."""
    nivel = str(payload.get("nivel") or "").strip().lower()
    if nivel in ("aee_base", "base", "aee"):
        return _upsert_base(payload)
    if nivel in ("individual", "pei_individual", "aluno"):
        return _upsert_individual(payload)
    return {
        "ok": False,
        "reason": "nivel obrigatório (aee_base|individual)",
        "override_applied": False,
    }


def _upsert_base(payload: dict[str, Any]) -> dict[str, Any]:
    instituicao_id = _valid_uuid(
        payload.get("instituicao_id") or payload.get("instituicao_b2b_id")
    )
    condicao = normalize_condicao(payload.get("condicao") or payload.get("condicao_categoria"))
    if not instituicao_id or not condicao:
        return {"ok": False, "reason": "instituicao_id/condicao obrigatórios"}

    atualizado_em = _parse_atualizado_em(
        payload.get("atualizado_em") or payload.get("updated_at")
    )
    versao = _parse_versao(payload.get("versao"), atualizado_em)
    diretriz = str(payload.get("diretriz") or "").strip()
    aee_id = _valid_uuid(payload.get("aee_matriz_id") or payload.get("aee_matriz_id_origem"))
    is_active = payload.get("is_active")
    if is_active is None:
        is_active = True

    ensure_pei_overrides_tables()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.inove_pei_overrides_base (
                    instituicao_b2b_id, condicao, diretriz, versao, atualizado_em,
                    aee_matriz_id_origem, is_active, synced_at
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s::uuid, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (instituicao_b2b_id, condicao) DO UPDATE SET
                    diretriz = EXCLUDED.diretriz,
                    versao = EXCLUDED.versao,
                    atualizado_em = EXCLUDED.atualizado_em,
                    aee_matriz_id_origem = COALESCE(
                        EXCLUDED.aee_matriz_id_origem,
                        inove_pei_overrides_base.aee_matriz_id_origem
                    ),
                    is_active = EXCLUDED.is_active,
                    synced_at = CURRENT_TIMESTAMP
                WHERE
                    EXCLUDED.versao > inove_pei_overrides_base.versao
                    OR (
                        EXCLUDED.versao = inove_pei_overrides_base.versao
                        AND EXCLUDED.atualizado_em >= inove_pei_overrides_base.atualizado_em
                    )
                RETURNING *
                """,
                (
                    instituicao_id,
                    condicao,
                    diretriz,
                    versao,
                    atualizado_em,
                    aee_id,
                    bool(is_active),
                ),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_base
                    WHERE instituicao_b2b_id = %s::uuid AND condicao = %s
                    """,
                    (instituicao_id, condicao),
                )
                row = cur.fetchone()
                return {
                    "ok": True,
                    "applied": False,
                    "reason": "stale_event",
                    "nivel": "aee_base",
                    "override": _row_base(row),
                }
    return {
        "ok": True,
        "applied": True,
        "nivel": "aee_base",
        "override": _row_base(row),
    }


def _upsert_individual(payload: dict[str, Any]) -> dict[str, Any]:
    instituicao_id = _valid_uuid(
        payload.get("instituicao_id") or payload.get("instituicao_b2b_id")
    )
    aluno_id = _valid_uuid(payload.get("aluno_id"))
    if not instituicao_id or not aluno_id:
        return {"ok": False, "reason": "instituicao_id/aluno_id obrigatórios"}

    atualizado_em = _parse_atualizado_em(
        payload.get("atualizado_em") or payload.get("updated_at")
    )
    versao = _parse_versao(payload.get("versao"), atualizado_em)
    aluno_nome = normalize_aluno_nome(payload.get("aluno_nome"))
    condicao = normalize_condicao(payload.get("condicao")) or ""
    particularidades = str(payload.get("particularidades") or "").strip()
    pei_origem = _valid_uuid(
        payload.get("pei_aluno_id") or payload.get("pei_aluno_id_origem")
    )
    aee_base = _valid_uuid(payload.get("aee_matriz_id_base"))
    is_active = payload.get("is_active")
    if is_active is None:
        is_active = True

    ensure_pei_overrides_tables()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.inove_pei_overrides_individual (
                    instituicao_b2b_id, aluno_id, aluno_nome, condicao,
                    particularidades, versao, atualizado_em,
                    pei_aluno_id_origem, aee_matriz_id_base, is_active, synced_at
                )
                VALUES (
                    %s::uuid, %s::uuid, %s, %s, %s, %s, %s,
                    %s::uuid, %s::uuid, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (instituicao_b2b_id, aluno_id) DO UPDATE SET
                    aluno_nome = COALESCE(
                        NULLIF(EXCLUDED.aluno_nome, ''),
                        inove_pei_overrides_individual.aluno_nome
                    ),
                    condicao = COALESCE(
                        NULLIF(EXCLUDED.condicao, ''),
                        inove_pei_overrides_individual.condicao
                    ),
                    particularidades = EXCLUDED.particularidades,
                    versao = EXCLUDED.versao,
                    atualizado_em = EXCLUDED.atualizado_em,
                    pei_aluno_id_origem = COALESCE(
                        EXCLUDED.pei_aluno_id_origem,
                        inove_pei_overrides_individual.pei_aluno_id_origem
                    ),
                    aee_matriz_id_base = COALESCE(
                        EXCLUDED.aee_matriz_id_base,
                        inove_pei_overrides_individual.aee_matriz_id_base
                    ),
                    is_active = EXCLUDED.is_active,
                    synced_at = CURRENT_TIMESTAMP
                WHERE
                    EXCLUDED.versao > inove_pei_overrides_individual.versao
                    OR (
                        EXCLUDED.versao = inove_pei_overrides_individual.versao
                        AND EXCLUDED.atualizado_em
                            >= inove_pei_overrides_individual.atualizado_em
                    )
                RETURNING *
                """,
                (
                    instituicao_id,
                    aluno_id,
                    aluno_nome,
                    condicao,
                    particularidades,
                    versao,
                    atualizado_em,
                    pei_origem,
                    aee_base,
                    bool(is_active),
                ),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_individual
                    WHERE instituicao_b2b_id = %s::uuid AND aluno_id = %s::uuid
                    """,
                    (instituicao_id, aluno_id),
                )
                row = cur.fetchone()
                return {
                    "ok": True,
                    "applied": False,
                    "reason": "stale_event",
                    "nivel": "individual",
                    "override": _row_indiv(row),
                }
    return {
        "ok": True,
        "applied": True,
        "nivel": "individual",
        "override": _row_indiv(row),
    }


def get_base_for_professor(
    id_clie: int | None, condicao: str | None
) -> dict[str, Any] | None:
    try:
        inst = get_professor_instituicao_b2b_id(id_clie)
        cond = normalize_condicao(condicao)
        if not inst or not cond:
            return None
        ensure_pei_overrides_tables()
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_base
                    WHERE instituicao_b2b_id = %s::uuid
                      AND lower(trim(condicao)) = lower(trim(%s))
                      AND is_active = TRUE
                    LIMIT 1
                    """,
                    (inst, cond),
                )
                return _row_base(cur.fetchone())
    except Exception as exc:
        _log(f"get_base: {exc}")
        return None


def get_individual_by_nome(
    id_clie: int | None, aluno_nome: str | None
) -> dict[str, Any] | None:
    """Match best-effort: igualdade normalizada do nome."""
    try:
        inst = get_professor_instituicao_b2b_id(id_clie)
        nome = normalize_aluno_nome(aluno_nome)
        if not inst or not nome:
            return None
        ensure_pei_overrides_tables()
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_individual
                    WHERE instituicao_b2b_id = %s::uuid
                      AND is_active = TRUE
                      AND lower(trim(aluno_nome)) = lower(trim(%s))
                    ORDER BY versao DESC
                    LIMIT 1
                    """,
                    (inst, nome),
                )
                row = cur.fetchone()
                if row:
                    return _row_indiv(row)
                # Fallback best-effort: contém / contido (João vs João Pedro)
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_individual
                    WHERE instituicao_b2b_id = %s::uuid AND is_active = TRUE
                    """,
                    (inst,),
                )
                target = _norm_key(nome)
                best = None
                for r in cur.fetchall() or []:
                    cand = _norm_key(r.get("aluno_nome") or "")
                    if not cand:
                        continue
                    if cand == target or target in cand or cand in target:
                        if best is None or int(r.get("versao") or 0) > int(
                            best.get("versao") or 0
                        ):
                            best = r
                return _row_indiv(best)

    except Exception as exc:
        _log(f"get_individual_by_nome: {exc}")
        return None


def resolve_context_for_professor(
    id_clie: int | None,
    *,
    condicao: str | None = None,
    aluno_nome: str | None = None,
) -> dict[str, Any]:
    """Monta contexto injetável (base ± individual). Fail-soft → vazio."""
    out: dict[str, Any] = {
        "base": None,
        "individual": None,
        "bloco_prompt": "",
        "mensagem_ui": None,
        "pei_override_versao_aplicada": None,
    }
    try:
        base = get_base_for_professor(id_clie, condicao) if condicao else None
        indiv = get_individual_by_nome(id_clie, aluno_nome) if aluno_nome else None
        # Se individual tem condição e base ainda não veio, completa
        if indiv and not base and indiv.get("condicao"):
            base = get_base_for_professor(id_clie, indiv.get("condicao"))
        out["base"] = base
        out["individual"] = indiv
        parts: list[str] = []
        msgs: list[str] = []
        versoes: dict[str, int] = {}
        if base and base.get("diretriz"):
            parts.append(
                f"[DIRETRIZ AEE DA ESCOLA — {base.get('condicao')}]\n"
                f"{base['diretriz']}\n"
                "[Fim da diretriz AEE]"
            )
            if base.get("mensagem"):
                msgs.append(base["mensagem"])
            versoes["base"] = int(base.get("versao") or 0)
        if indiv and indiv.get("particularidades"):
            parts.append(
                f"[PEI INDIVIDUAL — {indiv.get('aluno_nome') or 'aluno'}]\n"
                f"{indiv['particularidades']}\n"
                "[Fim do PEI individual]"
            )
            if indiv.get("mensagem"):
                msgs.append(indiv["mensagem"])
            versoes["individual"] = int(indiv.get("versao") or 0)
            if indiv.get("aluno_id"):
                versoes["aluno_id"] = indiv["aluno_id"]  # type: ignore[assignment]
            if indiv.get("pei_aluno_id_origem"):
                versoes["pei_aluno_id"] = indiv["pei_aluno_id_origem"]  # type: ignore[assignment]
        out["bloco_prompt"] = "\n\n".join(parts).strip()
        out["mensagem_ui"] = " ".join(msgs) if msgs else None
        out["pei_override_versao_aplicada"] = versoes or None
    except Exception as exc:
        _log(f"resolve_context: {exc}")
    return out


def list_overrides_for_professor(id_clie: int | None) -> dict[str, Any]:
    try:
        inst = get_professor_instituicao_b2b_id(id_clie)
        if not inst:
            return {"base": [], "individual": []}
        ensure_pei_overrides_tables()
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_base
                    WHERE instituicao_b2b_id = %s::uuid AND is_active = TRUE
                    ORDER BY condicao
                    """,
                    (inst,),
                )
                bases = [_row_base(r) for r in cur.fetchall() if r]
                cur.execute(
                    """
                    SELECT * FROM public.inove_pei_overrides_individual
                    WHERE instituicao_b2b_id = %s::uuid AND is_active = TRUE
                    ORDER BY aluno_nome
                    """,
                    (inst,),
                )
                indivs = [_row_indiv(r) for r in cur.fetchall() if r]
        return {"base": bases, "individual": indivs}
    except Exception as exc:
        _log(f"list_overrides: {exc}")
        return {"base": [], "individual": []}
