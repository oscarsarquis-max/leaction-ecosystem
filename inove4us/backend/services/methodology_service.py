"""
Dinâmicas do vetor Dia a Dia — catálogo de 39 nomes (base da obra / MAtivas).

Expõe nome + descrição curta (quando houver mecânica em METODOLOGIAS_DB).
NÃO devolve designações/categorias autorais (ÁGEIS, CRI-ATIVAS, etc.).
"""

from __future__ import annotations

import unicodedata
from typing import Any

from core.catalogo_metodologias_dia import (
    ETIQUETA_INDUTIVAS,
    entradas_catalogo_dia,
    etiqueta_publica,
)
from core.metodologias_db import METODOLOGIAS_DB

CACHE_VERSION = "2026-07-23.v6"

# IDs antigos do cache mínimo → id canônico do catálogo Dia a Dia
_ALIASES_LEGADOS: dict[str, str] = {
    "rapido_minute_paper": "agil_minute_paper",
    "ideacao_brainstorming_guiado": "criativa_design_thinking_express",
    "checkout_exit_ticket": "analitica_diagnostico_coletivo",
    # Design Thinking Express era o nome curto no DB de 16
    "criativa_design_thinking_express": "criativa_design_thinking_express",
}


def _norm(texto: str) -> str:
    raw = unicodedata.normalize("NFKD", texto or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(raw.lower().split())


def _descricao_curta_db(meta: dict[str, Any]) -> str:
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


def _descricao_para_entrada(entrada: dict[str, Any]) -> str:
    id_db = entrada.get("id_db")
    if id_db and id_db in METODOLOGIAS_DB:
        return _descricao_curta_db(METODOLOGIAS_DB[id_db])

    # fallback: match por nome/alias no DB de mecânicas
    alvos = {_norm(entrada["nome"])}
    for a in entrada.get("aliases") or []:
        alvos.add(_norm(a))
    for mid, meta in METODOLOGIAS_DB.items():
        if _norm(meta.get("nome") or "") in alvos or _norm(mid) in alvos:
            return _descricao_curta_db(meta)

    return "Dinâmica da base de metodologias — use na estação em campo do ciclo."


def _build_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for entrada in entradas_catalogo_dia():
        mid = entrada["id"]
        aliases = list(entrada.get("aliases") or [])
        # permitir resolver também pelo id_db quando diferente
        id_db = entrada.get("id_db")
        if id_db and id_db != mid and id_db not in aliases:
            aliases.append(id_db)
        catalog[mid] = {
            "id": mid,
            "nome": entrada["nome"],
            "etiqueta": etiqueta_publica(
                entrada.get("etiqueta"), fallback=ETIQUETA_INDUTIVAS
            ),
            "descricao_curta": _descricao_para_entrada(entrada),
            "aliases": aliases,
        }

    for alias, canonical in _ALIASES_LEGADOS.items():
        if canonical in catalog and alias not in catalog:
            if alias not in catalog[canonical]["aliases"]:
                catalog[canonical]["aliases"].append(alias)
    return catalog


METODOLOGIAS_RAPIDAS_CACHE: dict[str, dict[str, Any]] = _build_catalog()


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    etiqueta = etiqueta_publica(item.get("etiqueta"), fallback=ETIQUETA_INDUTIVAS)
    return {
        "id": item["id"],
        "nome": item.get("nome") or "",
        "etiqueta": etiqueta,
        "descricao_curta": item.get("descricao_curta") or "",
    }


def listar_dinamicas_rapidas() -> list[dict[str, Any]]:
    items = [_public_item(item) for item in METODOLOGIAS_RAPIDAS_CACHE.values()]
    items.sort(key=lambda x: _norm(x.get("nome") or ""))
    return items


def buscar_dinamicas_rapidas(termo_busca: str = "") -> list[dict[str, Any]]:
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
    key = (dinamica_id or "").strip()
    if not key:
        return None

    canonical = _ALIASES_LEGADOS.get(key) or _ALIASES_LEGADOS.get(key.lower())
    if canonical and canonical in METODOLOGIAS_RAPIDAS_CACHE:
        return _public_item(METODOLOGIAS_RAPIDAS_CACHE[canonical])

    item = METODOLOGIAS_RAPIDAS_CACHE.get(key)
    if item:
        return _public_item(item)

    key_l = key.lower()
    key_n = _norm(key)
    for mid, meta in METODOLOGIAS_RAPIDAS_CACHE.items():
        if mid.lower() == key_l or _norm(meta.get("nome") or "") == key_n:
            return _public_item(meta)
        for alias in meta.get("aliases") or []:
            if str(alias).lower() == key_l or _norm(alias) == key_n:
                return _public_item(meta)
    return None
