"""GESTAO-009: produto produzido, comprado e componente, e a troca que recusa a própria origem."""

import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import entrar
from tests.test_estoque import Api, farinha


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


@pytest.fixture()
def duas_orgs(client):
    a = Api(client, entrar(client, "dona-a", "dono", org="org-a"))
    with TestClient(create_app(), base_url="http://testserver") as client_b:
        b = Api(client_b, entrar(client_b, "dono-b", "dono", org="org-b", fonte_loja=False))
        yield a, b


def _produto(api, **extra):
    corpo = {
        "nome": "Bolo de chocolate",
        "modalidade": "produzido",
        "uso_venda": True,
        "uso_componente": False,
        "unidade_venda": "un",
    }
    corpo.update(extra)
    return api.post("/produtos", corpo)


def test_produzido_comprado_e_componente_na_busca(api):
    produzido = _produto(api)
    assert produzido.status_code == 201, produzido.text
    assert produzido.json()["receita"]["situacao"] == "rascunho"
    assert produzido.json()["receita"]["linhas"] == []
    assert "sem_receita" in produzido.json()["selos"]

    cobertura = _produto(
        api,
        nome="Cobertura de chocolate",
        uso_venda=False,
        uso_componente=True,
        confirmado_inexistente=True,
    )
    assert cobertura.status_code == 201, cobertura.text
    busca = api.get("/ingredientes/busca", q="Cobertura de chocolate").json()
    achados = [i for i in busca["da_padaria"] if i["nome"] == "Cobertura de chocolate"]
    assert achados and achados[0]["categoria"] == "Preparos da casa"
    assert achados[0]["id"] == cobertura.json()["ingrediente_id"]

    entrada = api.entrada([farinha(item_nome="Chocolate em barra", marca="Garoto")]).json()
    item_id = entrada["linhas"][0]["item_id"]
    sem_item = _produto(api, nome="Chocolate pronto", modalidade="comprado", unidade_venda="un")
    assert sem_item.status_code == 201, sem_item.text
    assert sem_item.json()["pendente"] is True and "sem_item" in sem_item.json()["selos"]
    pendentes = [p["nome"] for p in api.get("/produtos", filtro="pendentes").json()["produtos"]]
    assert "Chocolate pronto" in pendentes

    com_item = _produto(
        api,
        nome="Chocolate Garoto",
        modalidade="comprado",
        unidade_venda="un",
        item_estoque_id=item_id,
        confirmado_inexistente=True,
    )
    assert com_item.status_code == 201, com_item.text
    assert com_item.json()["pendente"] is False
    assert com_item.json()["item"]["nome"] == "Chocolate em barra"
    assert api.get("/fluxo").json()["etapas"][2]["estado"] == "atencao"


def test_nome_igual_409_e_parecido_pede_confirmacao(api):
    assert _produto(api).status_code == 201
    de_novo = _produto(api)
    assert de_novo.status_code == 409 and de_novo.json()["detail"]["codigo"] == "ja_existe"
    parecido = _produto(api, nome="Bolo chocolate")
    assert parecido.status_code == 409 and parecido.json()["detail"]["codigo"] == "produto_parecido"
    confirmado = _produto(api, nome="Bolo chocolate", confirmado_inexistente=True)
    assert confirmado.status_code == 201, confirmado.text


def test_desligar_componente_nao_apaga_o_ingrediente(api):
    cobertura = _produto(api, nome="Cobertura de chocolate", uso_venda=True, uso_componente=True)
    assert cobertura.status_code == 201, cobertura.text
    ingrediente_id = cobertura.json()["ingrediente_id"]
    editado = api.patch(
        f"/produtos/{cobertura.json()['id']}",
        {"uso_componente": False, "uso_venda": True},
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["ingrediente_id"] == ingrediente_id
    ficha = api.get(f"/ingredientes/{ingrediente_id}")
    assert ficha.status_code == 200, ficha.text
    assert ficha.json()["ativo"] is False
    assert ficha.json()["nome"] == "Cobertura de chocolate"


def test_troca_nao_sugere_a_origem_e_recusa_o_mesmo_destino(api):
    entrada = api.entrada([farinha(item_nome="Fubá Orgânico", ingrediente_nome="Fubá Orgânico")]).json()
    linha = entrada["linhas"][0]
    sugestoes = api.get(
        "/ingredientes/sugestao", item="Fubá Orgânico", exceto=linha["ingrediente_id"]
    ).json()["sugestoes"]
    assert all((s.get("ingrediente") or {}).get("id") != linha["ingrediente_id"] for s in sugestoes)
    recusa = api.post(
        f"/itens/{linha['item_id']}/trocar-ingrediente",
        {"ingrediente_id": linha["ingrediente_id"], "motivo": "é o mesmo"},
    )
    assert recusa.status_code == 422
    assert recusa.json()["detail"]["codigo"] == "mesmo_ingrediente"


def test_produto_de_outra_organizacao_nao_aparece(duas_orgs):
    a, b = duas_orgs
    criado = _produto(a, nome="Pão francês")
    assert criado.status_code == 201, criado.text
    assert b.get(f"/produtos/{criado.json()['id']}").status_code == 404
    assert b.get("/produtos").json()["produtos"] == []
    assert b.get("/familias").json()["sugestoes"]
    assert a.post("/familias", {"nome": "Pães"}).status_code == 201
    assert [f["nome"] for f in b.get("/familias").json()["familias"]] == []
