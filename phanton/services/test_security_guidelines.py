"""Testes: fase security_guidelines separada + anexação nos prompts."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.phase_context import normalize_phase_type  # noqa: E402
from services.security_domain import (  # noqa: E402
    append_security_section,
    classify_sensitive_domain,
    is_sensitive_domain,
    module_guidelines_hint,
    requires_open_finance_profile,
    standards_for_domain,
    strip_fapi_unless_open_finance,
)
from services.text_to_spec import _ensure_software_topology, _normalize_generated_spec  # noqa: E402


def test_classify_financeiro_vs_generico():
    assert classify_sensitive_domain(
        "Quero um SaaS financeiro com ledger, PIX e Open Finance"
    ) == "financeiro"
    assert is_sensitive_domain("plataforma de pagamentos e reconciliacao bancaria")
    assert classify_sensitive_domain("gerar apresentacao de slides sobre Scrum") is None
    assert not is_sensitive_domain("gerar apresentacao de slides sobre Scrum")


def test_classify_educacao_vence_pagamento_generico():
    """LMS com 'conteúdo pago' não pode virar domínio financeiro/FAPI."""
    assert (
        classify_sensitive_domain(
            "LMS educacional com SCORM, certificados e conteudo pago sem gateway"
        )
        == "educacao"
    )
    assert classify_sensitive_domain(
        "SaaS educacional de trilhas de aprendizagem"
    ) == "educacao"


def test_fapi_somente_open_finance():
    assert requires_open_finance_profile("ledger com Open Finance e PIX")
    assert not requires_open_finance_profile("LMS com aluno e certificado")
    std_fin = standards_for_domain(
        "financeiro", source_text="controle financeiro interno ledger"
    )
    assert "FAPI 2.0" not in std_fin
    std_of = standards_for_domain(
        "financeiro", source_text="integracao Open Banking PIX"
    )
    assert "FAPI 2.0" in std_of
    std_edu = standards_for_domain(
        "educacao", source_text="LMS SCORM xAPI"
    )
    assert "FAPI 2.0" not in std_edu
    assert "LGPD" in std_edu

    cleaned = strip_fapi_unless_open_finance(
        ["ASVS V4", "FAPI 2.0 PAR+PKCE", "LGPD"],
        source_text="LMS educacional",
        domain_id="educacao",
    )
    assert cleaned == ["ASVS V4", "LGPD"]

    auth_hint = module_guidelines_hint(
        "educacao", "auth-rbac", "login JWT", source_text="LMS"
    )
    joined = " || ".join(auth_hint)
    assert "FAPI 2.0 obrigatório" not in joined
    assert "token sender-constrained" not in joined
    assert "refresh" in joined.lower()


def test_software_topology_insere_fase_separada_para_financeiro():
    phases: dict = {
        "methodology": {"type": "methodology", "order": 2, "depends_on": []},
        "research": {"type": "research", "order": 3, "depends_on": []},
    }
    prompt = "Sistema SaaS financeiro com ledger, scheduler e integracao bancaria PIX"
    _ensure_software_topology(phases, user_prompt=prompt)

    assert "security_guidelines" in phases
    sec = phases["security_guidelines"]
    assert sec["type"] == "security_guidelines"
    assert sec.get("requires_approval") is True
    assert "generate_sdd" in (sec.get("depends_on") or [])

    cursor = phases["prompt_cursor"]
    deps = cursor.get("depends_on") or []
    assert "security_guidelines" in deps
    assert "generate_sdd" in deps
    # Ordem: SDD antes de security antes de prompt_cursor
    assert phases["generate_sdd"]["order"] < sec["order"] < cursor["order"]


def test_software_topology_educacao_tem_security_sem_fapi_default():
    phases: dict = {
        "methodology": {"type": "methodology", "order": 2, "depends_on": []},
    }
    _ensure_software_topology(
        phases,
        user_prompt="Quero construir um SaaS educacional de agenda escolar",
    )
    assert "security_guidelines" in phases
    assert "security_guidelines" in (phases["prompt_cursor"].get("depends_on") or [])
    std = standards_for_domain(
        "educacao",
        source_text="Quero construir um SaaS educacional de agenda escolar",
    )
    assert "FAPI 2.0" not in std


def test_normalize_keeps_security_on_educacao():
    raw = {
        "runId": "edu-app",
        "phases": {
            "generate_sdd": {"type": "generate_sdd", "order": 5, "depends_on": []},
            "security_guidelines": {
                "type": "security_guidelines",
                "order": 6,
                "depends_on": ["generate_sdd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 7,
                "depends_on": ["security_guidelines"],
            },
        },
    }
    spec = _normalize_generated_spec(
        raw,
        "Quero um software SaaS educacional de trilhas de aprendizagem",
    )
    assert "security_guidelines" in spec["phases"]


def test_normalize_keeps_security_on_generic_saas():
    """SaaS genérico também mantém security_guidelines (fase fixa do software)."""
    raw = {
        "runId": "todo-app",
        "phases": {
            "generate_sdd": {"type": "generate_sdd", "order": 5, "depends_on": []},
            "security_guidelines": {
                "type": "security_guidelines",
                "order": 6,
                "depends_on": ["generate_sdd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 7,
                "depends_on": ["security_guidelines"],
            },
        },
    }
    spec = _normalize_generated_spec(
        raw,
        "Quero um software SaaS de lista de tarefas e notas pessoais",
    )
    assert "security_guidelines" in spec["phases"]
    assert "security_guidelines" in (
        spec["phases"]["prompt_cursor"].get("depends_on") or []
    )


def test_software_topology_sempre_inclui_security_em_saas_generico():
    phases: dict = {
        "methodology": {"type": "methodology", "order": 2, "depends_on": []},
    }
    _ensure_software_topology(
        phases,
        user_prompt="Habit tracker offline-first com React e LocalStorage",
    )
    assert "security_guidelines" in phases
    assert phases["security_guidelines"]["type"] == "security_guidelines"
    assert "security_guidelines" in (phases["prompt_cursor"].get("depends_on") or [])
    assert (
        phases["generate_sdd"]["order"]
        < phases["security_guidelines"]["order"]
        < phases["prompt_cursor"]["order"]
    )


def test_ensure_fixed_software_phases_injeta_security_em_spec_antigo():
    from services.text_to_spec import ensure_fixed_software_phases

    spec = {
        "user_prompt": "Quero um software SaaS de hábitos com React",
        "description": "Quero um software SaaS de hábitos com React",
        "phases": {
            "context7_search": {"type": "context7_search", "order": 1},
            "generate_prd": {"type": "generate_prd", "order": 2, "depends_on": []},
            "generate_sdd": {
                "type": "generate_sdd",
                "order": 3,
                "depends_on": ["generate_prd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 4,
                "depends_on": ["generate_sdd"],
            },
        },
    }
    out = ensure_fixed_software_phases(spec)
    assert "security_guidelines" in out["phases"]
    assert "task_breakdown" in out["phases"]
    assert "security_guidelines" in (
        out["phases"]["prompt_cursor"].get("depends_on") or []
    )


def test_normalize_phase_type_security():
    assert normalize_phase_type("security_guidelines") == "security_guidelines"
    assert normalize_phase_type("security") == "security_guidelines"
    assert normalize_phase_type(None, "security_guidelines") == "security_guidelines"
    # LLM coloca type errado no id âncora — id vence SEMPRE
    for wrong in ("methodology", "prompt", "research", "synthesize", "", None):
        assert (
            normalize_phase_type(wrong, "security_guidelines")
            == "security_guidelines"
        ), wrong
    assert (
        normalize_phase_type("prompt", "diretrizes_seguranca")
        == "security_guidelines"
    )
    assert normalize_phase_type("research", "security_review") == "security_guidelines"


def test_anchor_phase_ids_force_type_unconditionally():
    """Âncoras do grafo: phase_id manda, type do LLM é ignorado."""
    cases = [
        ("context7_search", "methodology", "context7_search"),
        ("generate_prd", "prompt", "generate_prd"),
        ("generate_sdd", "research", "generate_sdd"),
        ("prompt_cursor", "methodology", "prompt_cursor"),
        ("security_guidelines", "prompt", "security_guidelines"),
    ]
    for phase_id, wrong_type, expected in cases:
        assert normalize_phase_type(wrong_type, phase_id) == expected


def test_financial_spec_with_type_prompt_is_repaired():
    """2ª geração: LLM mandou type=prompt em security_guidelines."""
    raw = {
        "runId": "financial-control-system",
        "phases": {
            "context7_search": {"type": "research", "order": 1, "depends_on": []},
            "generate_prd": {"type": "prompt", "order": 5, "depends_on": []},
            "generate_sdd": {"type": "methodology", "order": 6, "depends_on": []},
            "security_guidelines": {
                "name": "Diretrizes de Segurança",
                "type": "prompt",
                "order": 7,
                "depends_on": ["generate_sdd"],
            },
            "prompt_cursor": {
                "type": "delivery",
                "order": 8,
                "depends_on": ["generate_sdd"],
            },
        },
    }
    prompt = (
        "Sistema SaaS financeiro de controle de pagamentos com ledger, PIX "
        "e Open Finance"
    )
    spec = _normalize_generated_spec(raw, prompt)
    phases = spec["phases"]
    assert phases["security_guidelines"]["type"] == "security_guidelines"
    assert phases["generate_prd"]["type"] == "generate_prd"
    assert phases["generate_sdd"]["type"] == "generate_sdd"
    assert phases["prompt_cursor"]["type"] == "prompt_cursor"
    assert phases["context7_search"]["type"] == "context7_search"
    assert "security_guidelines" in phases["prompt_cursor"]["depends_on"]


def test_financial_spec_misplaced_security_is_repaired():
    """Replica o Spec quebrado (type methodology, order cedo, cursor sem dep)."""
    raw = {
        "runId": "financial-control-system",
        "phases": {
            "context7_search": {
                "type": "context7_search",
                "order": 1,
                "depends_on": [],
            },
            "methodology_finance": {
                "type": "methodology",
                "order": 2,
                "depends_on": [],
            },
            "research_pix_reconciliation": {
                "type": "research",
                "order": 3,
                "depends_on": [],
            },
            "security_guidelines": {
                "name": "Diretrizes de Segurança",
                "type": "methodology",
                "order": 4,
                "depends_on": [],
            },
            "sintese_produto": {
                "type": "synthesize",
                "order": 5,
                "depends_on": [
                    "context7_search",
                    "methodology_finance",
                    "research_pix_reconciliation",
                ],
            },
            "generate_prd": {
                "type": "generate_prd",
                "order": 6,
                "depends_on": ["sintese_produto"],
            },
            "generate_sdd": {
                "type": "generate_sdd",
                "order": 7,
                "depends_on": ["generate_prd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 8,
                "depends_on": ["generate_sdd"],
            },
        },
    }
    prompt = (
        "Quero construir um sistema SaaS financeiro de controle de pagamentos "
        "com ledger, PIX, Open Finance e reconciliacao bancaria"
    )
    spec = _normalize_generated_spec(raw, prompt)
    phases = spec["phases"]

    assert "security_guidelines" in phases
    sec = phases["security_guidelines"]
    assert sec["type"] == "security_guidelines"
    assert sec["depends_on"] == ["generate_sdd"]
    assert phases["generate_sdd"]["order"] < sec["order"]
    assert sec["order"] < phases["prompt_cursor"]["order"]

    cursor_deps = phases["prompt_cursor"]["depends_on"]
    assert cursor_deps == ["generate_sdd", "security_guidelines"]


def test_append_security_section_por_modulo():
    security = {
        "standards_aplicados": ["OWASP ASVS 5.0 (Level 3)", "FAPI 2.0"],
        "diretrizes_gerais": ["Criptografia em trânsito (ASVS V6)"],
        "diretrizes_por_modulo": {
            "ledger-service": ["Escrita só em transação ACID"],
            "bank-integration-service": ["FAPI 2.0: PAR + PKCE + DPoP/mTLS"],
        },
    }
    prompt = "# Implementar ledger\n\nFaça o núcleo."
    out = append_security_section(prompt, security, modulo="ledger-service")
    assert "## Segurança (padrão: OWASP ASVS 5.0 (Level 3), FAPI 2.0)" in out
    assert "Criptografia em trânsito" in out
    assert "Escrita só em transação ACID" in out
    assert "PAR + PKCE" not in out  # outro módulo

    bank = append_security_section(prompt, security, modulo="bank-integration-service")
    assert "PAR + PKCE" in bank


def test_sem_security_artifact_nao_altera_prompt():
    prompt = "# Prompt unico\nSem secao."
    assert append_security_section(prompt, None) == prompt
    assert append_security_section(prompt, {}) == prompt
