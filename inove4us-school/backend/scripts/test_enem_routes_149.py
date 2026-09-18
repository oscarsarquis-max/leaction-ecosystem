"""149 — serialização do catálogo ENEM (sem DB)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enem_routes import serialize_enem  # noqa: E402


def test_serialize_habilidade():
    got = serialize_enem(
        {
            "habilidade_codigo": "ENEM-CN-H17",
            "redacao_codigo": None,
            "area_codigo": "CN",
            "competencia_numero": 5,
            "rotulo": "Relacionar informações apresentadas em diferentes formas.",
            "disciplina_nome": "Biologia",
            "disciplina_canonica": "Biologia",
            "nuance": "Métodos das ciências naturais.",
            "status": "aprovado",
        }
    )
    assert got["habilidade_codigo"] == "ENEM-CN-H17"
    assert got["tema"] == "CN · C5"
    assert got["texto_oficial"].startswith("Relacionar")
    assert got["rotulo_seletor"].startswith("ENEM-CN-H17 — ")


def test_serialize_redacao():
    got = serialize_enem(
        {
            "habilidade_codigo": None,
            "redacao_codigo": "ENEM-RED-C1",
            "area_codigo": "RED",
            "competencia_numero": 1,
            "rotulo": "Demonstrar domínio da modalidade escrita formal.",
            "disciplina_nome": "Redação",
            "disciplina_canonica": "Redação",
        }
    )
    assert got["habilidade_codigo"] == "ENEM-RED-C1"
    assert got["tema"] == "RED · C1"


if __name__ == "__main__":
    test_serialize_habilidade()
    test_serialize_redacao()
    print("ok")
