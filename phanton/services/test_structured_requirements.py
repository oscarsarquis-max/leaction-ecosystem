"""Testes do rascunho estruturado de requisitos (29148 simplificado)."""

from __future__ import annotations

from services.context_warnings import CAMPO_CONTEXTO_USO, detect_context_warnings
from services.structured_requirements import (
    PERFIL_ARTEFATO,
    PERFIL_SOFTWARE,
    format_structured_requirements_block,
    normalize_structured_requirements,
)
from services.text_to_spec import _normalize_generated_spec


FINANCEIRO_AMBIGUO = (
    "Quero um SaaS financeiro de conciliacao bancaria para controlar a conta "
    "corrente bancaria da empresa, com autenticacao e Open Finance."
)


def test_normalize_contexto_indefinido():
    data = normalize_structured_requirements(
        {
            "perfil_sugerido": "software_saas",
            "proposito_escopo": "Conciliação",
            "contexto_de_uso": {"tipo": "indefinido", "justificativa": "ambíguo"},
            "partes_interessadas": [],
            "requisitos_funcionais": ["RF1"],
            "requisitos_nao_funcionais": [],
            "restricoes_premissas": [],
            "interfaces_integracoes": [],
        }
    )
    assert data["perfil_sugerido"] == PERFIL_SOFTWARE
    assert data["contexto_de_uso"]["tipo"] == "indefinido"


def test_warnings_from_structured_indefinido():
    structured = normalize_structured_requirements(
        {
            "perfil_sugerido": "software_saas",
            "proposito_escopo": "x",
            "contexto_de_uso": {
                "tipo": "indefinido",
                "justificativa": "não ficou claro",
            },
            "partes_interessadas": [],
            "requisitos_funcionais": [],
            "requisitos_nao_funcionais": ["dezenas de usuarios", "deploy AWS"],
            "restricoes_premissas": [],
            "interfaces_integracoes": ["Pluggy"],
        }
    )
    warnings = detect_context_warnings(FINANCEIRO_AMBIGUO, structured)
    assert any(w["campo"] == CAMPO_CONTEXTO_USO for w in warnings)


def test_warnings_cleared_when_single_tenant_chosen():
    structured = normalize_structured_requirements(
        {
            "perfil_sugerido": "software_saas",
            "proposito_escopo": "Uso interno",
            "contexto_de_uso": {
                "tipo": "single_tenant",
                "justificativa": "humano escolheu",
            },
            "partes_interessadas": [],
            "requisitos_funcionais": ["CRUD contas"],
            "requisitos_nao_funcionais": ["dezenas de usuarios", "AWS"],
            "restricoes_premissas": ["LGPD"],
            "interfaces_integracoes": ["Pluggy Open Finance Brasil"],
        }
    )
    warnings = detect_context_warnings(FINANCEIRO_AMBIGUO, structured)
    assert not any(w["campo"] == CAMPO_CONTEXTO_USO for w in warnings)


def test_format_block_forbids_multitenant_when_single():
    structured = normalize_structured_requirements(
        {
            "perfil_sugerido": "software_saas",
            "proposito_escopo": "Interno",
            "contexto_de_uso": {
                "tipo": "single_tenant",
                "justificativa": "ok",
            },
            "partes_interessadas": [],
            "requisitos_funcionais": [],
            "requisitos_nao_funcionais": [],
            "restricoes_premissas": [],
            "interfaces_integracoes": [],
        }
    )
    block = format_structured_requirements_block(structured)
    assert "SINGLE-TENANT" in block
    assert "X-Tenant-ID" in block


def test_format_block_empty_for_artefato():
    structured = normalize_structured_requirements(
        {
            "perfil_sugerido": PERFIL_ARTEFATO,
            "proposito_escopo": "Slides",
            "contexto_de_uso": {"tipo": "indefinido", "justificativa": ""},
            "partes_interessadas": [],
            "requisitos_funcionais": [],
            "requisitos_nao_funcionais": [],
            "restricoes_premissas": [],
            "interfaces_integracoes": [],
        }
    )
    assert format_structured_requirements_block(structured) == ""


def test_normalize_spec_persists_structured_requirements():
    structured = normalize_structured_requirements(
        {
            "perfil_sugerido": "software_saas",
            "proposito_escopo": "Finanças internas",
            "contexto_de_uso": {
                "tipo": "single_tenant",
                "justificativa": "uso interno",
            },
            "partes_interessadas": [{"papel": "CFO", "descricao": "aprovador"}],
            "requisitos_funcionais": ["conciliação"],
            "requisitos_nao_funcionais": ["dezenas de usuarios", "AWS"],
            "restricoes_premissas": ["LGPD"],
            "interfaces_integracoes": ["Pluggy"],
        }
    )
    spec = _normalize_generated_spec(
        {
            "phases": {
                "context7_search": {"type": "context7_search", "order": 1},
                "methodology_x": {"type": "methodology", "order": 2},
                "research_x": {"type": "research", "order": 3},
                "synthesize_x": {
                    "type": "synthesize",
                    "order": 4,
                    "depends_on": ["context7_search", "methodology_x", "research_x"],
                },
                "generate_prd": {
                    "type": "generate_prd",
                    "order": 5,
                    "depends_on": ["synthesize_x"],
                },
                "generate_sdd": {
                    "type": "generate_sdd",
                    "order": 6,
                    "depends_on": ["generate_prd"],
                },
                "prompt_cursor": {
                    "type": "prompt_cursor",
                    "order": 7,
                    "depends_on": ["generate_sdd"],
                },
            }
        },
        FINANCEIRO_AMBIGUO,
        structured_requirements=structured,
    )
    assert spec["structured_requirements"]["contexto_de_uso"]["tipo"] == "single_tenant"
    assert not any(w["campo"] == CAMPO_CONTEXTO_USO for w in spec["warnings"])
