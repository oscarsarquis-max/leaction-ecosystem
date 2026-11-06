"""GESTAO-012B: a conta é do servidor e a padaria avisa."""

from decimal import Decimal

import pytest
from app.domain.verificacoes import (
    aplicar_substituicao,
    calibrar_confianca,
    percentual_dos_gramas,
    verificar,
)

from tests.test_gigio import _pedir, _produto, _resposta
from tests.test_receitas import _put

pytest_plugins = ["tests.test_gigio"]


def test_focaccia_390_em_625_mostra_62_4_e_nao_78(api, falso):
    mostrado = percentual_dos_gramas(Decimal("390"), Decimal("625"))
    assert mostrado == Decimal("62.4")
    assert mostrado != Decimal("78")
    from app.db.session import get_engine
    from app.domain.gigio.servico import ensaiar
    from app.models.organizacao import Organizacao
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    falso.script.append(
        _resposta(
            [
                {"ingrediente": "Farinha de trigo", "quantidade_g": 500, "percentual": 80, "confianca": "baixa", "motivo": "Farinha."},
                {"ingrediente": "Sêmola", "quantidade_g": 125, "percentual": 20, "confianca": "baixa", "motivo": "Sêmola."},
                {
                    "ingrediente": "Água",
                    "quantidade_g": 390,
                    "percentual": 78,
                    "faixa_min": 70,
                    "faixa_max": 90,
                    "confianca": "alta",
                    "motivo": "Hidratação.",
                },
            ]
        )
    )
    falso.script.append(
        _resposta(
            [
                {"ingrediente": "Fermento", "quantidade_g": 12, "percentual": 2, "confianca": "baixa", "motivo": "Fermento."},
            ]
        )
    )
    with Session(get_engine()) as db:
        org = db.scalars(select(Organizacao).where(Organizacao.nome_curto == "loja")).one()
        resultado = ensaiar(
            db,
            org.id,
            titulo="Focaccia",
            familia="Focaccia",
            descricao="Focaccia alta.",
            base=[],
        )
        db.rollback()
    agua = next(linha for linha in resultado["linhas"] if linha["nome"] == "Água")
    assert agua["quantidade"] == 390
    assert agua["percentual"] == pytest.approx(62.4)
    assert resultado["farinha_contida_g"] == pytest.approx(625)


def test_acucar_de_10_porcento_vira_30_gramas(api, falso):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    api.ingrediente("Açúcar", "g", "Açúcares e mel")
    massa = _produto(api, "Massa de 300", uso_venda=False, uso_componente=True, confirmado_inexistente=True)
    salvo = _put(
        api,
        massa["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 300, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 200, "unidade": "g"},
        ],
        rendimento_quantidade=500,
        rendimento_unidade="g",
    )
    assert salvo.status_code == 200, salvo.text
    assert api.post(f"/receitas/{massa['id']}/publicar").status_code == 200
    pao = _produto(api, "Pão de canela sobre 300")
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Açúcar",
                    "quantidade_g": 50,
                    "percentual": 10,
                    "faixa_min": 8,
                    "faixa_max": 15,
                    "confianca": "alta",
                    "motivo": "Doçura.",
                }
            ]
        )
    )
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Fermento",
                    "quantidade_g": 9,
                    "percentual": 3,
                    "confianca": "alta",
                    "motivo": "Fermento.",
                }
            ]
        )
    )
    resposta = _pedir(api, pao["id"], massa_base_id=massa["id"], massa_base_quantidade=500)
    assert resposta.status_code == 200, resposta.text
    acucar = next(linha for linha in resposta.json()["linhas"] if linha["nome"] == "Açúcar")
    assert acucar["quantidade"] == 30
    assert acucar["percentual"] == pytest.approx(10)
    assert 8 <= acucar["percentual"] <= 15


def test_sem_fermento_faz_uma_nova_chamada(api, falso):
    pao = _produto(api, "Pão sem fermento")
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Açúcar",
                    "quantidade_g": 20,
                    "percentual": 4,
                    "confianca": "media",
                    "motivo": "Doçura.",
                }
            ]
        )
    )
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Fermento biológico",
                    "quantidade_g": 5,
                    "percentual": 1,
                    "confianca": "alta",
                    "motivo": "Fermento.",
                }
            ]
        )
    )
    resposta = _pedir(api, pao["id"], descricao="Pão simples, sem longa maturação.")
    assert resposta.status_code == 200, resposta.text
    assert len(falso.calls) == 2
    assert any("ermento" in linha["nome"] for linha in resposta.json()["linhas"])


def test_sem_fermento_depois_da_segunda_chamada_pede_confirmacao(api, falso):
    pao = _produto(api, "Pão ainda sem fermento")
    falso.script.append(_resposta([]))
    falso.script.append(_resposta([]))
    resposta = _pedir(api, pao["id"], descricao="Pão simples.")
    assert resposta.status_code == 200, resposta.text
    assert len(falso.calls) == 2
    assert any(item["mensagem"] == "Falta o fermento." for item in resposta.json()["verificacoes"]["pendencias"])
    aplicado = api.post(
        f"/receitas/{pao['id']}/aplicar-sugestao",
        {"linhas": [], "confirmar_sem_fermento": False},
    )
    assert aplicado.status_code == 422
    assert "fermento" in aplicado.json()["detail"]["mensagem"].lower()


def test_sal_a_3_3_avisa_e_sal_repetido_na_massa_avisa():
    avisos = verificar(
        [{"nome": "Sal", "categoria": "Sal e temperos", "quantidade_g": Decimal("10"), "componente": False}],
        farinha=Decimal("300"),
        familia="Pão Sovado",
        componentes=[
            {
                "nome": "Massa sovada",
                "folhas": [
                    {"nome": "Farinha de trigo", "categoria": "Farinhas", "quantidade_g": Decimal("300")},
                    {"nome": "Sal", "categoria": "Sal e temperos", "quantidade_g": Decimal("0")},
                ],
            }
        ],
    )
    textos = [aviso["mensagem"] for aviso in avisos["avisos"]]
    assert any("3,3 %" in texto for texto in textos)
    assert any("Sal já está na Massa sovada" in texto for texto in textos)


def test_alta_que_nao_e_fixa_nem_padrao_e_rebaixada():
    assert calibrar_confianca("alta", fixa=False, padrao=False, descrita=True) == "media"
    assert calibrar_confianca("alta", fixa=False, padrao=False, descrita=False) == "baixa"
    assert calibrar_confianca("alta", fixa=True, padrao=False, descrita=False) == "alta"
    assert calibrar_confianca("baixa", fixa=False, padrao=True, descrita=False) == "alta"


def test_substituicao_mantem_a_farinha_total():
    folhas = aplicar_substituicao(
        [
            {"nome": "Farinha de trigo", "categoria": "Farinhas", "quantidade_g": Decimal("500")},
            {"nome": "Água", "categoria": "Líquidos", "quantidade_g": Decimal("300")},
        ],
        "Farinha integral",
        Decimal("15"),
    )
    total = sum(Decimal(str(folha["quantidade_g"])) for folha in folhas if folha["categoria"] == "Farinhas")
    assert total == Decimal("500")
    assert any(folha["nome"] == "Farinha integral" and Decimal(str(folha["quantidade_g"])) == 75 for folha in folhas)
    assert any(folha["nome"] == "Farinha de trigo" and Decimal(str(folha["quantidade_g"])) == 425 for folha in folhas)
