"""Embeddings context7: sentence-transformers (default) + hash (testes rápidos)."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HASH_MODEL_ALIASES = frozenset({"hash", "local-hash", "deterministic"})

_model_cache: dict[str, object] = {}
_model_lock = threading.Lock()


def resolve_embedding_model_name(model_name: Optional[str] = None) -> str:
    """Nome canônico do modelo (default MiniLM; hash só se explícito)."""
    if model_name is not None:
        raw = model_name.strip()
    else:
        raw = (os.getenv("CONTEXT7_EMBEDDING_MODEL") or "").strip()
    if not raw:
        return DEFAULT_EMBEDDING_MODEL
    if raw.lower() in HASH_MODEL_ALIASES:
        return "hash"
    return raw


def is_hash_model(model_name: Optional[str]) -> bool:
    return resolve_embedding_model_name(model_name) == "hash"


def get_sentence_transformer(model_name: str):
    """Carrega SentenceTransformer uma vez por processo (singleton por nome)."""
    key = model_name.strip()
    with _model_lock:
        cached = _model_cache.get(key)
        if cached is not None:
            return cached
        from sentence_transformers import SentenceTransformer

        logger.info("context7: carregando modelo de embedding %s", key)
        model = SentenceTransformer(key)
        _model_cache[key] = model
        return model


def embed(texts: list[str], model_name: Optional[str] = None) -> list[list[float]]:
    """Gera embeddings para uma lista de textos com o modelo configurado."""
    name = resolve_embedding_model_name(model_name)
    fn = build_embedding_function(name)
    return fn(texts)


class DeterministicHashEmbedding:
    """Embedding local determinístico — só para testes unitários rápidos."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.model_name = "hash"

    def name(self) -> str:
        return "context7_hash_embedding"

    def is_legacy(self) -> bool:
        return True

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in input]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9]+", (text or "").lower())
        if not tokens:
            tokens = ["empty"]
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedding:
    """Wrapper Chroma-compatible com cache singleton do modelo."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = resolve_embedding_model_name(model_name)
        self._model = None

    def name(self) -> str:
        return f"context7_st:{self.model_name}"

    def is_legacy(self) -> bool:
        return True

    def _ensure_model(self):
        if self._model is None:
            self._model = get_sentence_transformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        vectors = model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [list(map(float, row)) for row in vectors]

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return self.embed(list(input))


def build_embedding_function(model_name: Optional[str] = None):
    """
    Resolve embedder:
    - hash -> DeterministicHashEmbedding (testes)
    - demais -> SentenceTransformerEmbedding (default MiniLM)
    """
    name = resolve_embedding_model_name(model_name)
    if name == "hash":
        return DeterministicHashEmbedding()
    return SentenceTransformerEmbedding(model_name=name)
