"""Testes unitários — task_breakdown (normalização + detecção no Spec)."""

from __future__ import annotations

from services.phase_context import normalize_phase_type
from services.phase_task_breakdown import (
    _normalize_breakdown,
    _normalize_issue,
)
from services.quality_score import _missing_required_fields
from services.text_to_spec import (
    _ensure_software_topology,
    _wants_task_breakdown,
)


def test_wants_task_breakdown_keywords():
    """Helper legado (keywords) — a topologia software inclui a fase sempre."""
    assert _wants_task_breakdown("Quero exportar para o Linear")
    assert _wants_task_breakdown("Gere épicos e issues do backlog")
    assert _wants_task_breakdown("Prepare tarefas para o Jira")
    assert not _wants_task_breakdown("Crie um micro-SaaS de hábitos")


def test_normalize_issue_micro_prompt_and_type():
    issue = _normalize_issue(
        {
            "title": "Criar rota POST /login",
            "type": "api",
            "description": "Use FastAPI e JWT conforme SDD.",
            "dependencies": [],
        },
        index=1,
    )
    assert issue is not None
    assert issue["title"] == "Criar rota POST /login"
    assert issue["type"] == "backend"
    assert "FastAPI" in issue["description_micro_prompt"]
    assert issue["dependencies"] == []


def test_normalize_breakdown_schema():
    parsed = _normalize_breakdown(
        {
            "epics": [
                {
                    "title": "Autenticação",
                    "description": "Login e sessão",
                    "issues": [
                        {
                            "title": "POST /login",
                            "type": "backend",
                            "description_micro_prompt": (
                                "Implemente POST /login com JWT; valide email/senha; "
                                "retorne 401 em falha. Critério: teste unitário verde."
                            ),
                            "dependencies": [],
                        }
                    ],
                }
            ]
        }
    )
    assert len(parsed["epics"]) == 1
    assert parsed["epics"][0]["issues"][0]["type"] == "backend"
    assert "JWT" in parsed["epics"][0]["issues"][0]["description_micro_prompt"]


def test_capability_aliases():
    assert normalize_phase_type("task_breakdown", "task_breakdown") == "task_breakdown"
    assert normalize_phase_type("linear_export", "linear_export") == "task_breakdown"
    assert normalize_phase_type("foo", "task_breakdown") == "task_breakdown"


def test_quality_requires_epics_and_micro_prompt():
    missing = _missing_required_fields("task_breakdown", {})
    assert "epics" in missing

    missing_ok = _missing_required_fields(
        "task_breakdown",
        {
            "epics": [
                {
                    "title": "E1",
                    "description": "d",
                    "issues": [
                        {
                            "title": "I1",
                            "type": "backend",
                            "description_micro_prompt": "Faça X com Y.",
                            "dependencies": [],
                        }
                    ],
                }
            ]
        },
    )
    assert missing_ok == []


def test_ensure_software_topology_adds_task_breakdown_when_asked():
    phases: dict = {
        "context7_search": {
            "type": "context7_search",
            "order": 1,
            "depends_on": [],
        },
        "sintese_produto": {
            "type": "synthesize",
            "order": 2,
            "depends_on": ["context7_search"],
        },
    }
    prompt = (
        "Quero um software SaaS de hábitos e gerar tarefas/épicos "
        "para exportar no Linear."
    )
    _ensure_software_topology(phases, user_prompt=prompt)
    assert "task_breakdown" in phases
    cfg = phases["task_breakdown"]
    assert cfg["type"] == "task_breakdown"
    assert "generate_sdd" in cfg["depends_on"]
    assert "generate_prd" in cfg["depends_on"]


def test_ensure_software_topology_always_adds_task_breakdown():
    """Task breakdown é fixo no software — sem exigir Linear/tarefas no prompt."""
    phases: dict = {}
    _ensure_software_topology(
        phases,
        user_prompt="Quero um micro-SaaS de gestão de hábitos diários.",
    )
    assert "generate_sdd" in phases
    assert "task_breakdown" in phases
    assert phases["task_breakdown"]["type"] == "task_breakdown"
    assert "generate_sdd" in phases["task_breakdown"]["depends_on"]
