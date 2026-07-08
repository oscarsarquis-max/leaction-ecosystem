"""Setor e framework padrão do Chamelleon — Educação (dimensão LA canônica)."""

from __future__ import annotations

# Educação é o setor padrão: a 5ª dimensão É a LA (Aprendizagem em Ação), não uma substituição.
DEFAULT_SECTOR = "educação"
DEFAULT_FRAMEWORK_ID = "educacao-v1"
DEFAULT_SECTOR_ACRONYM = "LA"
DEFAULT_SECTOR_ACTION_NAME = "Aprendizagem em Ação"
DEFAULT_SECTOR_FULL_LABEL = "Aprendizagem em Ação - LA"
DEFAULT_SECTOR_LEGACY_SETOR = "EDUCACAO"

# Dimensões universais (imutáveis) — id_dime legado PanelDX
UNIVERSAL_LEGACY_DIME_IDS = (1, 2, 3, 5)
SECTOR_LEGACY_DIME_ID = 4  # LA

LEGACY_DIME_ID_TO_KEY: dict[int, str] = {
    1: "SV",
    2: "HC",
    3: "FS",
    4: "LA",
    5: "DA",
}

LEGACY_DOMAIN_ID_TO_KEY: dict[int, str] = {
    1: "ds",
    2: "bm",
    3: "ic",
    4: "dc",
    5: "cc",
    6: "dg",
    7: "dp",
    8: "cap",
    9: "dm",
}

DOMAIN_NAMES_PT: dict[str, str] = {
    "ds": "Estratégia Digital",
    "bm": "Modelos de Negócio",
    "ic": "Inovação",
    "dc": "Cultura de Dados",
    "cc": "Colaboração",
    "dg": "Governança",
    "dp": "Plataformas",
    "cap": "Capacidades",
    "dm": "Métricas",
}

_EDUCATION_SECTOR_KEYS = frozenset(
    {"educação", "educacao", "education", "edu", "ensino"}
)


def _sector_key(sector: str | None) -> str:
    if not sector:
        return ""
    return sector.strip().lower()


def is_canonical_education_sector(sector: str | None) -> bool:
    """True para o setor base Educação (dimensão LA canônica)."""
    return _sector_key(sector) in _EDUCATION_SECTOR_KEYS


def is_canonical_education_framework(framework_id: str | None) -> bool:
    return (framework_id or "").strip().lower() == DEFAULT_FRAMEWORK_ID
