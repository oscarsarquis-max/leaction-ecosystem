"""GESTAO-010: receita técnica, % do padeiro, custo, ciclo e versão."""

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


def _put(api, produto_id, **corpo):
    base = {
        "linhas": [],
        "rendimento_quantidade": 1,
        "rendimento_unidade": "un",
        "perda_percentual": 0,
        "modo_fazer": [],
    }
    base.update(corpo)
    return api.c.put(f"/api/v1/receitas/{produto_id}", json=base, headers=api.h)


def _produto(api, nome, **extra):
    corpo = {
        "nome": nome,
        "modalidade": "produzido",
        "uso_venda": True,
        "uso_componente": False,
        "unidade_venda": "un",
    }
    corpo.update(extra)
    resposta = api.post("/produtos", corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_componente_nasce_em_grama_e_nao_na_unidade_de_venda(api):
    cobertura = _produto(api, "Cobertura de chocolate", uso_venda=False, uso_componente=True, unidade_venda="un")
    assert cobertura["unidade_base"] == "g"
    em_ml = _produto(
        api,
        "Calda",
        uso_venda=False,
        uso_componente=True,
        unidade_venda="un",
        unidade_base="ml",
        confirmado_inexistente=True,
    )
    assert em_ml["unidade_base"] == "ml"


def test_percentual_do_padeiro(api):
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua_id = api.ingrediente("Água", "g", "Líquidos")
    sal_id = api.ingrediente("Sal", "g", "Sal e temperos")
    pao = _produto(api, "Pão francês")
    salvo = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"},
            {"ingrediente_id": agua_id, "quantidade": 350, "unidade": "g"},
            {"ingrediente_id": sal_id, "quantidade": 10, "unidade": "g"},
        ],
    )
    assert salvo.status_code == 200, salvo.text
    assert [linha["percentual_padeiro"] for linha in salvo.json()["linhas"]] == [100, 70, 2]


def test_custo_de_linha_em_kg_com_ingrediente_em_g(api):
    api.ingrediente("Farinha de trigo", "g", "Farinhas")
    assert api.entrada([farinha()]).status_code == 201
    farinha_id = api.ingrediente("Farinha de trigo")
    bolo = _produto(api, "Bolo simples")
    salvo = _put(
        api,
        bolo["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 1, "unidade": "kg"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
    )
    assert salvo.status_code == 200, salvo.text
    # 1 kg da farinha a R$ 4,50 por kg.
    assert salvo.json()["linhas"][0]["custo"] == pytest.approx(4.5)
    assert salvo.json()["custo_por_unidade"] == pytest.approx(4.5)


def test_mililitro_com_ingrediente_em_grama_da_422(api):
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    bolo = _produto(api, "Bolo de leite")
    resposta = _put(
        api,
        bolo["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 100, "unidade": "ml"}],
    )
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert detalhe["codigo"] == "unidade_incompativel"
    assert detalhe["linha"] == 1
    assert "linha 1" in detalhe["mensagem"]


def test_componente_recursivo_e_ciclo(api):
    api.ingrediente("Farinha de trigo", "g", "Farinhas")
    assert api.entrada([farinha()]).status_code == 201
    farinha_id = api.ingrediente("Farinha de trigo")
    cobertura = _produto(api, "Cobertura", uso_componente=True, unidade_base="g", confirmado_inexistente=True)
    bolo = _produto(api, "Bolo de chocolate", confirmado_inexistente=True)
    cobertura_salva = _put(
        api,
        cobertura["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 200, "unidade": "g"}],
        rendimento_quantidade=100,
        rendimento_unidade="g",
    )
    assert cobertura_salva.status_code == 200, cobertura_salva.text
    publicada = api.post(f"/receitas/{cobertura['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    bolo_salvo = _put(
        api,
        bolo["id"],
        linhas=[{"ingrediente_id": cobertura["ingrediente_id"], "quantidade": 50, "unidade": "g"}],
    )
    assert bolo_salvo.status_code == 200, bolo_salvo.text
    # 200 g × R$ 4,50/kg = R$ 0,90; rendimento 100 g → R$ 0,009/g; 50 g = R$ 0,45.
    assert bolo_salvo.json()["linhas"][0]["custo"] == pytest.approx(0.45)
    assert bolo_salvo.json()["linhas"][0]["componente"] is True

    ciclo = _put(
        api,
        cobertura["id"],
        linhas=[{"ingrediente_id": bolo["ingrediente_id"], "quantidade": 1, "unidade": "un"}],
        rendimento_quantidade=100,
        rendimento_unidade="g",
    )
    # O bolo ainda não é componente, então não fecha ciclo. Liga o uso e tenta de novo.
    assert ciclo.status_code == 200, ciclo.text
    virou = api.patch(
        f"/produtos/{bolo['id']}",
        {"uso_venda": True, "uso_componente": True, "unidade_base": "un"},
    )
    assert virou.status_code == 200, virou.text
    ciclo = _put(
        api,
        cobertura["id"],
        linhas=[{"ingrediente_id": virou.json()["ingrediente_id"], "quantidade": 1, "unidade": "un"}],
        rendimento_quantidade=100,
        rendimento_unidade="g",
    )
    assert ciclo.status_code == 422
    assert ciclo.json()["detail"]["codigo"] == "ciclo_receita"


def test_linha_sem_custo_e_parcial_e_nao_zero(api):
    sal_id = api.ingrediente("Sal", "g", "Sal e temperos")
    bolo = _produto(api, "Bolo sem preço")
    salvo = _put(api, bolo["id"], linhas=[{"ingrediente_id": sal_id, "quantidade": 10, "unidade": "g"}])
    assert salvo.status_code == 200, salvo.text
    corpo = salvo.json()
    assert corpo["custo_parcial"] is True
    assert corpo["linhas_sem_custo"] == 1
    assert corpo["custo_total"] is None
    assert corpo["custo_por_unidade"] is None
    assert "custo_parcial" in corpo["selos"]


def test_publicar_grava_versao_imutavel_e_editar_abre_rascunho(api):
    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    bolo = _produto(api, "Bolo publicado")
    assert _put(
        api,
        bolo["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        modo_fazer=["Misture", "Asse"],
    ).status_code == 200
    publicada = api.post(f"/receitas/{bolo['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    assert publicada.json()["situacao"] == "publicada"
    assert publicada.json()["versao"] == 1
    assert publicada.json()["publicada"]["versao"] == 1
    assert publicada.json()["publicada"]["linhas"][0]["quantidade"] == 500

    editada = _put(
        api,
        bolo["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 600, "unidade": "g"}],
        modo_fazer=["Misture", "Asse"],
    )
    assert editada.status_code == 200, editada.text
    corpo = editada.json()
    assert corpo["situacao"] == "rascunho" and corpo["versao"] == 2
    assert corpo["linhas"][0]["quantidade"] == 600
    assert corpo["publicada"]["versao"] == 1
    assert corpo["publicada"]["linhas"][0]["quantidade"] == 500
    assert "sem_receita" not in api.get(f"/produtos/{bolo['id']}").json()["selos"]


def test_isolamento_entre_organizacoes(duas_orgs):
    a, b = duas_orgs
    bolo = _produto(a, "Bolo da outra padaria")
    assert b.c.get(f"/api/v1/receitas/{bolo['id']}").status_code == 404
    assert b.get("/receitas").json()["receitas"] == []
