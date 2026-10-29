"""Entrega HTML sozinha não pode falhar por falta de fases anteriores.

Não altera criação de sistemas nem a simulação de prompts, que continuam
exigindo os artefatos das fases das quais dependem.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from services.crystal_ball.experimental_run import (  # noqa: E402
    PHASE_CONTEXT7,
    PHASE_ENTREGA,
    PHASE_METHODOLOGY,
    PHASE_SYNTHESIZE,
    build_experimental_spec,
)
from services.phase_L4 import execute_phase_L4  # noqa: E402
from services.text_to_spec import _normalize_generated_spec  # noqa: E402

_HTML = "<!DOCTYPE html><html><body><h1>Fases do Phanton</h1></body></html>"
_HTML_PROMPT = (
    "criar uma apresentacao html mostrando todas as fases de criação de "
    "prompts pelo phanton. A apresentação deve ser dinâmica."
)
_SOFTWARE_PROMPT = (
    "criar um sistema que entre com as informacoes de compra via nota fiscal, "
    "escrito em python, para uso pessoal"
)


def test_lone_html_delivery_generates_from_the_request(monkeypatch):
    captured: dict[str, str] = {}

    def fake_generate(prompt, **kwargs):
        captured["prompt"] = prompt
        return _HTML, {"model": "test"}

    monkeypatch.setattr("services.phase_L4.generate_content", fake_generate)
    spec = {
        "description": _HTML_PROMPT,
        "user_prompt": _HTML_PROMPT,
        "phases": {
            "entrega_final": {
                "type": "prompt",
                "order": 1,
                "name": "Apresentação final",
                "depends_on": [],
                "descricao": "HTML dinâmico da apresentação",
            }
        },
    }
    result = asyncio.run(
        execute_phase_L4(
            "00000000-0000-0000-0000-000000000001",
            spec,
            db_session=object(),
            phase_id="entrega_final",
        )
    )
    assert result["status"] == "success"
    assert "<!DOCTYPE html>" in result["delivery"]
    assert "Nenhum artefato" not in captured["prompt"]
    assert "Não há fases anteriores" in captured["prompt"]
    assert "já produziu metodologia" not in captured["prompt"]
    assert "apresentacao html" in captured["prompt"] or "apresentação html" in captured["prompt"]


def test_delivery_still_waits_when_prior_phases_are_required(monkeypatch):
    monkeypatch.setattr(
        "services.phase_L4.load_dependency_artifacts",
        lambda *args, **kwargs: {},
    )

    def fail_generate(*args, **kwargs):
        raise AssertionError("não deve chamar o modelo sem as fases exigidas")

    monkeypatch.setattr("services.phase_L4.generate_content", fail_generate)
    spec = {
        "description": "roteiro de aula",
        "user_prompt": "roteiro de aula com PBL",
        "phases": {
            "sintese": {"type": "synthesize", "order": 1, "depends_on": []},
            "entrega_final": {
                "type": "prompt",
                "order": 2,
                "name": "Entrega final",
                "depends_on": ["sintese"],
            },
        },
    }
    result = asyncio.run(
        execute_phase_L4(
            "00000000-0000-0000-0000-000000000002",
            spec,
            db_session=object(),
            phase_id="entrega_final",
        )
    )
    assert result["status"] == "error"
    assert "Nenhum artefato de entrada" in result["artifact_data"]["erro"]


def test_software_spec_keeps_system_phases():
    spec = _normalize_generated_spec(
        {
            "phases": {
                "metodologia": {"type": "methodology", "order": 1, "depends_on": []},
            }
        },
        _SOFTWARE_PROMPT,
    )
    phases = spec["phases"]
    assert "generate_prd" in phases
    assert "generate_sdd" in phases
    assert "security_guidelines" in phases
    assert "prompt_cursor" in phases
    assert "task_breakdown" in phases
    assert phases["prompt_cursor"]["type"] == "prompt_cursor"
    assert "entrega_final" not in phases


def test_html_spec_does_not_become_a_software_pipeline():
    spec = _normalize_generated_spec(
        {
            "phases": {
                "entrega_final": {
                    "type": "prompt",
                    "order": 1,
                    "name": "Apresentação final",
                    "depends_on": [],
                }
            }
        },
        _HTML_PROMPT,
    )
    phases = spec["phases"]
    assert "generate_sdd" not in phases
    assert "prompt_cursor" not in phases
    assert phases["entrega_final"]["type"] == "prompt"


def test_prompt_simulation_still_depends_on_prior_phases():
    spec = build_experimental_spec(
        user_prompt="Sou professora. Quero um roteiro de aula com PBL.",
        metodologia="Aprendizagem Baseada em Problemas",
    )
    entrega = spec["phases"][PHASE_ENTREGA]
    assert entrega["type"] == "prompt"
    assert entrega["depends_on"] == [
        PHASE_CONTEXT7,
        PHASE_METHODOLOGY,
        PHASE_SYNTHESIZE,
    ]
