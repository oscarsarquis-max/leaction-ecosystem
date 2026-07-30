"""Testes da LLMFactory e resolução de provedor."""

from __future__ import annotations

import os

import pytest

from services.llm.factory import LLMFactory, resolve_provider_name
from services.llm.google_provider import GoogleProvider
from services.llm.ollama_provider import OllamaProvider


@pytest.fixture(autouse=True)
def _reset_factory():
    LLMFactory.reset()
    yield
    LLMFactory.reset()


def test_resolve_provider_default_google(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert resolve_provider_name() == "google"


def test_resolve_provider_aliases(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert resolve_provider_name() == "google"
    monkeypatch.setenv("LLM_PROVIDER", "local")
    assert resolve_provider_name() == "ollama"
    monkeypatch.setenv("LLM_PROVIDER", "OLLAMA")
    assert resolve_provider_name() == "ollama"


def test_factory_returns_google(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google")
    provider = LLMFactory.get_provider()
    assert isinstance(provider, GoogleProvider)
    # singleton
    assert LLMFactory.get_provider() is provider


def test_factory_returns_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("LLM_MODEL", "llama3")
    LLMFactory.reset()
    provider = LLMFactory.get_provider()
    assert isinstance(provider, OllamaProvider)


def test_factory_switches_provider_after_reset(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google")
    a = LLMFactory.get_provider()
    assert isinstance(a, GoogleProvider)

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    LLMFactory.reset()
    b = LLMFactory.get_provider()
    assert isinstance(b, OllamaProvider)
    assert a is not b


def test_factory_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    LLMFactory.reset()
    with pytest.raises(ValueError, match="desconhecido"):
        LLMFactory.get_provider()
