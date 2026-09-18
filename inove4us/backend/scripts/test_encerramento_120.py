"""Prompt 120 — trava pós-encerramento. Sem rede, sem AWS."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desafios_routes import (  # noqa: E402
    MSG_DESAFIO_ENCERRADO,
    _status_encerramento_desafio,
)


def _aula(status: str) -> dict:
    return {"tipo": "aula_eduscrum", "status": status}


def test_zero_aulas_nao_encerra():
    enc = _status_encerramento_desafio([])
    assert enc["encerrado"] is False
    assert enc["n_aulas"] == 0


def test_uma_aberta_nao_encerra():
    enc = _status_encerramento_desafio([_aula("planejado")])
    assert enc["encerrado"] is False
    assert enc["n_abertas"] == 1


def test_metade_da_cadeia_nao_encerra():
    enc = _status_encerramento_desafio([_aula("concluido"), _aula("planejado")])
    assert enc["encerrado"] is False
    assert enc["n_concluido"] == 1
    assert enc["n_abertas"] == 1


def test_todas_concluidas_encerra():
    enc = _status_encerramento_desafio([_aula("concluido"), _aula("concluido")])
    assert enc["encerrado"] is True
    assert enc["n_abertas"] == 0


def test_mensagem_somente_leitura():
    assert "somente leitura" in MSG_DESAFIO_ENCERRADO.lower()


if __name__ == "__main__":
    test_zero_aulas_nao_encerra()
    test_uma_aberta_nao_encerra()
    test_metade_da_cadeia_nao_encerra()
    test_todas_concluidas_encerra()
    test_mensagem_somente_leitura()
    print("ok")
