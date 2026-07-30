"""Testes da dupla visão do retorno (pipeline × Phanton)."""

from __future__ import annotations

from services.retorno_dual_vision import (
    resolve_phanton_improvement_proposal,
    split_retorno_dual_vision,
    summarize_phanton_improvement_local,
)


SAMPLE = """
## Retorno — pipeline
Troquei auth para JWT e ajustei o schema de aulas.

## Retorno — Phanton
- Incluir fase de assessment de SDD antes do prompt
- Melhorar o template de desvios na fila de módulos
"""


def test_split_retorno_dual_vision():
    parts = split_retorno_dual_vision(SAMPLE)
    assert "JWT" in parts["pipeline"]
    assert "assessment" in parts["phanton"]
    assert parts["split_mode"] == "headed"


def test_summarize_phanton_improvement_local():
    parts = split_retorno_dual_vision(SAMPLE)
    summary = summarize_phanton_improvement_local(parts["phanton"])
    assert summary["has_proposal"] is True
    assert summary["title"]
    assert "assessment" in summary["summary"].lower() or any(
        "assessment" in i.lower() for i in summary["items"]
    )


def test_resolve_without_llm_when_section_present():
    resolved = resolve_phanton_improvement_proposal(SAMPLE, use_llm_fallback=False)
    assert resolved["has_proposal"] is True
    assert resolved["source"] == "section"
    assert "JWT" in resolved["pipeline_section"]


def test_resolve_no_proposal_without_phanton_section():
    text = "## Retorno — pipeline\nSó desvio de implementação no auth."
    resolved = resolve_phanton_improvement_proposal(text, use_llm_fallback=False)
    assert resolved["has_proposal"] is False
    assert "auth" in resolved["pipeline_section"]
