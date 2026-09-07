"""Desempenho experimental — componentes por professor, sem nota nem ranking."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desempenho_professores import montar_linhas  # noqa: E402

FORBIDDEN = {"nota", "score", "ranking", "rank", "media", "média"}


def _aula(**kwargs):
    base = {
        "professor_vinculo_id": "p-ana",
        "professor_email": "ana.souza@escola.br",
        "professor_nome": "Ana Souza",
        "tipo_aula": "dia_a_dia",
        "metodologia_nome": "Estação",
        "mesa": {},
        "has_curadoria": False,
        "turma_id": "t1",
    }
    base.update(kwargs)
    return base


def test_ordena_por_nome_nao_por_volume():
    aulas = [
        _aula(
            professor_vinculo_id="p-bruno",
            professor_email="bruno.lima@escola.br",
            professor_nome="Bruno Lima",
            metodologia_nome="Roda",
        ),
        _aula(
            professor_vinculo_id="p-ana",
            professor_nome="Ana Souza",
            metodologia_nome="Estação",
        ),
        _aula(
            professor_vinculo_id="p-bruno",
            professor_email="bruno.lima@escola.br",
            professor_nome="Bruno Lima",
            tipo_aula="desafio",
            metodologia_nome="Sala de aula invertida",
            mesa={"has_pei_adaptations": True},
            has_curadoria=True,
            turma_id="t2",
        ),
    ]
    linhas = montar_linhas(aulas)
    assert [r["professor_nome"] for r in linhas] == ["Ana Souza", "Bruno Lima"]
    bruno = linhas[1]
    assert bruno["aulas_total"] == 2
    assert bruno["aulas_dia_a_dia"] == 1
    assert bruno["aulas_desafio"] == 1
    assert bruno["metodologias_distintas"] == 2
    assert bruno["curadoria_enviadas"] == 1
    assert bruno["pei"]["aulas_com_adaptacao"] == 1
    ana = linhas[0]
    assert ana["aulas_total"] == 1
    assert ana["metodologias_distintas"] == 1


def test_adesao_canonica_vs_livre():
    aulas = [
        _aula(
            mesa={
                "contribuicao": {
                    "tem_carimbos": True,
                    "aula_personalizada": False,
                }
            }
        ),
        _aula(
            professor_vinculo_id="p-ana",
            mesa={
                "contribuicao": {
                    "tem_carimbos": True,
                    "aula_personalizada": True,
                }
            },
        ),
        _aula(professor_vinculo_id="p-ana", mesa={"titulo": "sem carimbo"}),
    ]
    linha = montar_linhas(aulas)[0]
    assert linha["adesao"] == {
        "canonica": 1,
        "personalizada": 1,
        "sem_carimbo": 1,
    }


def test_payload_sem_nota_nem_ranking():
    linhas = montar_linhas(
        [
            _aula(),
            _aula(
                professor_vinculo_id="p-carla",
                professor_nome="Carla Dias",
                professor_email="carla@escola.br",
            ),
        ]
    )
    blob = str(linhas).casefold()
    for word in FORBIDDEN:
        assert word not in blob
    for row in linhas:
        assert "nota" not in row
        assert "score" not in row
        assert "ranking" not in row


if __name__ == "__main__":
    test_ordena_por_nome_nao_por_volume()
    test_adesao_canonica_vs_livre()
    test_payload_sem_nota_nem_ranking()
    print("ok")
