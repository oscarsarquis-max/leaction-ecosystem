"""Testes de runtime (generate_content via factory) e json_utils."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.llm.base_provider import LLMResult
from services.llm.factory import LLMFactory
from services.llm.json_utils import extract_json_payload
from services.llm.runtime import generate_content


@pytest.fixture(autouse=True)
def _reset_factory():
    LLMFactory.reset()
    yield
    LLMFactory.reset()


def test_extract_json_strips_markdown_fence():
    raw = 'Claro!\n```json\n{"a": 1}\n```\n'
    assert extract_json_payload(raw) == {"a": 1}


def test_runtime_generate_content_delegates_to_factory():
    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(
        return_value=LLMResult(text="ok", meta={"provider": "mock", "model": "x"})
    )

    with patch.object(LLMFactory, "get_provider", return_value=mock_provider):
        text, meta = generate_content(
            "hello",
            enable_google_search=True,
            response_json=True,
            temperature=0.1,
        )

    assert text == "ok"
    assert meta["provider"] == "mock"
    mock_provider.generate.assert_awaited_once()
    kwargs = mock_provider.generate.await_args.kwargs
    assert kwargs["enable_web_search"] is True
    assert kwargs["response_json"] is True
    assert kwargs["temperature"] == 0.1
