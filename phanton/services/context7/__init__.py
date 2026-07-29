"""Factory de providers context7 (env CONTEXT7_PROVIDER)."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from services.context7.provider_base import Context7Provider
from services.context7.provider_git import GitContext7Provider
from services.context7.provider_http import HttpContext7Provider
from services.context7.provider_mock import MockContext7Provider
from services.context7.provider_pgvector import PgVectorContext7Provider

_BACKEND_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "backend",
    ".env",
)
load_dotenv(_BACKEND_ENV, override=False)


def _parse_top_k(default: int = 2) -> int:
    raw = (os.getenv("CONTEXT7_TOP_K") or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _parse_min_score() -> Optional[float]:
    raw = (os.getenv("CONTEXT7_MIN_SCORE") or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def get_context7_top_k(default: int = 2) -> int:
    return _parse_top_k(default)


def get_context7_min_score() -> Optional[float]:
    return _parse_min_score()


def get_context7_provider(name: Optional[str] = None) -> Context7Provider:
    """Resolve provider: mock (default) | http | git | pgvector."""
    provider_name = (name or os.getenv("CONTEXT7_PROVIDER") or "mock").strip().lower()
    if provider_name in {"", "mock", "gemini"}:
        return MockContext7Provider()
    if provider_name == "http":
        return HttpContext7Provider(min_score=get_context7_min_score())
    if provider_name in {"git", "chroma", "local"}:
        return GitContext7Provider(min_score=get_context7_min_score())
    if provider_name in {"pgvector", "postgres", "pg"}:
        return PgVectorContext7Provider()
    raise ValueError(
        f"CONTEXT7_PROVIDER desconhecido: {provider_name!r}. "
        "Use mock|http|git|pgvector."
    )


__all__ = [
    "get_context7_provider",
    "get_context7_top_k",
    "get_context7_min_score",
]
