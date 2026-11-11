"""GESTAO-014B: comanda consolidada, referências da Loja e peso."""

from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.db.session import get_engine
from app.domain.perdas import massa_necessaria
from app.domain.producao import texto_quantidade
from tests.conftest import entrar
from tests.test_estoque import Api
from tests.test_producao_014 import _vincular
from tests.test_receitas import _produto, _put


def test_formatacao_do_peso():
    assert texto_quantidade(Decimal("36648")) == "36,65 kg"
    assert texto_quantidade(Decimal("7.34")) == "7,3 g"


def test_bloco_soma_112_marca_as_duas_e_nao_vaza_pessoa(client, loja):
    api = Api(client, entrar(client, "padeiro-014b", "dono"))
    levain = _produto(
        api,
        "Levain",
        uso_venda=True,
        uso_componente=True,
        cultura_viva=True,
        unidade_venda="un",
        confirmado_inexistente=True,
    )
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    ficha = _put(
        api,
        levain["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 100, "unidade": "g"},
            {"ingrediente_id": levain["ingrediente_id"], "quantidade": 50, "unidade": "g", "funcao": "inoculo"},
        ],
        formato="forma_enriquecida",
        peso_unidade_g=500,
        unidades_desejadas=112,
    )
    assert ficha.status_code == 200, ficha.text
    perdas = ficha.json()["perdas"]
    proc = Decimal(str(perdas["processo"]["percentual"]))
    coc = Decimal(str(perdas["coccao"]["percentual"]))
    massa = massa_necessaria(112, Decimal(500), coc, proc)
    fator = massa / Decimal(150)
    publicada = api.post(f"/receitas/{levain['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text

    hoje = date.fromisoformat(api.get("/producao").json()["hoje"])
    manha = next(item for item in api.get("/producao/fornadas").json()["fornadas"] if item["nome"] == "Manhã 05:00")
    programada = api.post(
        "/producao/programacoes",
        {
            "produto_id": levain["id"],
            "quantidade_por_fornada": 100,
            "fornada_ids": [manha["id"]],
            "dias_semana": [hoje.weekday()],
            "inicio": hoje.isoformat(),
            "fim": hoje.isoformat(),
            "ativa": True,
        },
    )
    assert programada.status_code == 201, programada.text

    base = loja.base("levain")
    produto_loja, variantes = loja.produto("Levain da vitrine", base, [("Unidade", 1)])
    _vincular(levain["id"], produto_loja)
    primeiro = loja.pedido("LPA39746B92A", "confirmed", hoje, nome_cliente="NOME-SINTETICO")
    loja.item(primeiro, produto=produto_loja, variante=variantes[0], quantidade=2, unidades=2, base=base)
    segundo = loja.pedido("SD10X9", "confirmed", hoje, nome_cliente="NOME-SINTETICO")
    loja.item(segundo, produto=produto_loja, variante=variantes[0], quantidade=10, unidades=10, base=base)
    trazido = api.post("/producao/trazer-loja", {"de": hoje.isoformat(), "ate": hoje.isoformat()})
    assert trazido.status_code == 200, trazido.text

    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    assert "NOME-SINTETICO" not in comanda.text
    assert "sintetico@example.invalid" not in comanda.text
    corpo = comanda.json()
    assert len(corpo["produtos"]) == 1
    bloco = corpo["produtos"][0]
    assert bloco["unidades"] == 112
    assert bloco["origens"] == "100 programadas + 12 da Loja"
    farinha_linha = next(linha for linha in bloco["linhas"] if linha["nome"] == "Farinha de trigo")
    assert abs(Decimal(farinha_linha["quantidade_g"]) - Decimal(100) * fator) < Decimal("0.02")
    inoculo = next(linha for linha in bloco["linhas"] if linha["funcao"] == "inoculo")
    assert "do preparo anterior" in inoculo["nome"]
    assert abs(Decimal(inoculo["quantidade_g"]) - Decimal(50) * fator) < Decimal("0.02")
    pesagem = next(item for item in corpo["pesagem"] if item["nome"] == "Levain · inóculo")
    assert abs(Decimal(pesagem["quantidade_g"]) - Decimal(50) * fator) < Decimal("0.02")
    refs = {item["referencia"]: item["unidades"] for item in bloco["loja"]}
    assert refs == {"LPA39746B92A": 2, "SD10X9": 10}

    impressa = api.post("/producao/comanda/imprimir", {"data": hoje.isoformat(), "fornada_id": manha["id"]})
    assert impressa.status_code == 200, impressa.text
    assert impressa.json()["produtos"][0]["unidades"] == 112
    assert "NOME-SINTETICO" not in impressa.text
    assert "sintetico@example.invalid" not in impressa.text
    with get_engine().begin() as conn:
        linhas = conn.execute(
            text(
                "SELECT origem, situacao, unidades FROM ordens_producao "
                "WHERE produto_id = :produto AND data = :dia AND situacao != 'cancelada'"
            ),
            {"produto": levain["id"], "dia": hoje},
        ).all()
    assert len(linhas) == 2
    assert {linha.situacao for linha in linhas} == {"impressa"}
    assert {linha.origem for linha in linhas} == {"programada", "loja"}
    assert sum(linha.unidades for linha in linhas) == 112
