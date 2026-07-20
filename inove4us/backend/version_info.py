"""Versão de release do inove4us — lida de VERSION (+ GIT_SHA no deploy)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VERSION_FILE = _ROOT / "VERSION"


@lru_cache(maxsize=1)
def get_version() -> str:
    env = (os.environ.get("APP_VERSION") or os.environ.get("INOVE4US_VERSION") or "").strip()
    if env:
        return env
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def get_git_sha() -> str:
    for key in ("GIT_SHA", "SOURCE_COMMIT", "GITHUB_SHA", "COMMIT_SHA"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val[:12]
    sha_file = _ROOT / "GIT_SHA"
    try:
        return sha_file.read_text(encoding="utf-8").strip()[:12] or "unknown"
    except OSError:
        return "unknown"


def version_payload(**extra) -> dict:
    payload = {
        "app": "inove4us",
        "version": get_version(),
        "git_sha": get_git_sha(),
    }
    payload.update(extra)
    return payload
