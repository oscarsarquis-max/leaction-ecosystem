"""Overrides de metodologia School → B2C (governança pedagógica).

Fail-soft: qualquer falha de leitura devolve None/[] e o Wizard/Dia a Dia
seguem com o catálogo padrão (freemium intacto).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from psycopg2.extras import RealDictCursor

from core.catalogo_metodologias_dia import _slug, resolver_entrada_catalogo
from db import get_conn

_TABLE_ENSURED = False


def _log(msg: str) -> None:
    print(f"[metodologia-override] {msg}", file=sys.stderr, flush=True)


def ensure_overrides_table(cur: Any | None = None) -> None:
    global _TABLE_ENSURED
    if _TABLE_ENSURED and cur is None:
        return
    sql = """
        CREATE TABLE IF NOT EXISTS public.inove_metodologia_overrides (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instituicao_b2b_id          UUID NOT NULL,
            metodologia_key             TEXT NOT NULL,
            metodologia_nome            TEXT,
            diretriz_customizada        TEXT,
            disponivel_dia_a_dia        BOOLEAN NOT NULL DEFAULT TRUE,
            disponivel_desafio          BOOLEAN NOT NULL DEFAULT TRUE,
            is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
            versao                      BIGINT NOT NULL DEFAULT 0,
            atualizado_em               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            origem_config_school_id     UUID,
            synced_at                   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_inove_metodologia_overrides_inst_key
                UNIQUE (instituicao_b2b_id, metodologia_key)
        );
        CREATE INDEX IF NOT EXISTS idx_inove_metodologia_overrides_inst
            ON public.inove_metodologia_overrides (instituicao_b2b_id)
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


def resolve_metodologia_key(
    *,
    metodologia_nome: str | None = None,
    metodologia_codigo: str | None = None,
    metodologia_key: str | None = None,
) -> str | None:
    """Chave estável = id do catálogo canônico B2C (39).

    Ordem: metodologia_key → codigo → resolução por nome/alias → slug do nome.
    """
    for raw in (metodologia_key, metodologia_codigo):
        token = str(raw or "").strip()
        if not token:
            continue
        entrada = resolver_entrada_catalogo(token)
        if entrada:
            return str(entrada["id"])
        # codigo School às vezes = id B2C literal
        if token.replace("-", "_").isalnum() or "_" in token:
            return token

    nome = str(metodologia_nome or "").strip()
    if not nome:
        return None
    entrada = resolver_entrada_catalogo(nome)
    if entrada:
        return str(entrada["id"])
    return f"dia_{_slug(nome)}"


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


def _as_bool(raw: Any, default: bool = True) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in ("0", "false", "no", "nao", "não", "off"):
        return False
    if text in ("1", "true", "yes", "sim", "on"):
        return True
    return default


def _valid_uuid(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (TypeError, ValueError):
        return None


def upsert_methodology_override(payload: dict[str, Any]) -> dict[str, Any]:
    """Persiste override com idempotência e 'versão mais recente vence'."""
    instituicao_id = _valid_uuid(
        payload.get("instituicao_id") or payload.get("instituicao_b2b_id")
    )
    if not instituicao_id:
        return {"ok": False, "reason": "instituicao_id obrigatório"}

    key = resolve_metodologia_key(
        metodologia_nome=payload.get("metodologia_nome"),
        metodologia_codigo=payload.get("metodologia_codigo")
        or payload.get("codigo"),
        metodologia_key=payload.get("metodologia_key"),
    )
    if not key:
        return {"ok": False, "reason": "metodologia_key/nome obrigatórios"}

    atualizado_em = _parse_atualizado_em(
        payload.get("atualizado_em")
        or payload.get("updated_at")
        or payload.get("timestamp")
    )
    versao = _parse_versao(payload.get("versao"), atualizado_em)
    diretriz = payload.get("diretriz_customizada")
    if diretriz is not None:
        diretriz = str(diretriz).strip() or None
    nome = str(payload.get("metodologia_nome") or "").strip() or None
    origem = _valid_uuid(
        payload.get("origem_config_school_id") or payload.get("config_id")
    )
    disponivel_dia = _as_bool(
        payload.get("disponivel_dia_a_dia", payload.get("ativo_dia_a_dia")), True
    )
    disponivel_des = _as_bool(
        payload.get("disponivel_desafio", payload.get("ativo_desafio")), True
    )
    is_active = _as_bool(payload.get("is_active"), True)

    ensure_overrides_table()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.inove_metodologia_overrides (
                    instituicao_b2b_id,
                    metodologia_key,
                    metodologia_nome,
                    diretriz_customizada,
                    disponivel_dia_a_dia,
                    disponivel_desafio,
                    is_active,
                    versao,
                    atualizado_em,
                    origem_config_school_id,
                    synced_at
                )
                VALUES (
                    %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid, CURRENT_TIMESTAMP
                )
                ON CONFLICT (instituicao_b2b_id, metodologia_key) DO UPDATE SET
                    metodologia_nome = COALESCE(
                        EXCLUDED.metodologia_nome,
                        inove_metodologia_overrides.metodologia_nome
                    ),
                    diretriz_customizada = EXCLUDED.diretriz_customizada,
                    disponivel_dia_a_dia = EXCLUDED.disponivel_dia_a_dia,
                    disponivel_desafio = EXCLUDED.disponivel_desafio,
                    is_active = EXCLUDED.is_active,
                    versao = EXCLUDED.versao,
                    atualizado_em = EXCLUDED.atualizado_em,
                    origem_config_school_id = COALESCE(
                        EXCLUDED.origem_config_school_id,
                        inove_metodologia_overrides.origem_config_school_id
                    ),
                    synced_at = CURRENT_TIMESTAMP
                WHERE
                    EXCLUDED.versao > inove_metodologia_overrides.versao
                    OR (
                        EXCLUDED.versao = inove_metodologia_overrides.versao
                        AND EXCLUDED.atualizado_em >= inove_metodologia_overrides.atualizado_em
                    )
                RETURNING
                    id, instituicao_b2b_id, metodologia_key, metodologia_nome,
                    diretriz_customizada, disponivel_dia_a_dia, disponivel_desafio,
                    is_active, versao, atualizado_em, origem_config_school_id,
                    (xmax = 0) AS inserted
                """,
                (
                    instituicao_id,
                    key,
                    nome,
                    diretriz,
                    disponivel_dia,
                    disponivel_des,
                    is_active,
                    versao,
                    atualizado_em,
                    origem,
                ),
            )
            row = cur.fetchone()
            if not row:
                # Evento mais antigo — mantém linha vigente
                cur.execute(
                    """
                    SELECT id, instituicao_b2b_id, metodologia_key, metodologia_nome,
                           diretriz_customizada, disponivel_dia_a_dia, disponivel_desafio,
                           is_active, versao, atualizado_em, origem_config_school_id,
                           FALSE AS inserted
                    FROM public.inove_metodologia_overrides
                    WHERE instituicao_b2b_id = %s::uuid AND metodologia_key = %s
                    """,
                    (instituicao_id, key),
                )
                row = cur.fetchone()
                return {
                    "ok": True,
                    "applied": False,
                    "reason": "stale_event",
                    "override": _row_public(row) if row else None,
                    "metodologia_key": key,
                }

    return {
        "ok": True,
        "applied": True,
        "override": _row_public(row),
        "metodologia_key": key,
    }


def _row_public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    atualizado = row.get("atualizado_em")
    return {
        "id": str(row["id"]) if row.get("id") else None,
        "instituicao_b2b_id": str(row["instituicao_b2b_id"])
        if row.get("instituicao_b2b_id")
        else None,
        "metodologia_key": row.get("metodologia_key"),
        "metodologia_nome": row.get("metodologia_nome"),
        "diretriz_customizada": row.get("diretriz_customizada"),
        "disponivel_dia_a_dia": bool(row.get("disponivel_dia_a_dia", True)),
        "disponivel_desafio": bool(row.get("disponivel_desafio", True)),
        "is_active": bool(row.get("is_active", True)),
        "versao": int(row.get("versao") or 0),
        "atualizado_em": atualizado.isoformat() if atualizado else None,
        "origem_config_school_id": str(row["origem_config_school_id"])
        if row.get("origem_config_school_id")
        else None,
    }


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
        _log(f"get_professor_instituicao: {exc}")
        return None


def list_overrides_for_instituicao(instituicao_id: str | None) -> list[dict[str, Any]]:
    if not instituicao_id:
        return []
    try:
        ensure_overrides_table()
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, instituicao_b2b_id, metodologia_key, metodologia_nome,
                           diretriz_customizada, disponivel_dia_a_dia, disponivel_desafio,
                           is_active, versao, atualizado_em, origem_config_school_id
                    FROM public.inove_metodologia_overrides
                    WHERE instituicao_b2b_id = %s::uuid
                      AND is_active = TRUE
                    """,
                    (str(instituicao_id),),
                )
                return [_row_public(r) for r in cur.fetchall() if r]
    except Exception as exc:
        _log(f"list_overrides: {exc}")
        return []


def overrides_map_for_professor(id_clie: int | None) -> dict[str, dict[str, Any]]:
    """mapa metodologia_key → override ativo. Vazio se solo / erro."""
    try:
        inst = get_professor_instituicao_b2b_id(id_clie)
        if not inst:
            return {}
        rows = list_overrides_for_instituicao(inst)
        return {
            str(r["metodologia_key"]): r
            for r in rows
            if r and r.get("metodologia_key")
        }
    except Exception as exc:
        _log(f"overrides_map: {exc}")
        return {}


def get_override_for_professor(
    id_clie: int | None, metodologia_key_or_nome: str | None
) -> dict[str, Any] | None:
    try:
        key = resolve_metodologia_key(
            metodologia_nome=metodologia_key_or_nome,
            metodologia_key=metodologia_key_or_nome,
            metodologia_codigo=metodologia_key_or_nome,
        )
        if not key:
            return None
        return overrides_map_for_professor(id_clie).get(key)
    except Exception as exc:
        _log(f"get_override: {exc}")
        return None


def blocked_ids_for_vector(
    id_clie: int | None, vector: str
) -> set[str]:
    """IDs bloqueados no vetor ('dia_a_dia' | 'desafio')."""
    field = (
        "disponivel_dia_a_dia" if vector in ("dia", "dia_a_dia", "daily") else "disponivel_desafio"
    )
    try:
        m = overrides_map_for_professor(id_clie)
        return {k for k, v in m.items() if not bool(v.get(field, True))}
    except Exception as exc:
        _log(f"blocked_ids: {exc}")
        return set()


def filter_dinamicas_by_vector(
    items: list[dict[str, Any]],
    id_clie: int | None,
    vector: str,
) -> list[dict[str, Any]]:
    """Remove dinâmicas desabilitadas pela escola; anexa meta de override quando houver."""
    try:
        m = overrides_map_for_professor(id_clie)
        if not m:
            return items
        field = (
            "disponivel_dia_a_dia"
            if vector in ("dia", "dia_a_dia", "daily")
            else "disponivel_desafio"
        )
        out: list[dict[str, Any]] = []
        for item in items:
            mid = str(item.get("id") or "")
            ov = m.get(mid)
            if ov and not bool(ov.get(field, True)):
                continue
            row = dict(item)
            if ov and (ov.get("diretriz_customizada") or not ov.get(field, True)):
                row["escola_override"] = {
                    "ativa": bool(ov.get("diretriz_customizada")),
                    "diretriz_customizada": ov.get("diretriz_customizada"),
                    "versao": ov.get("versao"),
                    "mensagem": _mensagem_ui(ov),
                }
            out.append(row)
        return out
    except Exception as exc:
        _log(f"filter_dinamicas: {exc}")
        return items


def _mensagem_ui(ov: dict[str, Any]) -> str | None:
    diretriz = str(ov.get("diretriz_customizada") or "").strip()
    nome = str(ov.get("metodologia_nome") or ov.get("metodologia_key") or "esta metodologia")
    if not diretriz:
        return None
    resumo = diretriz if len(diretriz) <= 220 else diretriz[:217] + "…"
    return f"Sua escola definiu uma regra para {nome}: {resumo}"


def apply_override_to_caminho(
    caminho: dict[str, Any],
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    """Injeta diretriz no caminho/plano (transparência + contexto IA/mecânica)."""
    if not override or not caminho:
        return caminho
    diretriz = str(override.get("diretriz_customizada") or "").strip()
    if not diretriz:
        # Ainda pode existir só para vetores; marca leve se desabilitado noutro fluxo
        return caminho

    msg = _mensagem_ui(override)
    bloco = (
        f"\n\n[DIRETRIZ DA ESCOLA — obrigatória nesta aula]\n{diretriz}\n"
        "[Fim da diretriz da escola]"
    )
    por_que = str(caminho.get("por_que_usar") or "").strip()
    caminho["por_que_usar"] = (por_que + bloco).strip() if por_que else diretriz

    plano = caminho.get("plano_eduscrum")
    if isinstance(plano, dict):
        missao = str(plano.get("missao") or "").strip()
        plano["missao"] = (missao + bloco).strip() if missao else diretriz.strip()
        plano["metodologia_override_versao_aplicada"] = int(override.get("versao") or 0)
        plano["escola_override"] = {
            "ativa": True,
            "versao": int(override.get("versao") or 0),
            "metodologia_key": override.get("metodologia_key"),
            "diretriz_customizada": diretriz,
            "mensagem": msg,
        }
        cards = plano.get("cards")
        if isinstance(cards, list) and cards:
            first = cards[0] if isinstance(cards[0], dict) else None
            if first is not None:
                mec = str(first.get("mecanica_passo_a_passo") or "").strip()
                first["mecanica_passo_a_passo"] = (
                    f"Respeite a diretriz da escola: {diretriz}\n\n{mec}"
                    if mec
                    else f"Respeite a diretriz da escola: {diretriz}"
                )

    caminho["escola_override"] = {
        "ativa": True,
        "versao": int(override.get("versao") or 0),
        "metodologia_key": override.get("metodologia_key"),
        "diretriz_customizada": diretriz,
        "mensagem": msg,
    }
    caminho["metodologia_override_versao_aplicada"] = int(override.get("versao") or 0)
    return caminho
