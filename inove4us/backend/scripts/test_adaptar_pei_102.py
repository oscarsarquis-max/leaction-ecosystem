"""Prompt 102 — retrieval PEI 🧩. Sem Bedrock, sem AWS."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kanban_pei_routes import (  # noqa: E402
    apendice_pei_individual,
    montar_texto_subcard_pei,
)


def test_justapoe_sem_fundir():
    texto = montar_texto_subcard_pei(
        passos="O aluno aponta/percorre com o dedo o texto no mapa.",
        apendice="PEI individual de Lucas Mendes:\nCheck-ins curtos.",
    )
    assert "aponta/percorre" in texto
    assert "— PEI individual —" in texto
    assert "Check-ins curtos" in texto
    assert texto.index("aponta/percorre") < texto.index("Check-ins")


def test_sem_apendice_e_so_canonico():
    t = montar_texto_subcard_pei(passos="Passo AEE.", apendice="")
    assert t == "Passo AEE."
    assert "PEI individual" not in t


def test_apendice_vem_do_pei_cadastrado():
    ctx = {
        "individual": {
            "aluno_nome": "Lucas Mendes",
            "particularidades": "Check-ins curtos, timer visível, entregas parciais.",
        }
    }
    ap = apendice_pei_individual(ctx)
    assert "Lucas Mendes" in ap
    assert "Check-ins curtos" in ap
    assert apendice_pei_individual({}) == ""
    assert apendice_pei_individual({"individual": {"aluno_nome": "X"}}) == ""


if __name__ == "__main__":
    test_justapoe_sem_fundir()
    test_sem_apendice_e_so_canonico()
    test_apendice_vem_do_pei_cadastrado()
    print("ok")
