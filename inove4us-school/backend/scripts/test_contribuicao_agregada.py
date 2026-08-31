"""Agregado do Radar — carimbo preciso, sem professor, sem faixa."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contribuicao_agregada import (  # noqa: E402
    agregar_aulas,
    classificar_aula,
    curadoria_foi_incorporada,
    montar_bloco_radar,
)


def test_aula_usa_bloco_contribuicao():
    assert (
        classificar_aula(
            {
                "contribuicao": {
                    "tem_carimbos": True,
                    "aula_personalizada": False,
                    "aula_canonica": True,
                }
            }
        )
        == "canonica"
    )
    assert (
        classificar_aula(
            {
                "contribuicao": {
                    "tem_carimbos": True,
                    "aula_personalizada": True,
                }
            }
        )
        == "personalizada"
    )


def test_aula_pelos_cards_carimbados():
    assert (
        classificar_aula(
            {
                "cards": [
                    {"id": "c1", "origem_card": "catalogo", "editado": False},
                ]
            }
        )
        == "canonica"
    )
    assert (
        classificar_aula(
            {
                "cards": [
                    {"id": "c1", "origem_card": "catalogo", "editado": True},
                    {"id": "x", "origem_card": "custom"},
                ]
            }
        )
        == "personalizada"
    )


def test_sem_carimbo_nao_usa_proxy():
    assert (
        classificar_aula(
            {
                "has_teacher_adaptations": True,
                "texto_sugestao": "mudei o passo",
                "cards": [{"id": "old", "titulo": "Sem objetivo"}],
            }
        )
        is None
    )


def test_agregado_percentuais_sem_professor():
    mesas = [
        {"contribuicao": {"tem_carimbos": True, "aula_personalizada": False}},
        {"contribuicao": {"tem_carimbos": True, "aula_personalizada": False}},
        {"contribuicao": {"tem_carimbos": True, "aula_personalizada": True}},
        {"cards": [{"titulo": "legado"}]},
    ]
    agg = agregar_aulas(mesas)
    assert agg["aulas_com_carimbo"] == 3
    assert agg["percentual_roteiro_base"] == 67
    assert agg["percentual_personalizacao"] == 33
    for proibido in ("professor", "vinculo", "faixa", "ranking", "posicao"):
        assert proibido not in agg


def test_incorporacao_e_voz_ativa():
    assert curadoria_foi_incorporada({"status_analise": "pendente"}) is False
    assert (
        curadoria_foi_incorporada(
            {"status_analise": "incorporado", "resultado_analise": "nao_incorporada"}
        )
        is False
    )
    assert curadoria_foi_incorporada({"status_analise": "incorporado"}) is True
    assert (
        curadoria_foi_incorporada(
            {"status_analise": "incorporado", "resultado_analise": "adaptada"}
        )
        is True
    )
    bloco = montar_bloco_radar(mesas=[], sugestoes_incorporadas=2)
    assert bloco["sugestoes_incorporadas"] == 2
    assert "faixa" not in bloco
    assert "professor" not in bloco


def main() -> int:
    test_aula_usa_bloco_contribuicao()
    test_aula_pelos_cards_carimbados()
    test_sem_carimbo_nao_usa_proxy()
    test_agregado_percentuais_sem_professor()
    test_incorporacao_e_voz_ativa()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
