#!/usr/bin/env python3
"""154 — aula sem trabalho some; aula com Kanban/conteúdo é preservada. Sem I/O."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from school_integracao_routes import _aula_tem_trabalho  # noqa: E402


def main() -> int:
    assert _aula_tem_trabalho(None) is False
    assert _aula_tem_trabalho({"status": "draft"}) is False
    assert _aula_tem_trabalho({"status": "em_execucao"}) is True
    assert _aula_tem_trabalho({"status": "draft", "kanban_state": {"tarefas": [{"id": 1}]}}) is True
    assert _aula_tem_trabalho({"status": "draft", "objetivo_aprendizagem": "x"}) is True
    print("ok 154 aula trabalho")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
