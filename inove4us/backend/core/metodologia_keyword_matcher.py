"""Matcher lexical de metodologias.

Calcula scores por keywords do catálogo canônico.
NÃO escolhe A/B/C nem altera stitch/fallback local.
O ranking pode alimentar a seleção de candidatas do prompt (Top N).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from core.catalogo_metodologias_dia import entradas_catalogo_dia

# Pesos simples por campo de entrada do wizard
_PESO_PROBLEMA = 3
_PESO_OBJETIVO = 3
_PESO_CONTEXTO = 1
_PESO_DISCIPLINA = 1
_PESO_TURMA = 1
_PESO_DURACAO = 1

# Cap por keyword: presença conta no máx. 1× por campo (evita "projeto"*10)
_MAX_HITS_POR_KEYWORD_POR_CAMPO = 1


def normalizar_texto_match(texto: str) -> str:
    """Lowercase, sem acentos, pontuação → espaço, whitespace colapsado."""
    raw = unicodedata.normalize("NFKD", str(texto or ""))
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = raw.casefold()
    raw = re.sub(r"[^\w\s]", " ", raw, flags=re.UNICODE)
    return " ".join(raw.split())


def _keyword_presente(texto_norm: str, keyword: str) -> bool:
    kw = normalizar_texto_match(keyword)
    if not kw or not texto_norm:
        return False
    # expressão / palavra: limites por espaço (texto já sem pontuação)
    return f" {kw} " in f" {texto_norm} "


def _score_campo(texto: str, keywords: list[str], peso: int) -> tuple[int, list[str]]:
    if peso <= 0 or not texto or not keywords:
        return 0, []
    norm = normalizar_texto_match(texto)
    if not norm:
        return 0, []
    matched: list[str] = []
    score = 0
    for kw in keywords:
        if _keyword_presente(norm, kw):
            # presença (não contagem repetida)
            score += peso * _MAX_HITS_POR_KEYWORD_POR_CAMPO
            matched.append(str(kw).strip())
    return score, matched


def rankear_metodologias_por_keywords(
    *,
    problema: str = "",
    objetivo: str = "",
    turma_nivel: str = "",
    duracao: str = "",
    contexto: str = "",
    disciplina_nome: str = "",
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """
    Ranking determinístico por keywords do catálogo.

    Retorna lista ordenada:
      {id, nome, score, matched_keywords}
    """
    campos = (
        (problema, _PESO_PROBLEMA),
        (objetivo, _PESO_OBJETIVO),
        (contexto, _PESO_CONTEXTO),
        (disciplina_nome, _PESO_DISCIPLINA),
        (turma_nivel, _PESO_TURMA),
        (duracao, _PESO_DURACAO),
    )

    resultados: list[dict[str, Any]] = []
    for entrada in entradas_catalogo_dia():
        keywords = [str(k).strip() for k in (entrada.get("keywords") or []) if str(k).strip()]
        if not keywords:
            resultados.append(
                {
                    "id": entrada["id"],
                    "nome": entrada.get("nome") or entrada["id"],
                    "score": 0,
                    "matched_keywords": [],
                }
            )
            continue

        total = 0
        matched_set: list[str] = []
        seen_kw: set[str] = set()
        for texto, peso in campos:
            sc, matched = _score_campo(texto, keywords, peso)
            total += sc
            for m in matched:
                key = normalizar_texto_match(m)
                if key and key not in seen_kw:
                    seen_kw.add(key)
                    matched_set.append(m)

        resultados.append(
            {
                "id": entrada["id"],
                "nome": entrada.get("nome") or entrada["id"],
                "score": total,
                "matched_keywords": matched_set,
            }
        )

    # maior score; desempate estável por id
    resultados.sort(key=lambda r: (-int(r["score"]), str(r["id"])))
    n = max(0, int(top_n)) if top_n is not None else len(resultados)
    return resultados[:n] if n else resultados


def format_top_log(ranking: list[dict[str, Any]], *, limite: int = 5) -> str:
    """Compacta Top N para log (sem texto do professor)."""
    partes = []
    for row in (ranking or [])[: max(0, limite)]:
        partes.append(f"{row.get('id')}:{row.get('score')}")
    return ",".join(partes)
