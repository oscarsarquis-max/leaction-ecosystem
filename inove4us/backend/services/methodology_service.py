"""
Dinâmicas do vetor Dia a Dia — catálogo completo a partir de core.metodologias_db.

Expõe o nome de cada atividade e uma descrição curta.
NÃO devolve as designações/categorias autorais proibidas (ÁGEIS, CRI-ATIVAS, etc.).
"""

from __future__ import annotations

import unicodedata
from typing import Any

from core.metodologias_db import METODOLOGIAS_DB

CACHE_VERSION = "2026-07-23.v4"

# Nunca devolver estes rótulos na API do Dia a Dia (questão autoral).
_PROIBIDOS = frozenset(
    {
        "ageis",
        "ágeis",
        "criativas",
        "cri-ativas",
        "cri ativas",
        "imersivas",
        "analiticas",
        "analíticas",
        "inov-ativas",
        "inovativas",
        "metodologias inovativas",
        "metodologias inov-ativas",
    }
)

# IDs antigos do cache mínimo → id canônico do METODOLOGIAS_DB
_ALIASES_LEGADOS: dict[str, str] = {
    "rapido_minute_paper": "agil_minute_paper",
    "ideacao_brainstorming_guiado": "criativa_design_thinking_express",
    "checkout_exit_ticket": "analitica_diagnostico_coletivo",
}


def _norm(texto: str) -> str:
    raw = unicodedata.normalize("NFKD", texto or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(raw.lower().split())


def _descricao_curta(meta: dict[str, Any]) -> str:
    """Monta um resumo usável no Dia a Dia a partir dos cards estáticos."""
    cards = meta.get("cards") or []
    if not cards:
        return str(meta.get("nome") or "").strip()
    primeiro = cards[0] if isinstance(cards[0], dict) else {}
    objetivo = str(primeiro.get("objetivo") or "").strip()
    foco = str(primeiro.get("foco_da_metodologia_escolhida") or "").strip()
    titulo = str(primeiro.get("titulo") or primeiro.get("titulo_do_card") or "").strip()
    if objetivo:
        return objetivo[:400]
    if foco:
        return foco[:400]
    if titulo:
        return f"Começa por: {titulo}"[:400]
    return str(meta.get("nome") or "").strip()


def _build_catalog() -> dict[str, dict[str, Any]]:
    """Índice id → item interno (com aliases)."""
    catalog: dict[str, dict[str, Any]] = {}
    for mid, meta in METODOLOGIAS_DB.items():
        nome = str(meta.get("nome") or mid).strip()
        item = {
            "id": mid,
            "nome": nome,
            "etiqueta": "Dinâmica",
            "descricao_curta": _descricao_curta(meta),
            "aliases": [],
        }
        catalog[mid] = item

    # aliases legados apontam para a entrada canônica
    for alias, canonical in _ALIASES_LEGADOS.items():
        if canonical in catalog and alias not in catalog:
            catalog[canonical]["aliases"].append(alias)
    return catalog


METODOLOGIAS_RAPIDAS_CACHE: dict[str, dict[str, Any]] = _build_catalog()


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Cópia pública: só id, nome, etiqueta neutra e descrição."""
    etiqueta = str(item.get("etiqueta") or "Dinâmica").strip() or "Dinâmica"
    if _norm(etiqueta) in _PROIBIDOS:
        etiqueta = "Dinâmica"
    return {
        "id": item["id"],
        "nome": item.get("nome") or "",
        "etiqueta": etiqueta,
        "descricao_curta": item.get("descricao_curta") or "",
    }


def listar_dinamicas_rapidas() -> list[dict[str, Any]]:
    """Todas as metodologias do catálogo local (visão pública, sem categorias)."""
    items = [_public_item(item) for item in METODOLOGIAS_RAPIDAS_CACHE.values()]
    items.sort(key=lambda x: _norm(x.get("nome") or ""))
    return items


def buscar_dinamicas_rapidas(termo_busca: str = "") -> list[dict[str, Any]]:
    """
    Sem termo → catálogo completo.
    Com termo → filtra por id, nome ou descrição (sem acento/case).
    """
    termo = _norm(termo_busca)
    if not termo:
        return listar_dinamicas_rapidas()

    hits: list[dict[str, Any]] = []
    for item in METODOLOGIAS_RAPIDAS_CACHE.values():
        blob = _norm(
            " ".join(
                [
                    str(item.get("id") or ""),
                    str(item.get("nome") or ""),
                    str(item.get("descricao_curta") or ""),
                    " ".join(str(a) for a in (item.get("aliases") or [])),
                ]
            )
        )
        if termo in blob:
            hits.append(_public_item(item))
    hits.sort(key=lambda x: _norm(x.get("nome") or ""))
    return hits


def get_dinamica_by_id(dinamica_id: str) -> dict[str, Any] | None:
    """Resolve pelo id canônico do METODOLOGIAS_DB ou alias legado."""
    key = (dinamica_id or "").strip()
    if not key:
        return None

    # alias legado → canônico
    canonical = _ALIASES_LEGADOS.get(key) or _ALIASES_LEGADOS.get(key.lower())
    if canonical and canonical in METODOLOGIAS_RAPIDAS_CACHE:
        return _public_item(METODOLOGIAS_RAPIDAS_CACHE[canonical])

    item = METODOLOGIAS_RAPIDAS_CACHE.get(key)
    if item:
        return _public_item(item)

    key_l = key.lower()
    for mid, meta in METODOLOGIAS_RAPIDAS_CACHE.items():
        if mid.lower() == key_l:
            return _public_item(meta)
        for alias in meta.get("aliases") or []:
            if str(alias).lower() == key_l:
                return _public_item(meta)
    return None
