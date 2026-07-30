"""Testes do OllamaProvider com httpx mockado."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm.ollama_provider import OllamaProvider


def test_ollama_generate_posts_payload():
    provider = OllamaProvider(
        base_url="http://ollama.test:11434",
        model="llama3",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "ola mundo", "model": "llama3"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    async def _run():
        with patch(
            "services.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client
        ):
            return await provider.generate(
                "ping",
                temperature=0.2,
                max_output_tokens=128,
            )

    result = asyncio.run(_run())

    assert result.text == "ola mundo"
    assert result.meta["provider"] == "ollama"
    assert result.meta["model"] == "llama3"
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == "http://ollama.test:11434/api/generate"
    body = kwargs["json"]
    assert body["model"] == "llama3"
    assert body["prompt"] == "ping"
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0.2
    assert body["options"]["num_predict"] == 128


def test_ollama_forces_json_in_system_when_response_json():
    provider = OllamaProvider(base_url="http://ollama.test", model="mistral")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": '{"ok": true}'}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    async def _run():
        with patch(
            "services.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client
        ):
            return await provider.generate(
                "gere json",
                system_instruction="Seja breve.",
                response_json=True,
            )

    result = asyncio.run(_run())

    body = mock_client.post.await_args.kwargs["json"]
    assert body["format"] == "json"
    assert "JSON" in body["system"]
    assert "Seja breve." in body["system"]
    assert result.text == '{"ok": true}'


def test_ollama_web_search_degrades_without_raising():
    provider = OllamaProvider(base_url="http://ollama.test", model="llama3")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "sem search"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    async def _run():
        with patch(
            "services.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client
        ):
            return await provider.generate("q", enable_web_search=True)

    result = asyncio.run(_run())
    assert result.meta.get("web_search_unsupported") is True
    assert result.text == "sem search"


def test_ollama_empty_response_raises():
    provider = OllamaProvider(base_url="http://ollama.test", model="llama3")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "  "}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    async def _run():
        with patch(
            "services.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client
        ):
            return await provider.generate("q")

    with pytest.raises(RuntimeError, match="texto vazio"):
        asyncio.run(_run())
