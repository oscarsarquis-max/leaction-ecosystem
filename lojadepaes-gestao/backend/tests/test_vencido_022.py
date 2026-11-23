"""GESTAO-022: lote vencido não conta como “vence em 7 dias”."""

from tests.conftest import entrar
from tests.test_estoque import Api, farinha, validade_em


def test_lote_vencido_aparece_como_falta_e_nao_conta_como_a_vencer(client):
    api = Api(client, entrar(client, "padeiro-022", "dono"))

    # Lote vencido há 7 dias, ainda com saldo → "1 lote vencido", estado falta.
    vencido = api.entrada(
        [
            farinha(
                item_nome="Semolina vencida",
                marca="Casa",
                ingrediente_nome="Farinha de semolina",
                validade=validade_em(-7),
                quantidade=2,
                unidade="kg",
            )
        ]
    )
    assert vencido.status_code == 201, vencido.text

    ingredientes = next(e for e in api.get("/fluxo").json()["etapas"] if e["id"] == "ingredientes")
    assert ingredientes["estado"] == "falta"
    assert ingredientes["frase"] == "1 lote vencido"

    hoje = api.get("/hoje").json()
    por_nome = {v["ingrediente"]: v for v in hoje["vence_em_7_dias"]}
    assert por_nome["Farinha de semolina"]["dias"] == -7

    # Lote que vence em 3 dias não entra na contagem de vencidos.
    perto = api.entrada(
        [
            farinha(
                item_nome="Fermento perto",
                marca="X",
                ingrediente_nome="Fermento",
                validade=validade_em(3),
                quantidade=1,
            )
        ]
    )
    assert perto.status_code == 201, perto.text

    ingredientes = next(e for e in api.get("/fluxo").json()["etapas"] if e["id"] == "ingredientes")
    assert ingredientes["estado"] == "falta"
    assert ingredientes["frase"] == "1 lote vencido · 1 vence em 7 dias"

    hoje = api.get("/hoje").json()
    por_nome = {v["ingrediente"]: v for v in hoje["vence_em_7_dias"]}
    assert por_nome["Farinha de semolina"]["dias"] == -7
    assert por_nome["Fermento"]["dias"] == 3
