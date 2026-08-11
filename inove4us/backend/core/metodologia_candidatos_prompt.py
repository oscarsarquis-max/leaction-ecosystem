"""Seleção conservadora de candidatas para o system prompt do wizard.

O matcher lexical ranqueia; esta camada monta o Top N enviado ao Sonnet.
O Sonnet continua escolhendo A/B/C — scores/keywords NÃO vão no prompt.
"""

from __future__ import annotations

import os
from typing import Any

from core.catalogo_metodologias_dia import (
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
    ETIQUETA_DEDUTIVAS,
    ETIQUETA_INDUTIVAS,
    entradas_catalogo_dia,
    resolver_entrada_catalogo,
)

# Top N configurável (não espalhar magic number).
MATCHER_CANDIDATE_TOP_N = int(os.environ.get("WIZARD_MATCHER_TOP_N", "8"))
MATCHER_CANDIDATE_MIN_N = 3

_FAMILY_ORDER = (
    ETIQUETA_INDUTIVAS,
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
    ETIQUETA_DEDUTIVAS,
)

# Origens só para observabilidade (não vão ao Sonnet).
ORIGEM_SCORE = "top_score"
ORIGEM_PREFERRED = "preferred"
ORIGEM_DIVERSITY = "diversity_fill"
ORIGEM_FULL = "full_catalog"


def _familia(mid: str) -> str:
    entrada = resolver_entrada_catalogo(mid)
    if entrada:
        return str(entrada.get("etiqueta") or "")
    return ""


def _catalogo_ids_por_familia(
    *,
    blocked: set[str],
) -> dict[str, list[str]]:
    """Ordem canônica do catálogo (não lexicográfica global)."""
    buckets: dict[str, list[str]] = {f: [] for f in _FAMILY_ORDER}
    for e in entradas_catalogo_dia():
        mid = str(e["id"])
        if mid in blocked:
            continue
        etq = str(e.get("etiqueta") or "")
        buckets.setdefault(etq, []).append(mid)
    return buckets


def selecionar_candidatos_para_sonnet(
    ranking: list[dict[str, Any]] | None,
    *,
    top_n: int | None = None,
    exclude_ids: set[str] | None = None,
    preferred_id: str | None = None,
) -> dict[str, Any]:
    """Monta até Top N candidatos (id+nome implícitos via catálogo).

    Retorno:
      candidate_ids, positive_count, fill_count, preferred_injected,
      full_catalog_fallback, origins (id→origem), n_min_ok
    """
    n = int(top_n if top_n is not None else MATCHER_CANDIDATE_TOP_N)
    n = max(MATCHER_CANDIDATE_MIN_N, n)
    blocked = {str(x) for x in (exclude_ids or set()) if x}
    pref = (preferred_id or "").strip() or None
    if pref and pref in blocked:
        pref = None
    if pref and not resolver_entrada_catalogo(pref):
        pref = None

    if not isinstance(ranking, list) or not ranking:
        return {
            "candidate_ids": [],
            "positive_count": 0,
            "fill_count": 0,
            "preferred_injected": False,
            "full_catalog_fallback": True,
            "origins": {},
            "n_min_ok": False,
        }

    # Ranking já ordenado por score; filtra bloqueados / ids inválidos.
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in ranking:
        if not isinstance(r, dict):
            continue
        mid = str(r.get("id") or "").strip()
        if not mid or mid in blocked or mid in seen:
            continue
        if not resolver_entrada_catalogo(mid):
            continue
        seen.add(mid)
        rows.append(
            {
                "id": mid,
                "score": int(r.get("score") or 0),
                "nome": r.get("nome") or mid,
            }
        )

    if not rows and not pref:
        return {
            "candidate_ids": [],
            "positive_count": 0,
            "fill_count": 0,
            "preferred_injected": False,
            "full_catalog_fallback": True,
            "origins": {},
            "n_min_ok": False,
        }

    selected: list[str] = []
    origins: dict[str, str] = {}
    preferred_injected = False

    def _add(mid: str, origem: str) -> None:
        nonlocal preferred_injected
        if mid in blocked or mid in origins:
            return
        if not resolver_entrada_catalogo(mid):
            return
        selected.append(mid)
        origins[mid] = origem
        if origem == ORIGEM_PREFERRED:
            preferred_injected = True

    # 1) Metodologia desejada sempre entra (se válida).
    if pref:
        _add(pref, ORIGEM_PREFERRED)

    positives = [r for r in rows if int(r["score"]) > 0]
    positive_count = len(positives)

    # 2) Score > 0 com diversidade simples (família menos representada).
    restantes = [r for r in positives if r["id"] not in origins]
    while len(selected) < n and restantes:
        fam_count: dict[str, int] = {}
        for mid in selected:
            f = _familia(mid)
            fam_count[f] = fam_count.get(f, 0) + 1

        def _chave(r: dict[str, Any]) -> tuple:
            f = _familia(r["id"])
            return (fam_count.get(f, 0), -int(r["score"]), str(r["id"]))

        best = min(restantes, key=_chave)
        _add(best["id"], ORIGEM_SCORE)
        restantes = [r for r in restantes if r["id"] not in origins]

    # 3) Preenchimento determinístico: famílias menos representadas primeiro.
    buckets = _catalogo_ids_por_familia(blocked=blocked)
    while len(selected) < n:
        fam_count: dict[str, int] = {}
        for mid in selected:
            f = _familia(mid)
            fam_count[f] = fam_count.get(f, 0) + 1
        order = sorted(
            _FAMILY_ORDER,
            key=lambda f: (fam_count.get(f, 0), _FAMILY_ORDER.index(f)),
        )
        added = False
        for fam in order:
            for mid in buckets.get(fam) or []:
                if mid in origins:
                    continue
                _add(mid, ORIGEM_DIVERSITY)
                added = True
                break
            if added:
                break
        if not added:
            break

    fill_count = sum(1 for o in origins.values() if o == ORIGEM_DIVERSITY)

    n_min_ok = len(selected) >= MATCHER_CANDIDATE_MIN_N
    # Se não há mínimo viável, fallback para catálogo completo.
    full_fallback = not n_min_ok

    if full_fallback:
        return {
            "candidate_ids": [],
            "positive_count": positive_count,
            "fill_count": fill_count,
            "preferred_injected": preferred_injected,
            "full_catalog_fallback": True,
            "origins": {},
            "n_min_ok": False,
        }

    return {
        "candidate_ids": selected[:n],
        "positive_count": positive_count,
        "fill_count": fill_count,
        "preferred_injected": preferred_injected,
        "full_catalog_fallback": False,
        "origins": {k: origins[k] for k in selected[:n]},
        "n_min_ok": True,
    }


def origem_escolha_sonnet(
    id_metodologia: str | None,
    *,
    origins: dict[str, str] | None,
    full_catalog_fallback: bool,
) -> str:
    """Classifica origem diagnóstica do ID escolhido pelo Sonnet."""
    mid = (id_metodologia or "").strip()
    if not mid:
        return "missing"
    if full_catalog_fallback:
        return ORIGEM_FULL
    return (origins or {}).get(mid, "outside_candidates")
