"""Outbound BNCC list in LESSON_RECORD (prompt 95)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from school_outbound import _bncc_from_evento  # noqa: E402


def test_envia_tres_codigos():
    ementa, first, codes = _bncc_from_evento(
        {
            "tema_aula": "título curto que não cabe todos os códigos",
            "ementa_topico": None,
            "habilidades_bncc": ["EF06MA07", "EF06MA08", "EF06MA09"],
            "titulo": "Dia a Dia",
        }
    )
    assert first == "EF06MA07"
    assert codes == ["EF06MA07", "EF06MA08", "EF06MA09"]


def test_regressao_regex_um_codigo():
    ementa, first, codes = _bncc_from_evento(
        {
            "tema_aula": "EF06MA07 — Frações no cotidiano",
            "titulo": "Dia a Dia · EF06MA07 — Frações no cotidiano · 6º Ano A",
        }
    )
    assert first == "EF06MA07"
    assert codes == ["EF06MA07"]


if __name__ == "__main__":
    test_envia_tres_codigos()
    test_regressao_regex_um_codigo()
    print("ok")
