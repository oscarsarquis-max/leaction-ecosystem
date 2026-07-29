"""Indexador incremental: repo Git (md) -> ChromaDB + manifest de hashes."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from services.context7.chunking import MarkdownChunk, chunk_markdown
from services.context7.embeddings import (
    DeterministicHashEmbedding,
    build_embedding_function,
    resolve_embedding_model_name,
)
from services.context7.manifest import FileManifestEntry, IndexManifest

logger = logging.getLogger(__name__)

COLLECTION_NAME = "context7_docs"
DEFAULT_DOCS_GLOB = "**/*.md"

# reexport para testes/compat
__all__ = [
    "COLLECTION_NAME",
    "DEFAULT_DOCS_GLOB",
    "DeterministicHashEmbedding",
    "GitDocsIndexer",
    "SyncStats",
    "build_embedding_function",
    "sha256_text",
]


@dataclass
class SyncStats:
    scanned: int = 0
    unchanged: int = 0
    upserted: int = 0
    removed: int = 0
    model_changed: bool = False
    reindexed_files: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.upserted > 0 or self.removed > 0 or self.model_changed


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_chunk_id(rel_path: str, index: int, content_hash: str) -> str:
    """ID estável e compatível com Chroma (<= limpeza de chars)."""
    digest = hashlib.sha1(
        f"{rel_path}|{index}|{content_hash}".encode("utf-8")
    ).hexdigest()[:24]
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", rel_path)[:48]
    return f"{slug}__{index}__{digest}"


class GitDocsIndexer:
    """Walk do repo + upsert incremental no Chroma."""

    def __init__(
        self,
        *,
        repo_path: str | Path,
        index_dir: str | Path,
        docs_glob: str = DEFAULT_DOCS_GLOB,
        embedding_model: Optional[str] = None,
        embedding_function: Any = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.index_dir = Path(index_dir).resolve()
        self.docs_glob = docs_glob or DEFAULT_DOCS_GLOB
        self.collection_name = collection_name
        self.embedding_model = resolve_embedding_model_name(embedding_model)
        self._embedding = embedding_function or build_embedding_function(
            self.embedding_model
        )
        self._manifest = IndexManifest(self.index_dir / "manifest.json")
        self._client = None
        self._collection = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        import chromadb

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.index_dir / "chroma"))
        return self._client

    def _ensure_collection(self, *, recreate: bool = False):
        client = self._ensure_client()
        if recreate:
            try:
                client.delete_collection(self.collection_name)
            except Exception:
                pass
            self._collection = None

        if self._collection is not None:
            return self._collection

        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self._embedding,
        )
        return self._collection

    def _invalidate_for_model_change(self) -> None:
        """Descarta índice antigo quando o modelo de embedding muda."""
        logger.warning(
            "context7: modelo de embedding mudou, reindexando tudo "
            "(antes=%r agora=%r)",
            self._manifest.embedding_model,
            self.embedding_model,
        )
        self._manifest.clear_files()
        self._manifest.embedding_model = self.embedding_model
        self._ensure_collection(recreate=True)

    def list_markdown_files(self) -> list[Path]:
        if not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repo context7 inacessivel: {self.repo_path}")
        files = [
            p
            for p in self.repo_path.glob(self.docs_glob)
            if p.is_file() and p.suffix.lower() == ".md"
        ]
        index_resolved = self.index_dir.resolve()
        out: list[Path] = []
        for p in files:
            try:
                p.resolve().relative_to(index_resolved)
                continue
            except ValueError:
                out.append(p)
        return sorted(out, key=lambda x: str(x).lower())

    def rel_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo_path).as_posix()

    def sync(self) -> SyncStats:
        """Reindexa só arquivos cujo hash mudou; remove órfãos.

        Se o modelo de embedding no manifest divergir do atual, reindexa tudo.
        """
        stats = SyncStats()
        registered = self._manifest.embedding_model
        if registered and registered != self.embedding_model:
            self._invalidate_for_model_change()
            stats.model_changed = True
        elif not registered:
            self._manifest.embedding_model = self.embedding_model

        collection = self._ensure_collection()
        files = self.list_markdown_files()
        stats.scanned = len(files)
        seen: set[str] = set()
        force_all = stats.model_changed

        for path in files:
            rel = self.rel_path(path)
            seen.add(rel)
            content = path.read_text(encoding="utf-8", errors="replace")
            content_hash = sha256_text(content)
            prev = self._manifest.get(rel)
            if (
                not force_all
                and prev
                and prev.content_hash == content_hash
                and prev.chunk_ids
            ):
                stats.unchanged += 1
                continue

            chunks = chunk_markdown(content, rel_path=rel)
            chunk_ids = [
                _safe_chunk_id(rel, i, content_hash) for i in range(len(chunks))
            ]
            documents = [c.indexed_text for c in chunks]
            metadatas = [self._chunk_metadata(rel, c, content_hash) for c in chunks]

            if prev and prev.chunk_ids and not force_all:
                try:
                    collection.delete(ids=prev.chunk_ids)
                except Exception:
                    pass

            if chunk_ids:
                collection.upsert(
                    ids=chunk_ids,
                    documents=documents,
                    metadatas=metadatas,
                )

            self._manifest.set(
                rel,
                FileManifestEntry(content_hash=content_hash, chunk_ids=chunk_ids),
            )
            stats.upserted += 1
            stats.reindexed_files.append(rel)

        for old_rel in sorted(self._manifest.paths() - seen):
            entry = self._manifest.pop(old_rel)
            if entry and entry.chunk_ids and not force_all:
                try:
                    collection.delete(ids=entry.chunk_ids)
                except Exception:
                    pass
            stats.removed += 1

        self._manifest.embedding_model = self.embedding_model
        self._manifest.save()
        return stats

    def _chunk_metadata(
        self,
        rel: str,
        chunk: MarkdownChunk,
        content_hash: str,
    ) -> dict[str, Any]:
        return {
            "rel_path": rel,
            "tipo": chunk.tipo or "DOC",
            "doc_title": chunk.doc_title,
            "heading": chunk.heading,
            "breadcrumb": chunk.breadcrumb,
            "level": chunk.level,
            "content_hash": content_hash,
        }

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 2,
        tipo: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Consulta a collection; retorna dicts com document/metadata/distance."""
        collection = self._ensure_collection()
        where = None
        if tipo:
            where = {"tipo": str(tipo).strip().upper()}

        kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": max(1, top_k),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        raw = collection.query(**kwargs)
        results: list[dict[str, Any]] = []
        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        for i, doc_id in enumerate(ids):
            distance = (
                float(dists[i]) if i < len(dists) and dists[i] is not None else 1.0
            )
            score = max(0.0, min(1.0, 1.0 - distance))
            meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
            text = docs[i] if i < len(docs) else ""
            results.append(
                {
                    "id": doc_id,
                    "document": text or "",
                    "metadata": meta,
                    "distance": distance,
                    "score": score,
                }
            )
        return results
