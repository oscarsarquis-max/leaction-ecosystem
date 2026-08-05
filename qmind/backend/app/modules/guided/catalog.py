"""Versioned guided question catalog (file-backed)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("catalog_iso9001_c4c5_v1.json")


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_version() -> str:
    return str(load_catalog()["catalog_version"])


def list_questions() -> list[dict[str, Any]]:
    return list(load_catalog()["questions"])


def get_question(question_id: str) -> dict[str, Any] | None:
    for q in list_questions():
        if q["id"] == question_id:
            return q
    return None
