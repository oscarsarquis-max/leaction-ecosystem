"""Testes da validação determinística single_tenant + testes_requeridos."""

from __future__ import annotations

import pytest

from services.context_consistency import (
    find_forbidden_terms,
    validar_consistencia_contexto,
)
from services.phase_prompt_cursor import (
    _append_testes_section,
    _parse_module_prompts_structured,
)


def test_validador_detecta_tenant_em_single_tenant():
    problemas = validar_consistencia_contexto(
        {
            "database-ledger-setup": [
                "Usar chaves distintas por tenant no ledger",
            ],
            "auth-audit-service": [
                "MFA obrigatório para admins",
            ],
        },
        {"tipo": "single_tenant"},
    )
    assert len(problemas) == 1
    assert problemas[0]["modulo"] == "database-ledger-setup"
    assert "tenant" in problemas[0]["termos"]


def test_validador_detecta_propria_organizacao():
    termos = find_forbidden_terms(
        "O usuário só pode ver pagamentos de sua própria organização",
        contexto_tipo="single_tenant",
    )
    assert "sua própria organização" in termos or "própria organização" in termos


def test_validador_ignora_quando_nao_single():
    problemas = validar_consistencia_contexto(
        {"m": ["isolamento por tenant"]},
        {"tipo": "multi_tenant"},
    )
    assert problemas == []


def test_parse_module_prompts_exige_testes_nao_vazios():
    parsed = {
        "module_prompts": [
            {
                "modulo": "a",
                "prompt": "implemente A",
                "testes_requeridos": ["teste do trigger imutável"],
            },
            {
                "modulo": "b",
                "prompt": "implemente B",
                "testes_requeridos": [],
            },
            {
                "modulo": "c",
                "prompt": "implemente C",
                # sem testes
            },
        ]
    }
    out = _parse_module_prompts_structured(parsed)
    assert "a" in out
    assert "b" not in out
    assert "c" not in out


def test_append_testes_section_obrigatoria():
    text = _append_testes_section(
        "Implemente o ledger.",
        [
            "Teste do trigger rejeitando UPDATE/DELETE",
            "Teste da constraint de soma zero",
        ],
    )
    assert "## Testes" in text
    assert "trigger" in text.lower()
    with pytest.raises(ValueError, match="testes_requeridos vazio"):
        _append_testes_section("sem testes", [])


def test_append_testes_substitui_secao_antiga():
    old = "Prompt\n\n## Testes\n- genérico escrever testes"
    text = _append_testes_section(old, ["Teste específico da constraint"])
    assert text.count("## Testes") == 1
    assert "genérico" not in text
    assert "constraint" in text
