"""Testes da nota objetiva e regras de auto-aprovação."""

from __future__ import annotations

from services.quality_score import (
    ALWAYS_HUMAN,
    AUTO_APPROVE_THRESHOLD,
    attach_quality_score,
    compute_quality_score,
    should_auto_approve,
)


def test_fallback_penalizes_heavily():
    score = compute_quality_score(
        "generate_sdd",
        {"fallback": True, "attempts": []},
        {"sdd_markdown": "# SDD", "build_order": [{"modulo": "a"}]},
    )
    assert score == 50  # 100 - 50


def test_retries_and_max_tokens_penalties():
    score = compute_quality_score(
        "generate_prd",
        {
            "fallback": False,
            "attempts": ["err1", "err2"],
            "finish_reason": "FinishReason.MAX_TOKENS",
        },
        {"prd_markdown": "# PRD completo"},
    )
    # 100 - 20 (2 retries) - 15 (MAX_TOKENS) = 65
    assert score == 65


def test_missing_build_order_penalizes_sdd():
    score = compute_quality_score(
        "generate_sdd",
        {"attempts": [], "finish_reason": "FinishReason.STOP"},
        {"sdd_markdown": "# ok", "build_order": []},
    )
    assert score == 80  # 100 - 20 missing build_order


def test_complete_artifact_high_score():
    score = compute_quality_score(
        "generate_sdd",
        {"attempts": [], "finish_reason": "FinishReason.STOP"},
        {
            "sdd_markdown": "# SDD",
            "build_order": [{"modulo": "api", "depends_on": []}],
        },
    )
    assert score == 100


def test_security_requires_module_coverage():
    score = compute_quality_score(
        "security_guidelines",
        {"attempts": []},
        {
            "standards_aplicados": ["LGPD"],
            "diretrizes_gerais": ["tls"],
            "diretrizes_por_modulo": {"api": ["x"]},
        },
        expected_modules=["api", "worker"],
    )
    # missing diretrizes_por_modulo.worker → -20
    assert score == 80


def test_context7_requires_keywords_and_hits():
    score = compute_quality_score(
        "context7_search",
        {},
        {"search_keywords": ["finance"], "context7_hits": []},
    )
    assert score == 80  # missing hits


def test_auto_approve_off_never_approves():
    assert not should_auto_approve(
        auto_approve=False, phase_type="generate_sdd", quality_score=100
    )


def test_auto_approve_on_high_score():
    assert should_auto_approve(
        auto_approve=True, phase_type="generate_sdd", quality_score=80
    )
    assert not should_auto_approve(
        auto_approve=True, phase_type="generate_sdd", quality_score=79
    )


def test_security_guidelines_always_human():
    assert "security_guidelines" in ALWAYS_HUMAN
    assert not should_auto_approve(
        auto_approve=True,
        phase_type="security_guidelines",
        quality_score=100,
        threshold=AUTO_APPROVE_THRESHOLD,
    )


def test_attach_quality_score_on_envelope():
    art = attach_quality_score(
        {"status": "ok", "meta": {"model": "x"}, "artifact_data": {"a": 1}},
        90,
    )
    assert art["quality_score"] == 90
    assert art["meta"]["quality_score"] == 90


def test_financial_sdd_with_retry_like_e2e():
    """Espelha o SDD do run financeiro E2E: 1 retry, sem fallback → nota 90."""
    score = compute_quality_score(
        "generate_sdd",
        {
            "attempts": ["ValueError: JSON inválido/truncado"],
            "finish_reason": "FinishReason.STOP",
            "fallback": False,
        },
        {
            "sdd_markdown": "# SDD",
            "build_order": [{"modulo": "infra-db-keycloak"}],
        },
    )
    assert score == 90
    assert should_auto_approve(
        auto_approve=True, phase_type="generate_sdd", quality_score=score
    )


def test_fallback_sdd_not_auto_approved():
    score = compute_quality_score(
        "generate_sdd",
        {"fallback": True, "attempts": ["boom"]},
        {"sdd_markdown": "template", "build_order": []},
    )
    # 100 - 50 - 10 - 20 = 20
    assert score == 20
    assert not should_auto_approve(
        auto_approve=True, phase_type="generate_sdd", quality_score=score
    )
