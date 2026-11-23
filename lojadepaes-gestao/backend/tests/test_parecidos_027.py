"""GESTAO-027: duplicidade estrita (sem marca nem palavra genérica); busca continua solta."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro-027", "dono", org="padaria-027"))


def novo(api, nome, base="g", **extra):
    return api.post("/ingredientes", {"nome": nome, "unidade_base": base, **extra})


def _entrada(api, *, item_nome, marca, ingrediente_nome):
    assert (
        api.entrada(
            [
                farinha(
                    item_nome=item_nome,
                    marca=marca,
                    ingrediente_nome=ingrediente_nome,
                )
            ]
        ).status_code
        == 201
    )
    return api.ingrediente(ingrediente_nome)


def test_especial_nuvola_e_parecido_da_tipo_0_pelo_item(api):
    tipo0 = _entrada(
        api,
        item_nome="Farinha de Trigo Tipo Nuvola",
        marca="Caputo",
        ingrediente_nome="Farinha de trigo tipo 0",
    )
    resp = novo(api, "Farinha de Trigo Especial Nuvola", categoria="Farinhas")
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "ingrediente_parecido"
    assert any(p["id"] == tipo0 for p in detalhe["parecidos"])
    assert any("tipo 0" in p["nome"].lower() for p in detalhe["parecidos"])


def test_semolina_caputo_nao_e_par_da_tipo_0_caputo(api):
    _entrada(
        api,
        item_nome="Farinha de Trigo Tipo Nuvola",
        marca="Caputo",
        ingrediente_nome="Farinha de trigo tipo 0",
    )
    _entrada(
        api,
        item_nome="Farinha de Trigo Sêmola",
        marca="Caputo",
        ingrediente_nome="Farinha de semolina",
    )
    pares = api.get("/ingredientes").json()["pares_parecidos"]
    nomes = {(p["a"]["nome"], p["b"]["nome"]) for p in pares} | {
        (p["b"]["nome"], p["a"]["nome"]) for p in pares
    }
    assert ("Farinha de semolina", "Farinha de trigo tipo 0") not in nomes
    assert ("Farinha de trigo tipo 0", "Farinha de semolina") not in nomes


def test_cevada_integral_nao_e_par_da_nita_integral(api):
    _entrada(
        api,
        item_nome="Farinha de Cevada Integral",
        marca="",
        ingrediente_nome="Farinha de Cevada",
    )
    _entrada(
        api,
        item_nome="Nita 100% Integral",
        marca="Nita",
        ingrediente_nome="Farinha de trigo integral",
    )
    pares = api.get("/ingredientes").json()["pares_parecidos"]
    nomes = {(p["a"]["nome"], p["b"]["nome"]) for p in pares} | {
        (p["b"]["nome"], p["a"]["nome"]) for p in pares
    }
    assert ("Farinha de Cevada", "Farinha de trigo integral") not in nomes


def test_par_marcado_diferente_some_e_nao_bloqueia(api):
    tipo0 = _entrada(
        api,
        item_nome="Farinha de Trigo Tipo Nuvola",
        marca="Caputo",
        ingrediente_nome="Farinha de trigo tipo 0",
    )
    # Sem “Especial”/“tipo” no nome: senão se_contradizem tira o par da lista (0 × especial).
    segundo = novo(api, "Farinha Nuvola", categoria="Farinhas", confirmado_inexistente=True)
    assert segundo.status_code == 201, segundo.text
    segundo_id = segundo.json()["id"]
    pares = api.get("/ingredientes").json()["pares_parecidos"]
    assert any({p["a"]["id"], p["b"]["id"]} == {tipo0, segundo_id} for p in pares), pares
    assert any(
        p.get("motivo") for p in pares if {p["a"]["id"], p["b"]["id"]} == {tipo0, segundo_id}
    )

    assert api.post("/ingredientes/distintos", {"a_id": tipo0, "b_id": segundo_id}).status_code == 204
    assert api.get("/ingredientes").json()["pares_parecidos"] == []

    # Edição entre o par marcado não bloqueia mais (ignorar_id + distintos).
    edit = api.patch(f"/ingredientes/{segundo_id}", {"nome": "Farinha Nuvola da casa"})
    assert edit.status_code == 200, edit.text


def test_busca_caputo_acha_as_duas_farinhas(api):
    tipo0 = _entrada(
        api,
        item_nome="Farinha de Trigo Tipo Nuvola",
        marca="Caputo",
        ingrediente_nome="Farinha de trigo tipo 0",
    )
    semolina = _entrada(
        api,
        item_nome="Farinha de Trigo Sêmola",
        marca="Caputo",
        ingrediente_nome="Farinha de semolina",
    )
    corpo = api.get("/ingredientes/busca", q="caputo").json()
    ids = {i["id"] for i in corpo["da_padaria"]}
    assert tipo0 in ids
    assert semolina in ids
