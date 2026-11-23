"""GESTAO-026: uma regra só de busca e duplicidade, com o item comprado."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha
from tests.test_ingrediente_busca import novo


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro-026", "dono", org="padaria-026"))


def _entrada_nuvola(api, *, ingrediente="Farinha de trigo tipo 0", ativo=True):
    assert (
        api.entrada(
            [
                farinha(
                    item_nome="Farinha de Trigo Tipo Nuvola",
                    marca="Caputo",
                    ingrediente_nome=ingrediente,
                )
            ]
        ).status_code
        == 201
    )
    if not ativo:
        # junta em outro e deixa inativo (sem item no ativo)
        mantem = api.ingrediente("Farinha reserva 026", "g", "Farinhas")
        origem = api.ingrediente(ingrediente)
        assert api.post("/ingredientes/juntar", {"mantem_id": mantem, "remove_id": origem}).status_code == 200
        return mantem
    return api.ingrediente(ingrediente)


def test_nuvola_acha_tipo_0_pelo_item(api):
    tipo0 = _entrada_nuvola(api)
    corpo = api.get("/ingredientes/busca", q="nuvola").json()
    assert [i["id"] for i in corpo["da_padaria"]] == [tipo0]
    assert corpo["da_padaria"][0]["achado_por"] == "Farinha de Trigo Tipo Nuvola"
    assert "Farinha de Trigo Tipo Nuvola" not in [c["nome"] for c in corpo["do_catalogo"]]


def test_caputo_marca_acha_a_mesma_farinha(api):
    tipo0 = _entrada_nuvola(api)
    corpo = api.get("/ingredientes/busca", q="caputo").json()
    assert tipo0 in [i["id"] for i in corpo["da_padaria"]]
    achado = next(i for i in corpo["da_padaria"] if i["id"] == tipo0)
    assert achado["achado_por"]
    assert "Nuvola" in achado["achado_por"] or "Caputo" in achado["achado_por"]


def test_item_de_inativo_nao_aparece(api):
    _entrada_nuvola(api, ativo=True)
    tipo0 = api.ingrediente("Farinha de trigo tipo 0")
    mantem = api.ingrediente("Farinha reserva ativa 026", "g", "Farinhas")
    assert api.post("/ingredientes/juntar", {"mantem_id": mantem, "remove_id": tipo0}).status_code == 200
    corpo = api.get("/ingredientes/busca", q="nuvola").json()
    ids = [i["id"] for i in corpo["da_padaria"]]
    assert tipo0 not in ids
    # o ativo que recebeu o item deve aparecer
    assert mantem in ids


def test_acerto_por_nome_vem_antes_do_item(api):
    por_nome = novo(api, "Nuvola", categoria="Farinhas").json()["id"]
    por_item = _entrada_nuvola(api, ingrediente="Farinha de trigo tipo 0")
    corpo = api.get("/ingredientes/busca", q="nuvola").json()
    ids = [i["id"] for i in corpo["da_padaria"]]
    assert ids[0] == por_nome
    assert por_item in ids


def test_cadastro_especial_nuvola_e_barrado_como_parecido(api):
    _entrada_nuvola(api)
    resp = novo(api, "Farinha de Trigo Especial Nuvola", categoria="Farinhas")
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "ingrediente_parecido"
    assert any("tipo 0" in p["nome"].lower() for p in detalhe["parecidos"])


def test_pares_parecidos_pegam_dois_ligados_pelo_item(api):
    tipo0 = _entrada_nuvola(api)
    # força um segundo com nome parecido ao item (confirma que não existe para passar do 409)
    segundo = novo(
        api,
        "Farinha de Trigo Tipo Nuvola",
        categoria="Farinhas",
        confirmado_inexistente=True,
    )
    assert segundo.status_code == 201, segundo.text
    pares = api.get("/ingredientes").json()["pares_parecidos"]
    ids = {(p["a"]["id"], p["b"]["id"]) for p in pares} | {(p["b"]["id"], p["a"]["id"]) for p in pares}
    assert (tipo0, segundo.json()["id"]) in ids or (segundo.json()["id"], tipo0) in ids
