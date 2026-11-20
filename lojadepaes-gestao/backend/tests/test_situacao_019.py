"""GESTAO-019: GET /produtos devolve receita (situacao, versao, publicada, linhas)."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def _por_nome(lista, nome):
    return next(p for p in lista["produtos"] if p["nome"] == nome)


def test_lista_devolve_receita_nos_quatro_casos_e_null_no_comprado(api):
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")

    publicada = _produto(api, "Publicada v1")
    assert _put(
        api,
        publicada["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
    ).status_code == 200
    assert api.post(f"/receitas/{publicada['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200

    rascunho_v2 = _produto(api, "Rascunho v2 com v1", confirmado_inexistente=True)
    assert _put(
        api,
        rascunho_v2["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 400, "unidade": "g"}],
    ).status_code == 200
    assert api.post(f"/receitas/{rascunho_v2['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200
    assert _put(
        api,
        rascunho_v2["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 450, "unidade": "g"}],
    ).status_code == 200

    rascunho_com_linhas = _produto(api, "Rascunho com linhas", confirmado_inexistente=True)
    assert _put(
        api,
        rascunho_com_linhas["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 300, "unidade": "g"}],
    ).status_code == 200

    sem_linhas = _produto(api, "Rascunho sem linhas", confirmado_inexistente=True)

    entrada = api.entrada([farinha(item_nome="Chocolate em barra", marca="Garoto")]).json()
    item_id = entrada["linhas"][0]["item_id"]
    comprado = api.post(
        "/produtos",
        {
            "nome": "Chocolate Garoto",
            "modalidade": "comprado",
            "uso_venda": True,
            "uso_componente": False,
            "unidade_venda": "un",
            "item_estoque_id": item_id,
            "confirmado_inexistente": True,
        },
    )
    assert comprado.status_code == 201, comprado.text

    lista = api.get("/produtos").json()

    pub = _por_nome(lista, "Publicada v1")
    assert pub["receita"] == {"situacao": "publicada", "versao": 1, "publicada": True, "linhas": 1}

    v2 = _por_nome(lista, "Rascunho v2 com v1")
    assert v2["receita"] == {"situacao": "rascunho", "versao": 2, "publicada": True, "linhas": 1}

    rasc = _por_nome(lista, "Rascunho com linhas")
    assert rasc["receita"] == {"situacao": "rascunho", "versao": 1, "publicada": False, "linhas": 1}

    vazio = _por_nome(lista, "Rascunho sem linhas")
    assert vazio["receita"] == {"situacao": "rascunho", "versao": 1, "publicada": False, "linhas": 0}

    comp = _por_nome(lista, "Chocolate Garoto")
    assert comp["receita"] is None
