"""Testes: parser JSON com preâmbulo + generate_sdd sem duplicar PRD."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.llm.json_utils import extract_json_payload  # noqa: E402
from services.phase_sdd import (  # noqa: E402
    _fallback_sdd,
    _generate_sdd_safe,
    _normalize_sdd,
    _strip_prd_appendix,
)


def test_extract_json_with_ascii_preamble():
    raw = """
   +-----+     +-----+
   | API | --> | DB  |
   +-----+     +-----+

{"sdd_markdown": "# SDD\\n\\n## Stack\\nPython", "build_order": [{"modulo": "api", "depende_de": [], "escopo": "REST"}]}
"""
    parsed = extract_json_payload(raw)
    assert parsed["sdd_markdown"].startswith("# SDD")
    assert parsed["build_order"][0]["modulo"] == "api"


def test_extract_json_with_mermaid_preamble():
    raw = """
sequenceDiagram
  User->>API: login
  API->>DB: query

{"sdd_markdown": "# ok", "build_order": []}
"""
    parsed = extract_json_payload(raw)
    assert parsed["sdd_markdown"] == "# ok"
    assert parsed["build_order"] == []


def test_fallback_does_not_embed_full_prd():
    inputs = {
        "generate_prd": {
            "prd_markdown": "# PRD enorme\n" + ("regra " * 500),
        }
    }
    out = _fallback_sdd(
        inputs,
        {"name": "fin-saas"},
        reason="teste",
        prd_phase_id="generate_prd",
    )
    assert "Ver artefato da fase `generate_prd`" in out["sdd_markdown"]
    assert "regra regra regra" not in out["sdd_markdown"]
    assert out["build_order"] == []


def test_strip_prd_appendix_removes_pasted_block():
    md = """# SDD

## Stack
Python

## Referência ao PRD
# PRD completo colado
- item 1
- item 2
"""
    cleaned = _strip_prd_appendix(md)
    assert "Referência ao PRD" not in cleaned
    assert "PRD completo" not in cleaned
    assert "## Stack" in cleaned


def test_generate_sdd_safe_uses_schema_and_returns_build_order():
    fake_json = {
        "sdd_markdown": (
            "# SDD Financeiro\n\n## Stack Tecnológica\nPython\n\n"
            "## Arquitetura do Sistema\nAPI + workers\n\n"
            "## Modelo de Dados\nledger_entries\n\n"
            "## Contratos de API / Componentes\nPOST /entries\n"
        ),
        "build_order": [
            {"modulo": "ledger-service", "depende_de": [], "escopo": "double-entry"},
            {
                "modulo": "scheduler-service",
                "depende_de": ["ledger-service"],
                "escopo": "agenda",
            },
            {
                "modulo": "bank-integration-service",
                "depende_de": ["ledger-service"],
                "escopo": "PIX",
            },
            {
                "modulo": "reconciliation-service",
                "depende_de": ["ledger-service", "bank-integration-service"],
                "escopo": "extrato",
            },
            {
                "modulo": "notification-service",
                "depende_de": ["scheduler-service"],
                "escopo": "alertas",
            },
        ],
    }

    from services.llm.base_provider import LLMResult
    from services.llm.factory import LLMFactory

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(
        return_value=LLMResult(
            text=__import__("json").dumps(fake_json),
            meta={"model": "stub", "finish_reason": "STOP", "provider": "mock"},
        )
    )

    with patch.object(LLMFactory, "get_provider", return_value=mock_provider):
        result, meta = _generate_sdd_safe(
            {"generate_prd": {"prd_markdown": "# PRD\nPagamentos PIX e ledger"}},
            {"name": "fin", "user_prompt": "SaaS financeiro com PIX"},
            "generate_sdd",
            {"name": "SDD", "descricao": "Gerar SDD"},
        )

    assert not meta.get("fallback")
    assert len(result["build_order"]) == 5
    assert result["build_order"][0]["modulo"] == "ledger-service"
    assert "Ver artefato" not in result["sdd_markdown"] or True
    assert "regra regra" not in result["sdd_markdown"]


def test_normalize_strips_prd_appendix_and_keeps_build_order():
    normalized = _normalize_sdd(
        {
            "sdd_markdown": "# SDD\n\n## Stack\nx\n\n## Referência ao PRD\n# PRD colado\n",
            "build_order": [
                {"modulo": "core", "depende_de": [], "escopo": "mvp"},
            ],
        }
    )
    assert "Referência ao PRD" not in normalized["sdd_markdown"]
    assert normalized["build_order"][0]["modulo"] == "core"
