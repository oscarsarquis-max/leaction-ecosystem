"""GESTAO-007D: ingrediente juntado sai da busca, reativar não move itens, 00 não junta com 0."""

import pytest

from tests.conftest import entrar
from tests.test_estoque import Api, farinha


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def test_pares_nao_propoem_00_com_0_e_a_api_recusa(api):
    tipo_00 = api.post("/ingredientes", {"nome": "Farinha de trigo tipo 00", "unidade_base": "g", "categoria": "Farinhas"}).json()["id"]
    tipo_0 = api.post(
        "/ingredientes",
        {"nome": "Farinha de trigo tipo 0", "unidade_base": "g", "categoria": "Farinhas", "confirmado_inexistente": True},
    ).json()["id"]
    pares = api.get("/ingredientes").json()["pares_parecidos"]
    nomes = {(p["a"]["nome"], p["b"]["nome"]) for p in pares}
    assert ("Farinha de trigo tipo 00", "Farinha de trigo tipo 0") not in nomes
    assert ("Farinha de trigo tipo 0", "Farinha de trigo tipo 00") not in nomes
    recusa = api.post("/ingredientes/juntar", {"mantem_id": tipo_0, "remove_id": tipo_00})
    assert recusa.status_code == 422
    assert recusa.json()["detail"]["codigo"] == "qualificadores_diferentes"
    seco = api.post("/ingredientes", {"nome": "Fermento biológico seco", "unidade_base": "g", "categoria": "Fermentos"}).json()["id"]
    fresco = api.post(
        "/ingredientes",
        {"nome": "Fermento biológico fresco", "unidade_base": "g", "categoria": "Fermentos", "confirmado_inexistente": True},
    ).json()["id"]
    assert api.post("/ingredientes/juntar", {"mantem_id": seco, "remove_id": fresco}).status_code == 422


def test_busca_nao_traz_o_juntado_reativar_nao_move_e_depois_a_troca_funciona(api):
    entrada = api.entrada(
        [
            farinha(
                item_nome="Farinha de Trigo Nita 00",
                marca="Nita",
                ingrediente_nome="Farinha de trigo tipo 00",
                quantidade=4,
                unidade="kg",
            )
        ]
    ).json()["linhas"][0]
    tipo_00 = entrada["ingrediente_id"]
    generica = api.post(
        "/ingredientes",
        {"nome": "Farinha de trigo", "unidade_base": "g", "categoria": "Farinhas", "confirmado_inexistente": True},
    ).json()["id"]
    assert api.post("/ingredientes/juntar", {"mantem_id": generica, "remove_id": tipo_00}).status_code == 200

    busca = api.get("/ingredientes/busca", q="Farinha de trigo tipo 00").json()
    assert all(i["nome"] != "Farinha de trigo tipo 00" for i in busca["da_padaria"])
    assert all(c["nome"] != "Farinha de trigo tipo 00" for c in busca["do_catalogo"])
    assert busca["juntados"][0]["nome"] == "Farinha de trigo tipo 00"
    assert busca["juntados"][0]["destino_nome"] == "Farinha de trigo"
    assert busca["juntados"][0]["juntado_em"]
    sugestoes = api.get("/ingredientes/sugestao", item="Farinha de Trigo Nita 00").json()["sugestoes"]
    assert all((s.get("catalogo") or {}).get("nome") != "Farinha de trigo tipo 00" for s in sugestoes)
    assert all((s.get("ingrediente") or {}).get("id") != tipo_00 for s in sugestoes)

    # O item ficou na farinha genérica. Reativar não o traz de volta.
    assert api.saldo(generica) == 4000
    reativado = api.post(f"/ingredientes/{tipo_00}/reativar", {"motivo": "Vou usar o tipo 00 de novo"})
    assert reativado.status_code == 200, reativado.text
    corpo = reativado.json()
    assert corpo["ativo"] is True and corpo["juntado_em_id"] is None
    assert corpo["itens_detalhe"] == []
    assert api.saldo(generica) == 4000
    assert any(m["reativacao"] for m in corpo["movimentos"])

    troca = api.post(
        f"/itens/{entrada['item_id']}/trocar-ingrediente",
        {"ingrediente_id": tipo_00, "motivo": "Era tipo 00, não a farinha genérica"},
    )
    assert troca.status_code == 200, troca.text
    assert api.saldo(tipo_00) == 4000
    assert api.saldo(generica) == 0


def test_trocar_para_o_inativo_diz_para_reativar(api):
    tipo_00 = api.post("/ingredientes", {"nome": "Farinha de trigo tipo 00", "unidade_base": "g", "categoria": "Farinhas"}).json()["id"]
    generica = api.post(
        "/ingredientes",
        {"nome": "Farinha de trigo", "unidade_base": "g", "categoria": "Farinhas", "confirmado_inexistente": True},
    ).json()["id"]
    api.entrada([farinha(ingrediente_nome="Farinha de trigo", ingrediente_id=generica)])
    assert api.post("/ingredientes/juntar", {"mantem_id": generica, "remove_id": tipo_00}).status_code == 200
    item = api.get(f"/ingredientes/{generica}").json()["itens_detalhe"][0]["id"]
    recusa = api.post(f"/itens/{item}/trocar-ingrediente", {"ingrediente_id": tipo_00, "motivo": "quero o 00"})
    detalhe = recusa.json()["detail"]
    assert detalhe["codigo"] == "ingrediente_inativo"
    assert "Reative" in detalhe["mensagem"]
    assert "Escolha o que ficou" not in detalhe["mensagem"]
    assert detalhe["reativar"]["destino_nome"] == "Farinha de trigo"
    criar = api.post("/ingredientes", {"nome": "Farinha de trigo tipo 00", "unidade_base": "g", "categoria": "Farinhas"})
    assert criar.status_code == 409
    assert criar.json()["detail"]["codigo"] == "ingrediente_inativo"
    assert criar.json()["detail"]["reativar"]["id"] == tipo_00
