"""Provider context7 baseado em repo Git + ChromaDB local."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from services.context7.fallback import (
    build_fallback_result,
    extract_keywords_from_text,
)
from services.context7.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    resolve_embedding_model_name,
)
from services.context7.git_indexer import GitDocsIndexer
from services.context7.provider_base import (
    Context7SearchResult,
    Hit,
    apply_min_score,
    clamp_score,
    normalize_tipo,
)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _truncate(text: str, limit: int = 600) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class GitContext7Provider:
    """Busca vetorial local em PRDs/SDDs Markdown de um repo já clonado."""

    name = "git"

    def __init__(
        self,
        *,
        repo_path: Optional[str] = None,
        index_dir: Optional[str] = None,
        docs_glob: Optional[str] = None,
        embedding_model: Optional[str] = None,
        min_score: Optional[float] = None,
        use_fallback_on_error: bool = True,
        indexer: Optional[GitDocsIndexer] = None,
    ) -> None:
        self.repo_path = repo_path if repo_path is not None else _env("CONTEXT7_GIT_REPO_PATH")
        self.docs_glob = docs_glob if docs_glob is not None else (
            _env("CONTEXT7_GIT_DOCS_GLOB") or "**/*.md"
        )
        self.embedding_model = resolve_embedding_model_name(
            embedding_model
            if embedding_model is not None
            else (_env("CONTEXT7_EMBEDDING_MODEL") or None)
        )
        configured_index = index_dir if index_dir is not None else _env("CONTEXT7_INDEX_DIR")
        if configured_index:
            self.index_dir = configured_index
        elif self.repo_path:
            self.index_dir = str(Path(self.repo_path) / ".context7_index")
        else:
            self.index_dir = ""
        self.min_score = min_score
        self.use_fallback_on_error = use_fallback_on_error
        self._indexer = indexer

    def _get_indexer(self) -> GitDocsIndexer:
        if self._indexer is not None:
            return self._indexer
        if not self.repo_path:
            raise FileNotFoundError("CONTEXT7_GIT_REPO_PATH nao configurada")
        if not self.index_dir:
            raise FileNotFoundError("CONTEXT7_INDEX_DIR nao configurada")
        self._indexer = GitDocsIndexer(
            repo_path=self.repo_path,
            index_dir=self.index_dir,
            docs_glob=self.docs_glob,
            embedding_model=self.embedding_model or DEFAULT_EMBEDDING_MODEL,
        )
        return self._indexer

    def search(
        self,
        keywords: list[str],
        *,
        top_k: int = 2,
        filtros: Optional[dict[str, Any]] = None,
        challenge: str = "",
    ) -> Context7SearchResult:
        kws = list(keywords) if keywords else extract_keywords_from_text(challenge)
        query = " ".join(kws).strip() or (challenge or "").strip() or "context7"

        try:
            indexer = self._get_indexer()
            sync_stats = indexer.sync()
            tipo = None
            if isinstance(filtros, dict):
                tipo = filtros.get("tipo") or filtros.get("type")
            raw_hits = indexer.query(query, top_k=top_k, tipo=tipo)
            hits = [self._to_hit(item) for item in raw_hits]
            hits = apply_min_score(hits, self.min_score)
            if not hits:
                raise RuntimeError("Nenhum hit no indice context7 git/chroma")
            return Context7SearchResult(
                hits=hits[: max(1, top_k)],
                keywords=kws,
                source="context7_git",
                meta={
                    "provider": "git",
                    "repo_path": self.repo_path,
                    "sync": {
                        "scanned": sync_stats.scanned,
                        "unchanged": sync_stats.unchanged,
                        "upserted": sync_stats.upserted,
                        "removed": sync_stats.removed,
                        "reindexed_files": list(sync_stats.reindexed_files),
                    },
                    "query": query,
                },
            )
        except Exception as exc:
            if not self.use_fallback_on_error:
                raise
            return build_fallback_result(
                challenge or query,
                reason=f"git_error: {exc}",
                source="context7_git_fallback",
                keywords=kws,
                top_k=top_k,
            )

    def _to_hit(self, item: dict[str, Any]) -> Hit:
        meta = item.get("metadata") or {}
        breadcrumb = str(meta.get("breadcrumb") or "").strip()
        doc_title = str(meta.get("doc_title") or "").strip()
        heading = str(meta.get("heading") or "").strip()
        titulo = breadcrumb or heading or doc_title or "Documento"
        document = str(item.get("document") or "")
        # remove breadcrumb duplicado do início do documento se presente
        trecho = document
        if breadcrumb and trecho.startswith(breadcrumb):
            trecho = trecho[len(breadcrumb) :].lstrip("\n").strip()
        trecho = trecho or document
        rel = str(meta.get("rel_path") or "").strip() or None
        return Hit(
            titulo=titulo,
            tipo=normalize_tipo(meta.get("tipo")),
            resumo=_truncate(trecho, 600),
            score=clamp_score(item.get("score"), default=0.5),
            url=rel,
            id=str(item.get("id") or "") or None,
            trecho=_truncate(trecho, 1200),
        )
