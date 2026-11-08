"""GESTAO-014: programação, demanda da Loja, escala da comanda e isolamento."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.db.session import get_engine
from app.domain.producao import texto_quantidade
from sqlalchemy import text

from tests.conftest import entrar
from tests.test_estoque import Api
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


@pytest.fixture()
def duas_orgs(client):
    from app.main import create_app
    from fastapi.testclient import TestClient

    a = Api(client, entrar(client, "dona-a", "dono", org="org-a"))
    with TestClient(create_app(), base_url="http://testserver") as client_b:
        b = Api(client_b, entrar(client_b, "dono-b", "dono", org="org-b", fonte_loja=False))
        yield a, b


def _vincular(produto_id: str, loja_id) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE produtos SET origem_loja_id = :loja WHERE id = :id"),
            {"loja": loja_id, "id": produto_id},
        )


def _fornadas(api):
    resposta = api.get("/producao/fornadas")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["fornadas"]


def _hoje(api) -> date:
    corpo = api.get("/producao").json()
    return date.fromisoformat(corpo["hoje"])


def test_programacao_de_14_dias_e_idempotente_e_nao_altera_impressa(api):
    pao = _produto(api, "Pãozinho do dia")
    fornadas = _fornadas(api)
    assert [item["nome"] for item in fornadas] == ["Manhã 05:00", "Tarde 13:00"]
    corpo = {
        "produto_id": pao["id"],
        "quantidade_por_fornada": 100,
        "fornada_ids": [item["id"] for item in fornadas],
        "dias_semana": [0, 1, 2, 3, 4, 5],
        "ativa": True,
    }
    criada = api.post("/producao/programacoes", corpo)
    assert criada.status_code == 201, criada.text
    hoje = _hoje(api)
    ate = hoje + timedelta(days=14)

    def ordens():
        resposta = api.get("/producao", de=hoje.isoformat(), ate=ate.isoformat())
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["ordens"]

    primeira = ordens()
    segunda = ordens()
    assert [item["id"] for item in primeira] == [item["id"] for item in segunda]
    assert all(item["unidades"] == 100 and item["origem"] == "programada" for item in primeira)
    esperadas = 0
    dia = hoje
    while dia <= ate:
        if dia.weekday() <= 5:
            esperadas += 2
        dia += timedelta(days=1)
    assert len(primeira) == esperadas

    alvo = primeira[0]
    impressa = api.post(
        "/producao/comanda/imprimir", {"data": alvo["data"], "fornada_id": alvo["fornada_id"]}
    )
    assert impressa.status_code == 200, impressa.text
    assert impressa.json()["numero"] == 1
    assert impressa.json()["via_rotulo"] is None
    segunda_via = api.post(
        "/producao/comanda/imprimir", {"data": alvo["data"], "fornada_id": alvo["fornada_id"]}
    )
    assert segunda_via.status_code == 200, segunda_via.text
    assert segunda_via.json()["via_rotulo"] == "2ª via"
    assert segunda_via.json()["numero"] == 1

    corpo["quantidade_por_fornada"] = 80
    mudou = api.patch(f"/producao/programacoes/{criada.json()['id']}", corpo)
    assert mudou.status_code == 200, mudou.text
    depois = ordens()
    impressas = [item for item in depois if item["situacao"] == "impressa"]
    planejadas = [item for item in depois if item["situacao"] == "planejada"]
    assert impressas and all(item["unidades"] == 100 for item in impressas)
    assert planejadas and all(item["unidades"] == 80 for item in planejadas)


def test_demanda_da_loja_lista_sem_vinculo_e_marca_diferenca(api, loja):
    base = loja.base("integral")
    produto_loja, variantes = loja.produto("Pão da vitrine", base, [("Unidade", 1)])
    pao = _produto(api, "Pão da vitrine")
    _vincular(pao["id"], produto_loja)
    hoje = _hoje(api)
    pedido = loja.pedido("vitrine-1", "confirmed", hoje)
    loja.item(pedido, produto=produto_loja, variante=variantes[0], quantidade=4, unidades=4, base=base)
    massa = loja.massa("Crie seu pão", base)
    avulso = loja.pedido("criador-1", "confirmed", hoje)
    loja.item(avulso, massa=massa, nome_massa="Crie seu pão", nome_forma="Bola", quantidade=2, base=base)

    trazido = api.post("/producao/trazer-loja", {"de": hoje.isoformat(), "ate": hoje.isoformat()})
    assert trazido.status_code == 200, trazido.text
    assert any(item["nome"].startswith("Crie seu pão") for item in trazido.json()["sem_vinculo"])
    loja_ordens = [
        item
        for item in api.get("/producao", de=hoje.isoformat(), ate=hoje.isoformat()).json()["ordens"]
        if item["origem"] == "loja"
    ]
    assert len(loja_ordens) == 1
    assert loja_ordens[0]["unidades"] == 4
    assert loja_ordens[0]["origem_rotulo"] == "Loja"

    impressa = api.post(
        "/producao/comanda/imprimir",
        {"data": hoje.isoformat(), "fornada_id": loja_ordens[0]["fornada_id"]},
    )
    assert impressa.status_code == 200, impressa.text
    extra = loja.pedido("vitrine-2", "confirmed", hoje)
    loja.item(extra, produto=produto_loja, variante=variantes[0], quantidade=2, unidades=2, base=base)
    de_novo = api.post("/producao/trazer-loja", {"de": hoje.isoformat(), "ate": hoje.isoformat()})
    assert de_novo.status_code == 200, de_novo.text
    atual = [
        item
        for item in api.get("/producao", de=hoje.isoformat(), ate=hoje.isoformat()).json()["ordens"]
        if item["origem"] == "loja"
    ][0]
    assert atual["unidades"] == 4
    assert atual["demanda_diferenca"] == 2
    assert atual["diferenca_texto"] == "+2"
    assert atual["situacao"] == "impressa"


def test_dez_paes_escalam_a_receita_e_expandem_a_massa_base(api):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    fermento = api.ingrediente("Fermento", "g", "Fermentos")
    massa = _produto(api, "Massa base da escala", uso_venda=False, uso_componente=True)
    ingrediente_massa = api.ingrediente("Massa base da escala")
    gravada = _put(
        api,
        massa["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 700, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 300, "unidade": "g"},
        ],
        rendimento_quantidade=1000,
        rendimento_unidade="g",
        modo_fazer=["misturar a base"],
    )
    assert gravada.status_code == 200, gravada.text
    publicada = api.post(f"/receitas/{massa['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text

    pao = _produto(api, "Pão de forma da escala")
    ficha = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": ingrediente_massa, "quantidade": 1000, "unidade": "g", "funcao": "massa"},
            {"ingrediente_id": fermento, "quantidade": "1.2", "unidade": "g", "funcao": "massa"},
        ],
        formato="forma_enriquecida",
        peso_unidade_g=500,
        unidades_desejadas=10,
        modo_fazer=["dividir", "assar"],
    )
    assert ficha.status_code == 200, ficha.text
    assert ficha.json()["perdas"]["massa_necessaria_g"] == 5981
    assert api.post(f"/receitas/{pao['id']}/publicar").status_code == 200

    hoje = _hoje(api)
    manha = next(item for item in _fornadas(api) if item["nome"] == "Manhã 05:00")
    ordem = api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 10},
    )
    assert ordem.status_code == 201, ordem.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco["massa"] == "5.981 g (5,981 kg)"
    componente = next(linha for linha in bloco["linhas"] if linha["componente"])
    assert componente["filhos"]
    farinha_folha = next(folha for folha in componente["filhos"] if folha["nome"] == "Farinha de trigo")
    fermento_linha = next(linha for linha in bloco["linhas"] if linha["nome"] == "Fermento")
    assert Decimal(fermento_linha["quantidade_g"]) < 20
    assert "," in fermento_linha["texto"]
    assert abs(Decimal(farinha_folha["quantidade_g"]) - Decimal(componente["quantidade_g"]) * Decimal("0.7")) < Decimal("0.02")
    pesagem_farinha = next(item for item in comanda.json()["pesagem"] if item["nome"] == "Farinha de trigo")
    assert Decimal(pesagem_farinha["quantidade_g"]) == Decimal(farinha_folha["quantidade_g"])
    assert "dividir" in bloco["modo_fazer"]
    fator = Decimal(componente["quantidade_g"]) / Decimal(1000)
    assert abs(Decimal(fermento_linha["quantidade_g"]) - Decimal("1.2") * fator) < Decimal("0.02")


def test_arredondamento_da_quantidade():
    assert texto_quantidade(Decimal("7.3")) == "7,3 g"
    assert texto_quantidade(Decimal("1234")) == "1.234 g (1,234 kg)"


def test_pesagem_soma_o_mesmo_ingrediente_de_produtos_diferentes(api):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    fermento = api.ingrediente("Fermento", "g", "Fermentos")
    hoje = _hoje(api)
    manha = next(item for item in _fornadas(api) if item["nome"] == "Manhã 05:00")
    for nome, quantidade in (("Pão claro", 400), ("Pão escuro", 250)):
        pao = _produto(api, nome)
        salvo = _put(
            api,
            pao["id"],
            linhas=[
                {"ingrediente_id": farinha, "quantidade": quantidade, "unidade": "g"},
                {"ingrediente_id": fermento, "quantidade": 8, "unidade": "g"},
            ],
            formato="forma_enriquecida",
            peso_unidade_g=500,
            unidades_desejadas=10,
        )
        assert salvo.status_code == 200, salvo.text
        assert api.post(f"/receitas/{pao['id']}/publicar").status_code == 200
        ordem = api.post(
            "/producao/ordens",
            {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 10},
        )
        assert ordem.status_code == 201, ordem.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"]).json()
    folhas = [
        Decimal(linha["quantidade_g"])
        for bloco in comanda["produtos"]
        for linha in bloco["linhas"]
        if linha["nome"] == "Farinha de trigo" and not linha["componente"]
    ]
    assert len(folhas) == 2
    pesagem = next(item for item in comanda["pesagem"] if item["nome"] == "Farinha de trigo")
    assert Decimal(pesagem["quantidade_g"]) == sum(folhas, Decimal(0))


def test_ordem_nao_vaza_entre_organizacoes(duas_orgs):
    a, b = duas_orgs
    pao = _produto(a, "Pão da casa A")
    hoje = _hoje(a).isoformat()
    fornada = _fornadas(a)[0]
    criada = a.post(
        "/producao/ordens",
        {"data": hoje, "fornada_id": fornada["id"], "produto_id": pao["id"], "unidades": 6},
    )
    assert criada.status_code == 201, criada.text
    da_outra = b.get("/producao", de=hoje, ate=hoje).json()["ordens"]
    assert da_outra == []
    assert b.patch(f"/producao/ordens/{criada.json()['id']}", {"unidades": 9}).status_code == 404
    assert [item["nome"] for item in _fornadas(b)] == ["Manhã 05:00", "Tarde 13:00"]
