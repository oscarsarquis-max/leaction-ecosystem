"""GESTAO-015: inóculo de cultura viva, ciclo e custo em regime."""

from datetime import date

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def _levain(api, *, cultura_viva: bool):
    return _produto(
        api,
        "Levain",
        uso_venda=False,
        uso_componente=True,
        cultura_viva=cultura_viva,
        unidade_venda="un",
        confirmado_inexistente=True,
    )


def _linhas(api, levain_id: str):
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua_id = api.ingrediente("Água", "g", "Líquidos")
    return farinha_id, agua_id, [
        {"ingrediente_id": farinha_id, "quantidade": 100, "unidade": "g"},
        {"ingrediente_id": agua_id, "quantidade": 100, "unidade": "g"},
        {"ingrediente_id": levain_id, "quantidade": 50, "unidade": "g", "funcao": "inoculo", "observacao": "do pote da véspera"},
    ]


def test_inoculo_do_proprio_levain_entra_e_custa_em_regime(api):
    api.ingrediente("Farinha de trigo", "g", "Farinhas")
    assert api.entrada([farinha(quantidade=1, custo=10)]).status_code == 201
    levain = _levain(api, cultura_viva=True)
    _farinha_id, _agua_id, linhas = _linhas(api, levain["ingrediente_id"])
    salvo = _put(api, levain["id"], linhas=linhas)
    assert salvo.status_code == 200, salvo.text
    corpo = salvo.json()
    inoculo = next(linha for linha in corpo["linhas"] if linha["funcao"] == "inoculo")
    assert inoculo["ingrediente_id"] == levain["ingrediente_id"]
    assert inoculo["observacao"] == "do pote da véspera"
    # 100 g × R$ 0,01 = R$ 1,00. Água sem custo. Massa 250 g − inóculo 50 g.
    assert corpo["custo_por_grama"] == pytest.approx(0.005)
    assert inoculo["percentual_padeiro"] == pytest.approx(50)


def test_sem_cultura_viva_a_autorreferencia_e_ciclo(api):
    levain = _levain(api, cultura_viva=False)
    _farinha_id, _agua_id, linhas = _linhas(api, levain["ingrediente_id"])
    resposta = _put(api, levain["id"], linhas=linhas)
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert detalhe["codigo"] == "ciclo_receita"
    assert detalhe["linha"] == 3
    assert "Levain usa Levain" in detalhe["mensagem"]


def test_autorreferencia_fora_de_inoculo_e_ciclo(api):
    levain = _levain(api, cultura_viva=True)
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    resposta = _put(
        api,
        levain["id"],
        linhas=[
            {"ingrediente_id": farinha_id, "quantidade": 100, "unidade": "g"},
            {"ingrediente_id": levain["ingrediente_id"], "quantidade": 50, "unidade": "g", "funcao": "massa"},
        ],
    )
    assert resposta.status_code == 422
    assert resposta.json()["detail"]["codigo"] == "ciclo_receita"
    assert resposta.json()["detail"]["linha"] == 2


def test_ciclo_entre_produtos_continua_422(api):
    levain = _levain(api, cultura_viva=True)
    pao = _produto(api, "Pão X", uso_componente=True, confirmado_inexistente=True)
    ida = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": levain["ingrediente_id"], "quantidade": 50, "unidade": "g"}],
    )
    assert ida.status_code == 200, ida.text
    volta = _put(
        api,
        levain["id"],
        linhas=[
            {"ingrediente_id": pao["ingrediente_id"], "quantidade": 50, "unidade": "g"},
            {"ingrediente_id": levain["ingrediente_id"], "quantidade": 20, "unidade": "g", "funcao": "inoculo"},
        ],
    )
    assert volta.status_code == 422
    detalhe = volta.json()["detail"]
    assert detalhe["codigo"] == "ciclo_receita"
    assert detalhe["mensagem"] == "Levain usa Pão X, que usa Levain."


def test_inoculo_maior_ou_igual_a_massa_da_erro(api):
    levain = _levain(api, cultura_viva=True)
    resposta = _put(
        api,
        levain["id"],
        linhas=[{"ingrediente_id": levain["ingrediente_id"], "quantidade": 50, "unidade": "g", "funcao": "inoculo"}],
    )
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert detalhe["mensagem"] == "O inóculo não pode ser maior que a massa."
    assert detalhe["linha"] == 1


def test_comanda_mostra_observacao_e_inoculo(api):
    levain = _levain(api, cultura_viva=True)
    _farinha_id, _agua_id, linhas = _linhas(api, levain["ingrediente_id"])
    ficha = _put(
        api,
        levain["id"],
        linhas=linhas,
        formato="forma_enriquecida",
        peso_unidade_g=500,
        unidades_desejadas=1,
    )
    assert ficha.status_code == 200, ficha.text
    assert ficha.json()["peso_unidade_g"] == 500
    publicada = api.post(f"/receitas/{levain['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    hoje = date.fromisoformat(api.get("/producao").json()["hoje"])
    manha = next(item for item in api.get("/producao/fornadas").json()["fornadas"] if item["nome"] == "Manhã 05:00")
    ordem = api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": levain["id"], "unidades": 1},
    )
    assert ordem.status_code == 201, ordem.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco.get("aviso") is None, bloco
    inoculo = next(linha for linha in bloco["linhas"] if linha["funcao"] == "inoculo")
    assert inoculo["nome"].startswith("Inóculo: ")
    assert inoculo["nome"].endswith("de Levain do preparo anterior")
    assert inoculo["observacao"] == "do pote da véspera"
