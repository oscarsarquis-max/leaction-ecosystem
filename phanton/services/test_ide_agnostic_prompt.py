"""Entrega de prompt deve ser agnóstica de IDE (não só Cursor)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.phase_prompt_cursor import neutralize_ide_branding  # noqa: E402
from services.text_to_spec import _CURSOR_DESCRICAO, _ensure_software_topology  # noqa: E402


def test_neutralize_ide_branding():
    raw = (
        "Cole no Cursor IDE. O agente do Cursor e o GitHub Copilot "
        "devem ler PRD.md. Windsurf também serve."
    )
    out = neutralize_ide_branding(raw)
    assert "Cursor" not in out
    assert "Copilot" not in out
    assert "Windsurf" not in out
    assert "IDE" in out
    assert "PRD.md" in out


def test_cursor_descricao_menciona_qualquer_ide():
    assert "qualquer IDE" in _CURSOR_DESCRICAO or "qualquer IDE" in _CURSOR_DESCRICAO.lower()
    # Descrição interna pode citar exemplos; o texto gerado ao usuário é que deve ser neutro
    assert "agnostico" in _CURSOR_DESCRICAO.lower() or "agnóstico" in _CURSOR_DESCRICAO.lower()


def test_topology_phase_name_not_cursor_only():
    phases: dict = {
        "methodology": {"type": "methodology", "order": 2, "depends_on": []},
    }
    _ensure_software_topology(
        phases,
        user_prompt="Quero um software SaaS de lista de tarefas",
    )
    name = phases["prompt_cursor"]["name"]
    assert "IDE" in name
    assert "Cursor IDE" not in name
