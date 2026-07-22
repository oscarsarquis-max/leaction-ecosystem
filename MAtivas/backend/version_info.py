"""Versão de release do MAtivas — lida de VERSION (+ GIT_SHA no deploy)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _find_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here, here.parent):
        if (candidate / "VERSION").is_file():
            return candidate
    return here.parent


_ROOT = _find_root()


@lru_cache(maxsize=1)
def get_version() -> str:
    env = (os.environ.get("APP_VERSION") or os.environ.get("MATIVAS_VERSION") or "").strip()
    if env:
        return env
    try:
        return (_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def get_git_sha() -> str:
    for key in ("GIT_SHA", "SOURCE_COMMIT", "GITHUB_SHA", "COMMIT_SHA"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val[:12]
    try:
        return (_ROOT / "GIT_SHA").read_text(encoding="utf-8").strip()[:12] or "unknown"
    except OSError:
        return "unknown"


def version_payload(**extra) -> dict:
    payload = {
        "app": "mativas",
        "version": get_version(),
        "git_sha": get_git_sha(),
    }
    payload.update(extra)
    return payload
