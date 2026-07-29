"""Integracao semantica real (sentence-transformers) — marcar como slow."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.context7.embeddings import DEFAULT_EMBEDDING_MODEL  # noqa: E402
from services.context7.provider_git import GitContext7Provider  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "docs_repo"


def _assert_top_doc(result, expected_rel: str, expected_tipo: str) -> None:
    assert result.source == "context7_git", result.meta
    assert result.hits, "sem hits"
    top = result.hits[0]
    assert top.url == expected_rel, (
        f"esperado top={expected_rel}, veio={top.url} "
        f"(titulo={top.titulo!r}, score={top.score}, "
        f"todos={[ (h.url, round(h.score, 3)) for h in result.hits ]})"
    )
    assert top.tipo == expected_tipo
    assert top.titulo and ">" in top.titulo  # breadcrumb hierarquico
    if len(result.hits) > 1:
        assert top.score >= result.hits[1].score
        # margem semantica: top deve se destacar do segundo
        assert top.score - result.hits[1].score >= 0.02, (
            f"margem insuficiente: {[ (h.url, round(h.score, 3)) for h in result.hits ]}"
        )


@pytest.mark.slow
def test_semantic_search_payment_flow_returns_checkout(tmp_path: Path):
    pytest.importorskip("sentence_transformers")
    index_dir = tmp_path / "index_semantic"
    provider = GitContext7Provider(
        repo_path=str(FIXTURE_REPO),
        index_dir=str(index_dir),
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        use_fallback_on_error=False,
    )
    query = "como funciona o fluxo de pagamento"
    result = provider.search(
        [query],
        top_k=4,
        challenge=query,
    )
    _assert_top_doc(result, "prd/prd-checkout.md", "PRD")


@pytest.mark.slow
def test_semantic_search_login_architecture_returns_auth(tmp_path: Path):
    pytest.importorskip("sentence_transformers")
    index_dir = tmp_path / "index_semantic_auth"
    provider = GitContext7Provider(
        repo_path=str(FIXTURE_REPO),
        index_dir=str(index_dir),
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        use_fallback_on_error=False,
    )
    query = "arquitetura de login e sessao"
    result = provider.search(
        [query],
        top_k=4,
        challenge=query,
    )
    _assert_top_doc(result, "sdd/sdd-auth.md", "SDD")
