"""Provider HTTP genérico: POST {query, top_k, filtros?} -> {hits: [...]}."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from services.context7.fallback import (
    build_fallback_result,
    extract_keywords_from_text,
)
from services.context7.provider_base import (
    Context7SearchResult,
    Hit,
    apply_min_score,
    hit_from_mapping,
)


class Context7HttpError(RuntimeError):
    """Falha ao consultar a API context7."""


class HttpContext7Provider:
    """Cliente REST configurável via CONTEXT7_API_URL / CONTEXT7_API_KEY."""

    name = "http"

    def __init__(
        self,
        *,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        min_score: Optional[float] = None,
        use_fallback_on_error: bool = True,
    ) -> None:
        self.api_url = (
            api_url if api_url is not None else os.getenv("CONTEXT7_API_URL", "")
        ).strip()
        self.api_key = (
            api_key if api_key is not None else os.getenv("CONTEXT7_API_KEY", "")
        ).strip()
        self.timeout = timeout
        self.min_score = min_score
        self.use_fallback_on_error = use_fallback_on_error

    def search(
        self,
        keywords: list[str],
        *,
        top_k: int = 2,
        filtros: Optional[dict[str, Any]] = None,
        challenge: str = "",
    ) -> Context7SearchResult:
        kws = list(keywords) if keywords else extract_keywords_from_text(challenge)
        query = " ".join(kws).strip() or (challenge or "").strip()
        if not query:
            query = "context7"

        try:
            hits = self._request_hits(query=query, top_k=top_k, filtros=filtros)
            hits = apply_min_score(hits, self.min_score)
            if not hits:
                raise Context7HttpError("API retornou zero hits")
            return Context7SearchResult(
                hits=hits[: max(1, top_k)],
                keywords=kws,
                source="context7_http",
                meta={"api_url": self.api_url, "query": query},
            )
        except Exception as exc:
            if not self.use_fallback_on_error:
                raise
            return build_fallback_result(
                challenge or query,
                reason=f"http_error: {exc}",
                source="context7_http_fallback",
                keywords=kws,
                top_k=top_k,
            )

    def _request_hits(
        self,
        *,
        query: str,
        top_k: int,
        filtros: Optional[dict[str, Any]],
    ) -> list[Hit]:
        if not self.api_url:
            raise Context7HttpError("CONTEXT7_API_URL nao configurada")

        payload: dict[str, Any] = {"query": query, "top_k": top_k}
        if filtros:
            payload["filtros"] = filtros

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.api_url, json=payload, headers=headers)

        if response.status_code >= 400:
            raise Context7HttpError(
                f"HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            body = response.json()
        except Exception as exc:
            raise Context7HttpError(f"JSON invalido: {exc}") from exc

        raw_hits = body.get("hits") if isinstance(body, dict) else None
        if raw_hits is None and isinstance(body, dict):
            raw_hits = body.get("context7_hits")
        if not isinstance(raw_hits, list):
            raise Context7HttpError("Resposta sem lista hits/context7_hits")

        hits: list[Hit] = []
        for item in raw_hits:
            if isinstance(item, dict):
                hits.append(hit_from_mapping(item))
        return hits
