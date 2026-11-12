"""GESTAO-018: preparo da casa rende em peso; hidratação total; sem falso fermento."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, validade_em
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def _compra(api, nome, custo_kg):
    resposta = api.entrada(
        [
            {
                "item_nome": nome,
                "marca": "Casa",
                "unidade_controle": "massa",
                "ingrediente_nome": nome,
                "quantidade": 1,
                "unidade": "kg",
                "validade": validade_em(120),
                "custo": custo_kg,
            }
        ]
    )
    assert resposta.status_code == 201, resposta.text


def _levain(api):
    integral = api.ingrediente("Farinha integral", "g", "Farinhas")
    centeio = api.ingrediente("Farinha de centeio", "g", "Farinhas")
    tipo0 = api.ingrediente("Farinha tipo 0", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    mel = api.ingrediente("Mel", "g", "Outros")
    _compra(api, "Farinha integral", 7)
    _compra(api, "Farinha de centeio", 22)
    _compra(api, "Farinha tipo 0", 37.9)
    produto = _produto(
        api,
        "Levain do Oscar",
        uso_venda=False,
        uso_componente=True,
        cultura_viva=True,
        unidade_venda="un",
        confirmado_inexistente=True,
    )
    return produto, {
        "inoculo": produto["ingrediente_id"],
        "integral": integral,
        "centeio": centeio,
        "tipo0": tipo0,
        "agua": agua,
        "mel": mel,
    }


def _linhas(ids, inoculo_g):
    return [
        {"ingrediente_id": ids["inoculo"], "quantidade": inoculo_g, "unidade": "g", "funcao": "inoculo"},
        {"ingrediente_id": ids["integral"], "quantidade": 50, "unidade": "g"},
        {"ingrediente_id": ids["centeio"], "quantidade": 50, "unidade": "g"},
        {"ingrediente_id": ids["tipo0"], "quantidade": 100, "unidade": "g"},
        {"ingrediente_id": ids["agua"], "quantidade": 100, "unidade": "g"},
        {"ingrediente_id": ids["mel"], "quantidade": 20, "unidade": "g"},
    ]


def _gravar(api, produto_id, ids, inoculo_g):
    return _put(
        api,
        produto_id,
        linhas=_linhas(ids, inoculo_g),
        processo={"percentual": 5, "origem": "manual", "motivo": "teste da area"},
        peso_unidade_g=500,
        formato="livre",
        unidades_desejadas=8,
        coccao={"percentual": 12, "origem": "manual", "motivo": "teste da area"},
    )


def _codigos(corpo):
    return [item["codigo"] for item in corpo["verificacoes"]["pendencias"]]


def test_levain_rende_em_peso_hidrata_e_publica_399_g(api):
    produto, ids = _levain(api)
    salvo = _gravar(api, produto["id"], ids, 100)
    assert salvo.status_code == 200, salvo.text
    corpo = salvo.json()
    assert corpo["modo_rendimento"] == "massa"
    massa = corpo["rendimento_massa"]
    assert massa["massa_g"] == pytest.approx(420)
    assert massa["processo_pct"] == pytest.approx(5)
    assert massa["rende_g"] == 399
    assert massa["reserva_g"] == pytest.approx(100)
    assert massa["disponivel_g"] == pytest.approx(299)
    # 5,24 / 299 × 1000 = 17,525… → 17,53 na meia para cima.
    assert massa["custo_por_kg"] == pytest.approx(17.53)
    assert corpo["custo_parcial"] is True
    assert corpo["custo_por_grama"] == pytest.approx(0.01753)
    agua = corpo["hidratacao"]
    assert agua["farinha_g"] == pytest.approx(262.5)
    assert agua["agua_g"] == pytest.approx(131.25)
    assert agua["percentual"] == pytest.approx(50.0)
    assert "sem_fermento" not in _codigos(corpo)
    assert corpo["peso_unidade_g"] is None
    assert corpo["formato"] is None
    assert corpo["unidades_desejadas"] is None
    publicada = api.post(f"/receitas/{produto['id']}/publicar")
    assert publicada.status_code == 200, publicada.text
    assert publicada.json()["rendimento_quantidade"] == pytest.approx(399)
    assert publicada.json()["rendimento_unidade"] == "g"


def test_pao_de_venda_sem_fermento_continua_em_pecas(api):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    pao = _produto(api, "Pão de venda sem fermento", uso_venda=True, uso_componente=False)
    salvo = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 350, "unidade": "g"},
        ],
        peso_unidade_g=500,
        formato="livre",
        unidades_desejadas=2,
        processo={"percentual": 5, "origem": "manual", "motivo": "teste da area"},
        coccao={"percentual": 12, "origem": "manual", "motivo": "teste da area"},
    )
    assert salvo.status_code == 200, salvo.text
    corpo = salvo.json()
    assert corpo["modo_rendimento"] == "unidades"
    assert corpo["rendimento_massa"] is None
    assert corpo["peso_unidade_g"] == pytest.approx(500)
    assert corpo["formato"] == "livre"
    assert "sem_fermento" in _codigos(corpo)
    assert corpo["rendimento_unidade"] == "un"
    assert corpo["hidratacao"]["percentual"] == pytest.approx(70.0)


def test_pao_com_levain_conta_a_farinha_e_a_agua_de_dentro(api):
    produto, ids = _levain(api)
    assert _gravar(api, produto["id"], ids, 100).status_code == 200
    assert api.post(f"/receitas/{produto['id']}/publicar").status_code == 200
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    pao = _produto(api, "Pão com levain", uso_venda=True, uso_componente=False)
    salvo = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 100, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 80, "unidade": "g"},
            {"ingrediente_id": ids["inoculo"], "quantidade": 420, "unidade": "g"},
        ],
    )
    assert salvo.status_code == 200, salvo.text
    agua_total = salvo.json()["hidratacao"]
    assert agua_total["farinha_g"] == pytest.approx(362.5)
    assert agua_total["agua_g"] == pytest.approx(211.25)
    assert agua_total["percentual"] == pytest.approx(58.3)


def test_reserva_maior_que_o_rendimento_bloqueia_a_publicacao(api):
    produto, ids = _levain(api)
    quinhentos = _gravar(api, produto["id"], ids, 500)
    assert quinhentos.status_code == 200, quinhentos.text
    # 820 g × 0,95 = 779 g; 779 − 500 = 279 g ainda disponíveis.
    assert quinhentos.json()["rendimento_massa"]["disponivel_g"] == pytest.approx(279)
    assert "reserva_maior" not in _codigos(quinhentos.json())
    maior = _gravar(api, produto["id"], ids, 6500)
    assert maior.status_code == 200, maior.text
    assert maior.json()["rendimento_massa"]["disponivel_g"] < 0
    assert "reserva_maior" in _codigos(maior.json())
    negado = api.post(f"/receitas/{produto['id']}/publicar")
    assert negado.status_code == 422
    assert negado.json()["detail"]["codigo"] == "reserva_maior"
