"""GESTAO-014C: a massa da comanda fecha com a soma dos ingredientes."""

import json
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.db.session import get_engine
from tests.conftest import entrar
from tests.test_estoque import Api
from tests.test_receitas import _produto, _put


def _api(client, usuario):
    return Api(client, entrar(client, usuario, "dono"))


def _perdas(produto_id: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE receitas SET
                  perda_processo_pct = 5,
                  perda_processo_origem = 'manual',
                  perda_processo_motivo = 'teste da area',
                  perda_coccao_pct = 0,
                  perda_coccao_origem = 'manual',
                  perda_coccao_motivo = 'teste da area'
                WHERE produto_id = :id
                """
            ),
            {"id": produto_id},
        )


def _pao(api, nome, farinha_g):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    pao = _produto(api, nome, uso_venda=True, unidade_venda="un")
    ficha = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": farinha_g, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 300, "unidade": "g"},
        ],
        formato="livre",
        peso_unidade_g=568,
    )
    assert ficha.status_code == 200, ficha.text
    publicada = api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    _perdas(pao["id"])
    return pao


def _manha(api):
    hoje = date.fromisoformat(api.get("/producao").json()["hoje"])
    manha = next(item for item in api.get("/producao/fornadas").json()["fornadas"] if item["nome"] == "Manhã 05:00")
    return hoje, manha


def _soma(bloco) -> Decimal:
    total = Decimal(0)
    for linha in bloco["linhas"]:
        if linha["componente"]:
            total += sum((Decimal(filho["quantidade_g"]) for filho in linha["filhos"]), Decimal(0))
        else:
            total += Decimal(linha["quantidade_g"])
    return total


def test_112_pecas_de_568_g_com_5_por_cento_fecha(client):
    api = _api(client, "padeiro-014c")
    pao = _pao(api, "Pão country", 700)
    hoje, manha = _manha(api)
    ordem = api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 112},
    )
    assert ordem.status_code == 201, ordem.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco["unidades"] == 112
    assert bloco["pecas"] == "Peças de 568 g"
    # 112 × 568 g ÷ 0,95 = 66.964 kg, exibido em kg com 2 casas.
    assert bloco["massa"] == "66,96 kg"
    assert bloco["aviso"] is None
    massa = Decimal(66964)
    assert abs(_soma(bloco) - massa) / massa <= Decimal("0.005")


def test_conta_diferente_avisa_e_o_bloco_fica(client, caplog):
    api = _api(client, "padeiro-014c-aviso")
    pao = _pao(api, "Pão da conta", 700)
    hoje, manha = _manha(api)
    assert api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 112},
    ).status_code == 201
    impressa = api.post("/producao/comanda/imprimir", {"data": hoje.isoformat(), "fornada_id": manha["id"]})
    assert impressa.status_code == 200, impressa.text
    farinha = next(linha["quantidade_g"] for linha in impressa.json()["produtos"][0]["linhas"] if linha["nome"] == "Farinha de trigo")
    with get_engine().begin() as conn:
        bruto = conn.execute(
            text("SELECT foto FROM ordens_producao WHERE produto_id = :id AND data = :dia"),
            {"id": pao["id"], "dia": hoje},
        ).scalar_one()
        foto = json.loads(bruto) if isinstance(bruto, str) else bruto
        foto["massa_necessaria_g"] = int(foto["massa_necessaria_g"]) // 2
        conn.execute(
            text("UPDATE ordens_producao SET foto = CAST(:foto AS json) WHERE produto_id = :id AND data = :dia"),
            {"foto": json.dumps(foto), "id": pao["id"], "dia": hoje},
        )
    alvo = logging.getLogger("app.domain.producao")
    alvo.disabled = False
    with caplog.at_level(logging.WARNING, logger="app.domain.producao"):
        comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco["produto"] == "Pão da conta"
    assert bloco["aviso"].startswith("Conta não fecha:")
    assert "Revise a receita" in bloco["aviso"]
    assert next(linha["quantidade_g"] for linha in bloco["linhas"] if linha["nome"] == "Farinha de trigo") == farinha
    assert any("Conta não fecha" in rec.message for rec in caplog.records)


def test_consolidacao_100_mais_12_usa_as_mesmas_perdas(client):
    api = _api(client, "padeiro-014c-soma")
    pao = _pao(api, "Pão da soma", 700)
    hoje, manha = _manha(api)
    programada = api.post(
        "/producao/programacoes",
        {
            "produto_id": pao["id"],
            "quantidade_por_fornada": 100,
            "fornada_ids": [manha["id"]],
            "dias_semana": [hoje.weekday()],
            "inicio": hoje.isoformat(),
            "fim": hoje.isoformat(),
            "ativa": True,
        },
    )
    assert programada.status_code == 201, programada.text
    impressa = api.post("/producao/comanda/imprimir", {"data": hoje.isoformat(), "fornada_id": manha["id"]})
    assert impressa.status_code == 200, impressa.text
    avulsa = api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 12},
    )
    assert avulsa.status_code == 201, avulsa.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco["unidades"] == 112
    assert bloco["origens"] == "100 programadas + 12 avulsas"
    assert bloco["pecas"] == "Peças de 568 g"
    assert bloco["massa"] == "66,96 kg"
    assert bloco["aviso"] is None
    massa = Decimal(66964)
    assert abs(_soma(bloco) - massa) / massa <= Decimal("0.005")


def test_fotos_de_receitas_diferentes_nao_somam_as_cegas(client):
    api = _api(client, "padeiro-014c-diff")
    pao = _pao(api, "Pão das duas fotos", 700)
    hoje, manha = _manha(api)
    programada = api.post(
        "/producao/programacoes",
        {
            "produto_id": pao["id"],
            "quantidade_por_fornada": 100,
            "fornada_ids": [manha["id"]],
            "dias_semana": [hoje.weekday()],
            "inicio": hoje.isoformat(),
            "fim": hoje.isoformat(),
            "ativa": True,
        },
    )
    assert programada.status_code == 201, programada.text
    impressa = api.post("/producao/comanda/imprimir", {"data": hoje.isoformat(), "fornada_id": manha["id"]})
    assert impressa.status_code == 200, impressa.text
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    trocada = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 1400, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 300, "unidade": "g"},
        ],
        formato="livre",
        peso_unidade_g=568,
    )
    assert trocada.status_code == 200, trocada.text
    assert api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200
    _perdas(pao["id"])
    avulsa = api.post(
        "/producao/ordens",
        {"data": hoje.isoformat(), "fornada_id": manha["id"], "produto_id": pao["id"], "unidades": 12},
    )
    assert avulsa.status_code == 201, avulsa.text
    comanda = api.get("/producao/comanda", data=hoje.isoformat(), fornada=manha["id"])
    assert comanda.status_code == 200, comanda.text
    bloco = comanda.json()["produtos"][0]
    assert bloco["unidades"] == 112
    assert bloco["origens"] == "100 programadas + 12 avulsas"
    assert bloco["aviso"] == "receitas diferentes nas ordens"
    assert bloco["linhas"] == []
    with get_engine().begin() as conn:
        bruto = conn.execute(
            text(
                "SELECT foto FROM ordens_producao WHERE produto_id = :id AND data = :dia AND origem = 'programada'"
            ),
            {"id": pao["id"], "dia": hoje},
        ).scalar_one()
    foto = json.loads(bruto) if isinstance(bruto, str) else bruto
    assert foto["linhas"]
    assert foto.get("aviso") != "receitas diferentes nas ordens"
