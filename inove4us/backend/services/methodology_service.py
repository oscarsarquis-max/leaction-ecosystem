"""
Cache local versionado de dinâmicas rápidas (vetor Dia a Dia).

Desacoplado do app MAtivas: sem import cross-app e sem HTTP interno por enquanto.
Termos de designação comercial/autoral NÃO são expostos na API (nem em categoria).
"""

from __future__ import annotations

import unicodedata
from typing import Any

# Snapshot versionado — dinâmicas para aulas de ~50 min (ciclo rápido).
# IDs canônicos novos; aliases mantêm compatibilidade com drafts antigos.
METODOLOGIAS_RAPIDAS_CACHE: dict[str, dict[str, Any]] = {
    "rapido_minute_paper": {
        "id": "rapido_minute_paper",
        "aliases": ["agil_minute_paper"],
        "nome": "Minute Paper (Votação Rápida)",
        "etiqueta": "Ritmo",
        "descricao_curta": (
            "No fim da aula, os alunos escrevem em 1 minuto a resposta para: "
            "'Qual foi o conceito mais importante de hoje?' e "
            "'Qual dúvida ainda permanece?'."
        ),
    },
    "ideacao_brainstorming_guiado": {
        "id": "ideacao_brainstorming_guiado",
        "aliases": ["criativa_brainstorming_guiado"],
        "nome": "Brainstorming Guiado (3 Ideias)",
        "etiqueta": "Ideação",
        "descricao_curta": (
            "Dinâmica rápida de ideação. Divida em grupos e peça 3 ideias de "
            "solução para o problema do dia em 5 minutos."
        ),
    },
    "checkout_exit_ticket": {
        "id": "checkout_exit_ticket",
        "aliases": ["analitica_exit_ticket"],
        "nome": "Exit Ticket (Ticket de Saída)",
        "etiqueta": "Verificação",
        "descricao_curta": (
            "Para sair da sala, o aluno deve entregar um post-it respondendo a "
            "uma pergunta rápida de verificação do conteúdo da aula."
        ),
    },
}

CACHE_VERSION = "2026-07-23.v3"

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
    }
)


def _norm(texto: str) -> str:
    raw = unicodedata.normalize("NFKD", texto or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(raw.lower().split())


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Cópia pública: sem aliases internos; etiqueta segura."""
    etiqueta = str(item.get("etiqueta") or item.get("categoria") or "Dinâmica").strip()
    if _norm(etiqueta) in _PROIBIDOS:
        etiqueta = "Dinâmica"
    return {
        "id": item["id"],
        "nome": item.get("nome") or "",
        "etiqueta": etiqueta,
        "descricao_curta": item.get("descricao_curta") or "",
    }


def listar_dinamicas_rapidas() -> list[dict[str, Any]]:
    """Retorna todas as entradas do cache (visão pública)."""
    return [_public_item(item) for item in METODOLOGIAS_RAPIDAS_CACHE.values()]


def buscar_dinamicas_rapidas(termo_busca: str = "") -> list[dict[str, Any]]:
    """
    Consulta o dicionário local METODOLOGIAS_RAPIDAS_CACHE.

    Sem termo → todas as dinâmicas.
    Com termo → filtra por id, nome, etiqueta ou descrição (sem acento/case).
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
                    str(item.get("etiqueta") or ""),
                    str(item.get("descricao_curta") or ""),
                    " ".join(str(a) for a in (item.get("aliases") or [])),
                ]
            )
        )
        if termo in blob:
            hits.append(_public_item(item))
    return hits


def get_dinamica_by_id(dinamica_id: str) -> dict[str, Any] | None:
    """Resolve uma dinâmica pelo id canônico ou alias legado."""
    key = (dinamica_id or "").strip()
    if not key:
        return None
    item = METODOLOGIAS_RAPIDAS_CACHE.get(key)
    if item:
        return _public_item(item)
    key_l = key.lower()
    for mid, meta in METODOLOGIAS_RAPIDAS_CACHE.items():
        if mid.lower() == key_l or str(meta.get("id") or "").lower() == key_l:
            return _public_item(meta)
        for alias in meta.get("aliases") or []:
            if str(alias).lower() == key_l:
                return _public_item(meta)
    return None
