"""Testes de identidade projeto/versão e regras de imutabilidade."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.project_versioning import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_OPEN,
    LINEAGE_EVOLUCAO,
    LINEAGE_RETORNO,
    ProjectVersioningError,
    assert_run_mutable,
    build_reanalysis_prompt,
    bump_version,
    ensure_identity_on_spec,
    is_accepted,
    normalize_version,
    slugify_project_key,
)


def test_slugify_project_key_ascii():
    assert slugify_project_key("LeActiona LMS!") == "leactiona-lms"
    assert slugify_project_key("  Plataforma Multimedia  ") == "plataforma-multimedia"
    assert slugify_project_key("") == "projeto"


def test_bump_version():
    assert bump_version("1.0") == "1.1"
    assert bump_version("1.9") == "1.10"
    assert bump_version("2") == "2.1"
    assert bump_version("v") == "1.1"


def test_ensure_identity_on_spec():
    spec = ensure_identity_on_spec({"description": "Meu App SaaS"})
    assert spec["name"] == "Meu App SaaS"
    assert spec["version"] == "1.0"
    assert spec["project_key"] == "meu-app-saas"


def test_is_accepted_and_mutable():
    open_run = SimpleNamespace(acceptance_status=ACCEPTANCE_OPEN, status="COMPLETED")
    sealed = SimpleNamespace(acceptance_status=ACCEPTANCE_ACCEPTED, status="ACCEPTED")
    assert not is_accepted(open_run)
    assert is_accepted(sealed)
    assert_run_mutable(open_run)
    with pytest.raises(ProjectVersioningError, match="imutável"):
        assert_run_mutable(sealed)


def test_build_reanalysis_prompt_contains_versions_and_kind():
    prompt = build_reanalysis_prompt(
        project_name="Demo",
        version="1.0",
        next_version="1.1",
        kind=LINEAGE_RETORNO,
        user_input="Ajustei o auth para JWT.",
        prior_prompt="Construir demo",
        artifact_digest="### sdd\nok",
    )
    assert "1.0" in prompt
    assert "1.1" in prompt
    assert "retorno do implementador" in prompt
    assert "JWT" in prompt

    prompt2 = build_reanalysis_prompt(
        project_name="Demo",
        version="1.1",
        next_version="1.2",
        kind=LINEAGE_EVOLUCAO,
        user_input="Adicionar certificados PDF.",
        prior_prompt="Construir demo",
        artifact_digest="x",
    )
    assert "pedido de evolução" in prompt2


def test_normalize_version():
    assert normalize_version(None) == "1.0"
    assert normalize_version(" 2.3 ") == "2.3"
