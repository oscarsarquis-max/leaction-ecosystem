"""GESTAO-007: a lista diz o que entrou e o código do lote; a correção continua no histórico."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha, validade_em


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def _linha(nome: str, codigo: str):
    return farinha(
        item_nome=nome,
        ingrediente_nome=nome,
        quantidade=1,
        unidade="kg",
        lote_codigo=codigo,
        validade=validade_em(90),
        custo=None,
        valor_pago=10,
    )


def test_lista_da_entrada_traz_os_itens_e_os_lotes(api):
    resposta = api.entrada(
        [
            _linha("Fubá Orgânico", "E20261103-12"),
            _linha("Trigo Sarraceno", "E20261103-13"),
            _linha("Sal", "E20261103-14"),
        ],
        motivo="contagem",
    )
    assert resposta.status_code == 201, resposta.text
    entrada = next(e for e in api.get("/entradas").json()["entradas"] if "E20261103-12" in e["lotes"])
    assert entrada["itens_nomes"] == ["Fubá Orgânico", "Trigo Sarraceno", "Sal"]
    assert entrada["ingredientes"] == ["Fubá Orgânico", "Trigo Sarraceno", "Sal"]
    assert entrada["lotes"] == ["E20261103-12", "E20261103-13", "E20261103-14"]
    fuba = next(i for i in api.get("/ingredientes").json()["ingredientes"] if i["nome"] == "Fubá Orgânico")
    assert fuba["itens_nomes"] == ["Fubá Orgânico"]
    assert "E20261103-12" in fuba["lotes_codigos"]


def test_corrigir_custo_na_entrada_grava_historico_e_o_selo(api):
    resposta = api.entrada([_linha("Fubá Orgânico", "E20261103-12")], motivo="contagem")
    assert resposta.status_code == 201, resposta.text
    linha = resposta.json()["linhas"][0]
    assert linha["custo_corrigido"] is False
    correcao = api.post(f"/lotes/{linha['lote_id']}/custo", {"valor_pago": 20, "motivo": "Achei a nota"})
    assert correcao.status_code == 200, correcao.text
    assert correcao.json()["historico"][0]["motivo"] == "Achei a nota"
    assert correcao.json()["historico"][0]["custo_antes"] is not None
    de_novo = api.get(f"/entradas/{resposta.json()['id']}").json()["linhas"][0]
    assert de_novo["custo_corrigido"] is True
    assert de_novo["custo_antes"] == linha["custo_unidade_base"]
    assert de_novo["custo_depois"] != de_novo["custo_antes"]
    ing = next(i for i in api.get("/ingredientes").json()["ingredientes"] if i["nome"] == "Fubá Orgânico")
    detalhe = api.get(f"/ingredientes/{ing['id']}").json()["lotes_detalhe"]
    lote = next(item for item in detalhe if item["codigo"] == "E20261103-12")
    assert lote["custo_corrigido"] is True
