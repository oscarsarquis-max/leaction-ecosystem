"""GESTAO-025: excluir ingrediente cadastrado por engano."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import entrar
from tests.test_estoque import Api, farinha
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro-025", "dono", org="padaria-025"))


def _excluir(api, ingrediente_id):
    return api.c.delete(f"/api/v1/ingredientes/{ingrediente_id}", headers=api.h)


def test_sem_nada_e_excluido(api):
    ing_id = api.ingrediente("Farinha de Trigo Especial Nuvola", "g", "Farinhas")
    resp = _excluir(api, ing_id)
    assert resp.status_code == 204, resp.text
    assert api.get(f"/ingredientes/{ing_id}").status_code == 404


def test_com_item_da_409(api):
    assert api.entrada([farinha(item_nome="Farinha Nuvola item", ingrediente_nome="Farinha com item 025")]).status_code == 201
    ing_id = api.ingrediente("Farinha com item 025")
    resp = _excluir(api, ing_id)
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "em_uso"
    assert "item" in detalhe["mensagem"].lower()
    assert "Juntar" in detalhe["mensagem"]


def test_em_receita_da_409(api):
    farinha_id = api.ingrediente("Farinha receita 025", "g", "Farinhas")
    pao = _produto(api, "Pão Rústico Comercial", confirmado_inexistente=True)
    assert _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    ).status_code == 200
    resp = _excluir(api, farinha_id)
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "em_uso"
    assert "Pão Rústico Comercial" in detalhe["mensagem"]
    assert "Juntar" in detalhe["mensagem"]


def test_em_versao_publicada_da_409(api):
    farinha_id = api.ingrediente("Farinha publicada 025", "g", "Farinhas")
    pao = _produto(api, "Pão Publicado 025", confirmado_inexistente=True)
    assert _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    ).status_code == 200
    assert api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200
    # tira do rascunho atual para sobrar só a cópia publicada
    assert _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g", "texto": "a decidir"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    )
    # troca a linha para outro ingrediente no rascunho
    outro = api.ingrediente("Farinha rascunho 025", "g", "Farinhas")
    assert _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": outro, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    ).status_code == 200
    resp = _excluir(api, farinha_id)
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "em_uso"
    assert "publicada" in detalhe["mensagem"].lower() or "Pão Publicado 025" in detalhe["mensagem"]


def test_ligado_a_produto_da_409(api):
    cobertura = _produto(
        api,
        "Cobertura 025",
        uso_venda=False,
        uso_componente=True,
        confirmado_inexistente=True,
    )
    # o preparo da casa vira ingrediente ligado ao produto
    lista = api.get("/ingredientes").json()["ingredientes"]
    ligado = next(i for i in lista if i["nome"] == "Cobertura 025")
    resp = _excluir(api, ligado["id"])
    assert resp.status_code == 409, resp.text
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "em_uso"
    assert "produto" in detalhe["mensagem"].lower() or "Cobertura 025" in detalhe["mensagem"]


def test_outra_organizacao_da_404(client, api):
    ing_id = api.ingrediente("Só da org A 025", "g", "Farinhas")
    with TestClient(create_app(), base_url="http://testserver") as client_b:
        outro = Api(client_b, entrar(client_b, "dono-b-025", "dono", org="org-b-025", fonte_loja=False))
        resp = _excluir(outro, ing_id)
        assert resp.status_code == 404, resp.text
