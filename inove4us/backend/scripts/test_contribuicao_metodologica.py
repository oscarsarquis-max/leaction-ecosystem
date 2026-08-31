"""Faixas e selo Voz Ativa — só carimbo + aviso do loop 53."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contribuicao_metodologica import (  # noqa: E402
    FAIXA_ALTA,
    FAIXA_EQUILIBRIO,
    FAIXA_FIEL,
    calcular_faixa,
    carimbar_origem_catalogo,
    carimbar_origem_custom,
    classificar_card,
    contar_classificados,
    marcar_editado,
    montar_resumo,
    resumo_aula_contribuicao,
    voz_ativa_desbloqueada,
)


def test_resumo_aula_bate_com_carimbo():
    canon = resumo_aula_contribuicao(
        [{"id": "c1", "origem_card": "catalogo", "editado": False}]
    )
    assert canon["tem_carimbos"] is True
    assert canon["aula_canonica"] is True
    assert canon["aula_personalizada"] is False
    pers = resumo_aula_contribuicao(
        [
            {"id": "c1", "origem_card": "catalogo", "editado": False},
            {"id": "x", "origem_card": "custom"},
        ]
    )
    assert pers["aula_personalizada"] is True
    assert pers["cards_canonicos"] == 1
    assert pers["cards_personalizados"] == 1
    vazio = resumo_aula_contribuicao([{"id": "old", "titulo": "Legado"}])
    assert vazio["tem_carimbos"] is False


def test_carimbo_catalogo_e_custom():
    cat = carimbar_origem_catalogo({"id": "t1", "titulo": "Pitch"})
    assert cat["origem_card"] == "catalogo"
    assert cat["editado"] is False
    custom = carimbar_origem_custom({"id": "x", "titulo": "Meu passo"})
    assert custom["origem_card"] == "custom"
    assert classificar_card(cat) == "canonico"
    assert classificar_card(marcar_editado(cat)) == "personalizado"
    assert classificar_card(custom) == "personalizado"


def test_sem_carimbo_nao_classifica():
    assert classificar_card({"id": "old", "titulo": "Legado"}) is None
    assert classificar_card({"id": "p", "origem_card": "catalogo", "parent_card_id": "t1"}) is None


def test_faixa_predominancia_canonico():
    cards = [
        {"id": f"c{i}", "origem_card": "catalogo", "editado": False} for i in range(4)
    ] + [{"id": "x", "origem_card": "custom"}]
    assert calcular_faixa(contar_classificados(cards)) == FAIXA_FIEL


def test_faixa_uso_misto():
    cards = [
        {"id": "c1", "origem_card": "catalogo", "editado": False},
        {"id": "c2", "origem_card": "catalogo", "editado": False},
        {"id": "x1", "origem_card": "custom"},
        {"id": "x2", "origem_card": "catalogo", "editado": True},
    ]
    assert calcular_faixa(contar_classificados(cards)) == FAIXA_EQUILIBRIO


def test_faixa_predominancia_customizacao():
    cards = [
        {"id": "c1", "origem_card": "catalogo", "editado": False},
        {"id": "x1", "origem_card": "custom"},
        {"id": "x2", "origem_card": "custom"},
        {"id": "x3", "origem_card": "catalogo", "editado": True},
    ]
    assert calcular_faixa(contar_classificados(cards)) == FAIXA_ALTA


def _aula(mes_dia: str, tarefas: list) -> dict:
    return {
        "tipo": "aula_eduscrum",
        "data_evento": f"{mes_dia}T08:00:00",
        "kanban_state": {"tarefas": tarefas},
    }


def test_resumo_fiel_evolucao_e_sem_ranking():
    eventos = [
        _aula(
            "2026-08-10",
            [{"id": "c1", "origem_card": "catalogo", "editado": False}] * 3,
        ),
        _aula(
            "2026-07-10",
            [
                {"id": "p1", "origem_card": "catalogo", "editado": True},
                {"id": "p2", "origem_card": "custom"},
            ],
        ),
    ]
    resumo = montar_resumo(eventos=eventos, avisos=[], mes="2026-08")
    assert resumo["faixa"] == FAIXA_FIEL
    assert resumo["faixa_rotulo"] == "Fiel ao Roteiro"
    assert "mês passado" in resumo["evolucao_texto"]
    assert "roteiro-base" in resumo["evolucao_texto"]
    assert "posicao" not in resumo
    assert "ranking" not in resumo
    blob = str(resumo).lower()
    for proibido in ("ranking", "colegas", "média da turma", "media da turma"):
        assert proibido not in blob
    assert resumo["selos"] == []


def test_voz_ativa_so_com_incorporacao_real():
    assert voz_ativa_desbloqueada([]) is False
    assert (
        voz_ativa_desbloqueada(
            [
                {
                    "tipo": "resposta_proposta_metodologica",
                    "meta": {"resultado": "nao_incorporada"},
                }
            ]
        )
        is False
    )
    assert (
        voz_ativa_desbloqueada(
            [
                {
                    "tipo": "geral",
                    "meta": {"resultado": "aprovada"},
                }
            ]
        )
        is False
    )
    assert (
        voz_ativa_desbloqueada(
            [
                {
                    "tipo": "resposta_proposta_metodologica",
                    "meta": {"resultado": "aprovada"},
                }
            ]
        )
        is True
    )
    assert (
        voz_ativa_desbloqueada(
            [
                {
                    "tipo": "resposta_proposta_metodologica",
                    "meta_json": {"resultado": "adaptada"},
                }
            ]
        )
        is True
    )
    com = montar_resumo(
        eventos=[],
        avisos=[
            {
                "tipo": "resposta_proposta_metodologica",
                "meta": {"resultado": "adaptada"},
            }
        ],
        mes="2026-08",
    )
    assert com["selos"] == [{"id": "voz_ativa", "rotulo": "Voz Ativa"}]
    sem = montar_resumo(eventos=[], avisos=[], mes="2026-08")
    assert sem["selos"] == []


def main() -> int:
    test_resumo_aula_bate_com_carimbo()
    test_carimbo_catalogo_e_custom()
    test_sem_carimbo_nao_classifica()
    test_faixa_predominancia_canonico()
    test_faixa_uso_misto()
    test_faixa_predominancia_customizacao()
    test_resumo_fiel_evolucao_e_sem_ranking()
    test_voz_ativa_so_com_incorporacao_real()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
