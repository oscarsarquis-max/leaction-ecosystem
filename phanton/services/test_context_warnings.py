"""Testes do checklist de lacunas de contexto (warnings no Spec)."""

from __future__ import annotations

from services.context_warnings import (
    CAMPO_CONTEXTO_USO,
    CAMPO_ESCALA,
    detect_context_warnings,
    normalize_warnings,
)
from services.text_to_spec import _normalize_generated_spec


FINANCEIRO_AMBIGUO = (
    "Quero um SaaS financeiro de conciliacao bancaria e gestao de contas a "
    "pagar/receber para controlar a conta corrente bancaria da empresa, com "
    "autenticacao, dashboard e integracao Open Finance. Dominio sensivel de financas."
)

FINANCEIRO_SINGLE_EXPLICITO = (
    "Quero um sistema financeiro de conciliacao bancaria para uso interno de "
    "uma unica empresa, nao e produto para vender. Single-tenant. Escala: "
    "dezenas de usuarios. Deploy na AWS. Integracao via Pluggy (Open Finance "
    "Brasil). Adequacao a LGPD e FAPI 2.0."
)


def test_warnings_always_list_even_when_absent_in_raw_spec():
    spec = _normalize_generated_spec(
        {
            "description": "x",
            "phases": {
                "methodology_x": {
                    "type": "methodology",
                    "order": 1,
                    "descricao": "m",
                },
                "prompt_html": {
                    "type": "prompt",
                    "order": 2,
                    "depends_on": ["methodology_x"],
                    "descricao": "entrega",
                },
            },
        },
        "Criar uma apresentacao HTML sobre PBL para professores",
    )
    assert isinstance(spec.get("warnings"), list)


def test_financeiro_ambiguo_tem_contexto_de_uso():
    warnings = detect_context_warnings(FINANCEIRO_AMBIGUO)
    campos = {w["campo"] for w in warnings}
    assert CAMPO_CONTEXTO_USO in campos
    assert CAMPO_ESCALA in campos  # sem dezenas/milhares


def test_financeiro_explicito_sem_contexto_de_uso():
    warnings = detect_context_warnings(FINANCEIRO_SINGLE_EXPLICITO)
    campos = {w["campo"] for w in warnings}
    assert CAMPO_CONTEXTO_USO not in campos
    assert CAMPO_ESCALA not in campos


def test_normalize_merges_and_keeps_heuristic_authority():
    # LLM inventou que multi-tenant estava claro; heurística do pedido ambíguo vence.
    merged = normalize_warnings(
        [
            {
                "campo": CAMPO_CONTEXTO_USO,
                "descricao": "LLM disse que está ok",
                "impacto": "x",
            }
        ],
        FINANCEIRO_AMBIGUO,
    )
    by_campo = {w["campo"]: w for w in merged}
    assert CAMPO_CONTEXTO_USO in by_campo
    assert "multi-tenant" in by_campo[CAMPO_CONTEXTO_USO]["descricao"].lower() or (
        "single-tenant" in by_campo[CAMPO_CONTEXTO_USO]["descricao"].lower()
    )


def test_normalize_empty_when_prompt_covers_critical_gaps():
    merged = normalize_warnings([], FINANCEIRO_SINGLE_EXPLICITO)
    campos = {w["campo"] for w in merged}
    assert CAMPO_CONTEXTO_USO not in campos
    assert isinstance(merged, list)


def test_normalize_generated_spec_attaches_warnings_for_finance_case():
    raw = {
        "runId": "fin-test",
        "description": FINANCEIRO_AMBIGUO,
        "phases": {
            "context7_search": {"type": "context7_search", "order": 1},
            "methodology_saas": {"type": "methodology", "order": 2},
            "research_x": {"type": "research", "order": 3},
            "synthesize_x": {
                "type": "synthesize",
                "order": 4,
                "depends_on": ["context7_search", "methodology_saas", "research_x"],
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
            "security_guidelines": {
                "type": "security_guidelines",
                "order": 7,
                "depends_on": ["generate_sdd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 8,
                "depends_on": ["generate_sdd", "security_guidelines"],
            },
        },
    }
    spec = _normalize_generated_spec(raw, FINANCEIRO_AMBIGUO)
    assert isinstance(spec["warnings"], list)
    assert any(w["campo"] == CAMPO_CONTEXTO_USO for w in spec["warnings"])
