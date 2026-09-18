"""Prompt 102 — lookup canônico por condição. Sem DB."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aee_internal_routes import _item_from_row  # noqa: E402


def test_item_exige_passos():
    assert _item_from_row(None) is None
    assert _item_from_row({"passos_adaptados": "  "}) is None
    item = _item_from_row(
        {
            "metodologia_codigo": "agil_mapeamento_mental",
            "metodologia_nome": "Mapa mental",
            "condicao_categoria": "TEA",
            "passos_adaptados": "O aluno aponta/percorre com o dedo o texto no mapa.",
        }
    )
    assert item["fonte"] == "card_modificado_79_81"
    assert "aponta/percorre" in item["passos_adaptados"]


if __name__ == "__main__":
    test_item_exige_passos()
    print("ok")
