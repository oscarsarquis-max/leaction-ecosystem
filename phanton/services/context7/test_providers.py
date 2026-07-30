"""Testes dos providers context7 (contrato titulo/tipo/resumo/score)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.context7.fallback import build_fallback_result  # noqa: E402
from services.context7.provider_base import Hit  # noqa: E402
from services.context7.provider_http import HttpContext7Provider  # noqa: E402
from services.context7.provider_mock import MockContext7Provider  # noqa: E402
from services.context7.provider_pgvector import PgVectorContext7Provider  # noqa: E402


REQUIRED_HIT_KEYS = ("titulo", "tipo", "resumo", "score")


def _assert_contract_hits(hits: list[dict]) -> None:
    assert hits, "esperado ao menos 1 hit"
    for hit in hits:
        for key in REQUIRED_HIT_KEYS:
            assert key in hit, f"hit sem campo obrigatorio: {key}"
        assert isinstance(hit["titulo"], str) and hit["titulo"].strip()
        assert isinstance(hit["tipo"], str) and hit["tipo"].strip()
        assert isinstance(hit["resumo"], str)
        assert isinstance(hit["score"], (int, float))
        assert 0.0 <= float(hit["score"]) <= 1.0


def test_fallback_result_matches_artifact_contract():
    result = build_fallback_result("plataforma educacao SaaS MVP", reason="unit")
    data = {
        "search_keywords": result.keywords,
        "context7_hits": result.hits_as_dicts(),
        "source": result.source,
    }
    assert data["search_keywords"]
    assert data["source"].startswith("context7_")
    _assert_contract_hits(data["context7_hits"])


def test_mock_provider_contract_with_stubbed_llm():
    fake_json = """
    {
      "search_keywords": ["SaaS", "educacao"],
      "context7_hits": [
        {"titulo": "PRD X", "tipo": "PRD", "resumo": "regras", "score": 0.9},
        {"titulo": "SDD Y", "tipo": "SDD", "resumo": "arch", "score": 0.85}
      ]
    }
    """

    from services.llm.base_provider import LLMResult
    from services.llm.factory import LLMFactory

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(
        return_value=LLMResult(text=fake_json, meta={"model": "stub", "provider": "mock"})
    )

    with patch.object(LLMFactory, "get_provider", return_value=mock_provider):
        result = MockContext7Provider().search(
            ["SaaS"], top_k=2, challenge="app educacao"
        )

    assert result.source == "context7_mock"
    assert result.keywords == ["SaaS", "educacao"]
    _assert_contract_hits(result.hits_as_dicts())


def test_http_provider_contract_with_mocked_response():
    payload = {
        "hits": [
            {
                "titulo": "PRD real",
                "tipo": "PRD",
                "resumo": "jornadas",
                "score": 0.91,
                "url": "https://example/prd",
                "id": "prd-1",
            },
            {
                "titulo": "SDD real",
                "tipo": "SDD",
                "resumo": "stack",
                "score": 0.88,
            },
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_response.text = "{}"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_response

    with patch("services.context7.provider_http.httpx.Client", return_value=mock_client):
        provider = HttpContext7Provider(
            api_url="https://context7.example/search",
            api_key="test-key",
            use_fallback_on_error=False,
        )
        result = provider.search(["SaaS", "MVP"], top_k=2, challenge="produto B2B")

    assert result.source == "context7_http"
    hits = result.hits_as_dicts()
    _assert_contract_hits(hits)
    assert hits[0].get("url") == "https://example/prd"
    assert hits[0].get("id") == "prd-1"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["json"]["query"]
    assert call_kwargs.kwargs["json"]["top_k"] == 2


def test_http_provider_falls_back_when_api_fails():
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.side_effect = httpx.ConnectError("boom")

    with patch("services.context7.provider_http.httpx.Client", return_value=mock_client):
        provider = HttpContext7Provider(
            api_url="https://context7.example/search",
            use_fallback_on_error=True,
        )
        result = provider.search(["educacao"], top_k=2, challenge="plataforma educacao")

    assert result.source == "context7_http_fallback"
    assert result.meta.get("fallback") is True
    _assert_contract_hits(result.hits_as_dicts())


def test_pgvector_provider_is_stub():
    provider = PgVectorContext7Provider(dsn="")
    with pytest.raises(NotImplementedError):
        provider.search(["kw"], top_k=2, challenge="x")


def test_hit_to_dict_optional_fields():
    hit = Hit(titulo="T", tipo="DOC", resumo="r", score=0.5, url="u", id="1", trecho="t")
    d = hit.to_dict()
    assert d["url"] == "u" and d["id"] == "1" and d["trecho"] == "t"
