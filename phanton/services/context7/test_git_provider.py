"""Testes: chunking hierárquico + indexer git/chroma + provider_git."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.context7.chunking import chunk_markdown  # noqa: E402
from services.context7.git_indexer import (  # noqa: E402
    DeterministicHashEmbedding,
    GitDocsIndexer,
)
from services.context7.provider_git import GitContext7Provider  # noqa: E402


SAMPLE_PRD = """---
title: PRD Plataforma Edu
tipo: PRD
---

# Visao Geral

Texto da visao do produto educacional.

## Personas

Descricao das personas principais.

### Gestor Escolar

Jornada do gestor com RBAC e onboarding.

## Metricas

OKRs e criterios de aceite do MVP.
"""


SAMPLE_SDD = """---
title: SDD Hub API
tipo: SDD
---

# Arquitetura

Camadas frontend e API.

## Stack

Vite, Flask e Postgres.
"""


def _write_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "docs_repo"
    (repo / "prd").mkdir(parents=True)
    (repo / "sdd").mkdir(parents=True)
    (repo / "prd" / "edu-prd.md").write_text(SAMPLE_PRD, encoding="utf-8")
    (repo / "sdd" / "hub-sdd.md").write_text(SAMPLE_SDD, encoding="utf-8")
    return repo


def test_chunking_preserves_three_level_breadcrumb():
    chunks = chunk_markdown(SAMPLE_PRD, rel_path="prd/edu-prd.md")
    assert chunks
    crumbs = [c.breadcrumb for c in chunks]
    # deve existir trilha com 3 niveis
    assert any(c.count(">") >= 2 for c in crumbs), crumbs
    gestor = next(c for c in chunks if "Gestor Escolar" in c.breadcrumb)
    assert "PRD Plataforma Edu" in gestor.breadcrumb or "Visao Geral" in gestor.breadcrumb
    assert "Personas" in gestor.breadcrumb
    assert "Gestor Escolar" in gestor.breadcrumb
    assert gestor.tipo == "PRD"


def test_sync_second_call_does_not_reprocess(tmp_path: Path):
    repo = _write_repo(tmp_path)
    index_dir = tmp_path / "index"
    indexer = GitDocsIndexer(
        repo_path=repo,
        index_dir=index_dir,
        embedding_model="hash",
        embedding_function=DeterministicHashEmbedding(dim=64),
    )
    first = indexer.sync()
    assert first.upserted == 2
    assert first.unchanged == 0

    second = indexer.sync()
    assert second.upserted == 0
    assert second.removed == 0
    assert second.unchanged == 2
    assert second.reindexed_files == []
    assert indexer._manifest.embedding_model == "hash"


def test_sync_reindexes_only_changed_file(tmp_path: Path):
    repo = _write_repo(tmp_path)
    index_dir = tmp_path / "index"
    indexer = GitDocsIndexer(
        repo_path=repo,
        index_dir=index_dir,
        embedding_model="hash",
        embedding_function=DeterministicHashEmbedding(dim=64),
    )
    indexer.sync()

    target = repo / "prd" / "edu-prd.md"
    target.write_text(
        SAMPLE_PRD + "\n\n## Nova Secao\n\nConteudo novo para forcar rehash.\n",
        encoding="utf-8",
    )

    stats = indexer.sync()
    assert stats.upserted == 1
    assert stats.unchanged == 1
    assert stats.reindexed_files == ["prd/edu-prd.md"]


def test_sync_reindexes_all_when_embedding_model_changes(tmp_path: Path, caplog):
    import logging

    repo = _write_repo(tmp_path)
    index_dir = tmp_path / "index"
    first = GitDocsIndexer(
        repo_path=repo,
        index_dir=index_dir,
        embedding_model="test-model-a",
        embedding_function=DeterministicHashEmbedding(dim=64),
    )
    first_stats = first.sync()
    assert first_stats.upserted == 2
    assert first._manifest.embedding_model == "test-model-a"

    with caplog.at_level(logging.WARNING, logger="services.context7.git_indexer"):
        second = GitDocsIndexer(
            repo_path=repo,
            index_dir=index_dir,
            embedding_model="test-model-b",
            embedding_function=DeterministicHashEmbedding(dim=64),
        )
        stats = second.sync()

    assert stats.model_changed is True
    assert stats.upserted == 2
    assert stats.unchanged == 0
    assert second._manifest.embedding_model == "test-model-b"
    assert any("modelo de embedding mudou" in r.message for r in caplog.records)


def test_search_respects_tipo_filter(tmp_path: Path):
    repo = _write_repo(tmp_path)
    index_dir = tmp_path / "index"
    indexer = GitDocsIndexer(
        repo_path=repo,
        index_dir=index_dir,
        embedding_model="hash",
        embedding_function=DeterministicHashEmbedding(dim=64),
    )
    provider = GitContext7Provider(
        repo_path=str(repo),
        index_dir=str(index_dir),
        embedding_model="hash",
        use_fallback_on_error=False,
        indexer=indexer,
    )
    result = provider.search(
        ["arquitetura", "stack", "Postgres"],
        top_k=2,
        filtros={"tipo": "SDD"},
        challenge="arquitetura API Postgres",
    )
    assert result.source == "context7_git"
    assert result.hits
    assert all(h.tipo == "SDD" for h in result.hits)
    assert all(h.titulo and h.resumo for h in result.hits)


def test_search_fallback_when_repo_missing(tmp_path: Path):
    provider = GitContext7Provider(
        repo_path=str(tmp_path / "does-not-exist"),
        index_dir=str(tmp_path / "index"),
        embedding_model="hash",
        use_fallback_on_error=True,
    )
    result = provider.search(
        ["educacao"],
        top_k=2,
        challenge="plataforma educacao",
    )
    assert result.source == "context7_git_fallback"
    assert result.meta.get("fallback") is True
    assert len(result.hits) >= 1
    for hit in result.hits:
        assert hit.titulo and hit.tipo and hit.resumo
        assert 0.0 <= hit.score <= 1.0
