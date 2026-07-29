"""Stub pgvector — busca vetorial ainda nao implementada."""

from __future__ import annotations

import os
from typing import Any, Optional

from services.context7.provider_base import Context7SearchResult


class PgVectorContext7Provider:
    """Esqueleto para origem Postgres/pgvector (CONTEXT7_DB_DSN)."""

    name = "pgvector"

    def __init__(self, *, dsn: Optional[str] = None) -> None:
        self.dsn = (dsn if dsn is not None else os.getenv("CONTEXT7_DB_DSN", "")).strip()

    def search(
        self,
        keywords: list[str],
        *,
        top_k: int = 2,
        filtros: Optional[dict[str, Any]] = None,
        challenge: str = "",
    ) -> Context7SearchResult:
        # TODO: embedding + SELECT ... ORDER BY embedding <=> query_vec LIMIT top_k
        raise NotImplementedError(
            "provider_pgvector ainda nao implementado. "
            "Configure CONTEXT7_PROVIDER=mock|http ou implemente a busca vetorial "
            f"(dsn={'set' if self.dsn else 'missing'}, top_k={top_k}, "
            f"keywords={len(keywords)}, challenge_len={len(challenge or '')}, "
            f"filtros={filtros})."
        )
