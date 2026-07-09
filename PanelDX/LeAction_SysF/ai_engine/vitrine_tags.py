"""Classificação de tags da vitrine ActionHub — gravada na criação da Sprint (IA).

A IA classifica apenas na genese; o match em runtime é SQL (overlap de arrays).
Tags canônicas: formacao | equipamentos | software
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

CANONICAL_TAGS = ("formacao", "equipamentos", "software")

_TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "software": (
        "software",
        "sistema",
        "lms",
        "erp",
        "saas",
        "plataforma",
        "aplicativo",
        "licenca",
        "crm",
        "cloud",
        "cyber",
        "seguranca da informacao",
        "gestao escolar",
    ),
    "equipamentos": (
        "infraestrutura",
        "infra",
        "rede",
        "roteador",
        "switch",
        "servidor",
        "hardware",
        "notebook",
        "chromebook",
        "tablet",
        "impressora",
        "projetor",
        "laboratorio",
        "equipamento",
        "automacao",
        "tecnologia da informacao",
    ),
    "formacao": (
        "formacao",
        "lideranca",
        "curso",
        "treinamento",
        "capacitacao",
        "pedagog",
        "metodolog",
        "workshop",
        "mentoria",
        "cultura",
        "pessoas",
        "gestao de pessoas",
        "tatico",
    ),
}


def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_tag(raw: Any) -> str | None:
    if raw is None:
        return None
    t = _normalize(str(raw)).replace(" ", "_").replace("-", "_")
    aliases = {
        "formacao": "formacao",
        "formação": "formacao",
        "equipamentos": "equipamentos",
        "equipamento": "equipamentos",
        "infra": "equipamentos",
        "infraestrutura": "equipamentos",
        "software": "software",
        "sistemas": "software",
    }
    if t in aliases:
        return aliases[t]
    if t in CANONICAL_TAGS:
        return t
    return None


def classify_vitrine_tags(
    *,
    nome_sprint: str | None = None,
    desc_sprint: str | None = None,
    name_bloc: str | None = None,
    name_doma: str | None = None,
    dime_num: int | None = None,
    ai_tags: Iterable[Any] | None = None,
    tatico: bool = False,
) -> list[str]:
    """
    Resolve tags canônicas para persistir em ctdi_sprn.tags.

    Prioridade:
      1) tags explícitas da IA (campo tags / vitrine_categories no JSON)
      2) keywords em domínio/bloco/nome/descrição
      3) fallback: formacao (DIM / tático)
    """
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(tag: str | None) -> None:
        if tag and tag in CANONICAL_TAGS and tag not in seen:
            seen.add(tag)
            ordered.append(tag)

    if ai_tags:
        for raw in ai_tags:
            if isinstance(raw, (list, tuple)):
                for inner in raw:
                    _add(_normalize_tag(inner))
            else:
                _add(_normalize_tag(raw))

    haystack = _normalize(
        " ".join(
            str(p)
            for p in (name_doma, name_bloc, nome_sprint, desc_sprint)
            if p
        )
    )
    for tag, keywords in _TAG_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            _add(tag)

    if not ordered:
        if tatico or (dime_num is not None and 1 <= int(dime_num) <= 5):
            _add("formacao")
        elif re.search(r"\b(ti|infra|rede)\b", haystack):
            _add("equipamentos")
        else:
            _add("formacao")

    return ordered
