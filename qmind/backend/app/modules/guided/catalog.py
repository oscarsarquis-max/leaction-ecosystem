"""Versioned guided question catalogs (file-backed)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent

# Newest first — used for new sessions and default GET /guided/catalog.
_CATALOG_FILES: dict[str, Path] = {
    "iso9001-2015-c4c10-v1": _DIR / "catalog_iso9001_c4c10_v1.json",
    "iso9001-2015-c4c5-v1": _DIR / "catalog_iso9001_c4c5_v1.json",
}

DEFAULT_CATALOG_VERSION = "iso9001-2015-c4c10-v1"


class UnknownCatalogVersion(KeyError):
    """Raised when a session/API asks for a catalog version that is not registered."""


def available_catalog_versions() -> list[str]:
    return list(_CATALOG_FILES.keys())


@lru_cache(maxsize=8)
def load_catalog(version: str | None = None) -> dict[str, Any]:
    ver = version or DEFAULT_CATALOG_VERSION
    path = _CATALOG_FILES.get(ver)
    if path is None or not path.is_file():
        raise UnknownCatalogVersion(ver)
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("catalog_version")) != ver:
        raise ValueError(
            f"Catalog file {path.name} declares version "
            f"{data.get('catalog_version')!r}, expected {ver!r}"
        )
    return data


def clear_catalog_cache() -> None:
    load_catalog.cache_clear()


def catalog_version() -> str:
    """Default (latest) catalog version for new guided sessions."""
    return DEFAULT_CATALOG_VERSION


def list_questions(version: str | None = None) -> list[dict[str, Any]]:
    return list(load_catalog(version)["questions"])


def get_question(
    question_id: str, version: str | None = None
) -> dict[str, Any] | None:
    for q in list_questions(version):
        if q["id"] == question_id:
            return q
    return None
