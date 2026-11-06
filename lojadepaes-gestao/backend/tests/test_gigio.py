"""GESTAO-012: sugestão do Gigio com o gateway falso. Nada publica e nada cria ingrediente."""

import json
from decimal import ROUND_HALF_UP, Decimal

import pytest
from app.db.session import get_engine
from app.domain.gigio.fake import FakeGateway
from app.domain.gigio.gateway import ChatResponse
from app.domain.gigio.servico import definir_gateway
from app.domain.receitas import farinha_contida
from app.main import create_app
from app.models.gigio import GigioSugestao
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import entrar
from tests.test_estoque import Api
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


@pytest.fixture()
def duas_orgs(client):
    a = Api(client, entrar(client, "dona-a", "dono", org="org-a"))
    with TestClient(create_app(), base_url="http://testserver") as client_b:
        b = Api(client_b, entrar(client_b, "dono-b", "dono", org="org-b", fonte_loja=False))
        yield a, b


@pytest.fixture()
def falso(monkeypatch):
    monkeypatch.setenv("GESTAO_GIGIO_GATEWAY", "fake")
    gateway = FakeGateway()
    definir_gateway(gateway)
    yield gateway
    definir_gateway(None)


def _resposta(linhas):
    return ChatResponse(
        text="",
        tool_use=[{"id": "t", "name": "sugerir_receita", "input": {"linhas": linhas, "rendimento_g": 800, "perda_pct": 0, "modo_de_fazer": ["Misture."]}}],
        model_id="fake",
        input_tokens=3,
        output_tokens=4,
    )


def _pedir(api, produto_id, **extra):
    corpo = {
        "descricao": "Pão de canela sobre a massa sovada, com inclusão que eu não medi.",
        "linhas_fixas": [],
    }
    corpo.update(extra)
    return api.post(f"/receitas/{produto_id}/sugestao-gigio", corpo)


def _publicar_sovada(api, farinha, agua, residual):
    massa = _produto(api, "Massa sovada", uso_venda=False, uso_componente=True, confirmado_inexistente=True)
    salvo = _put(
        api,
        massa["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 300, "unidade": "g"},
            {"ingrediente_id": residual, "quantidade": 30, "unidade": "g"},
        ],
        rendimento_quantidade=830,
        rendimento_unidade="g",
    )
    assert salvo.status_code == 200, salvo.text
    publicada = api.post(f"/receitas/{massa['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    return massa


def test_linhas_fixas_e_massa_base_nao_mudam(api, falso):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    residual = api.ingrediente("Água residual", "g", "Líquidos")
    sal = api.ingrediente("Sal", "g", "Sal e temperos")
    massa = _publicar_sovada(api, farinha, agua, residual)
    pao = _produto(api, "Pão de canela")
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Canela",
                    "quantidade_g": 8,
                    "percentual": 2,
                    "faixa_min": 1,
                    "faixa_max": 3,
                    "confianca": "baixa",
                    "motivo": "Inclusão.",
                }
            ]
        )
    )
    resposta = _pedir(
        api,
        pao["id"],
        massa_base_id=massa["id"],
        massa_base_quantidade=800,
        linhas_fixas=[{"ingrediente_id": sal, "quantidade": 10, "unidade": "g"}],
    )
    assert resposta.status_code == 200, resposta.text
    linhas = {linha["nome"]: linha for linha in resposta.json()["linhas"]}
    assert linhas["Sal"]["quantidade"] == 10
    assert linhas["Sal"]["fixa"] is True
    assert linhas["Sal"]["motivo"].startswith("Linha fixa")
    assert linhas["Massa sovada"]["fixa"] is True
    assert linhas["Massa sovada"]["quantidade"] == 800
    assert linhas["Massa sovada"]["percentual"] is None
    assert "Farinha de trigo" not in linhas
    assert "Água" not in linhas
    pedido = falso.calls[0].system_prompt
    assert "Hidratação" in pedido
    assert "60" in pedido
    assert "Sal: 10 g" in pedido
    assert "Farinha de trigo:" in pedido
    assert "já incluída na massa-base" in pedido
    assert "481.9" in pedido


def test_linha_que_repete_a_massa_base_e_descartada(api, falso):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    residual = api.ingrediente("Água residual", "g", "Líquidos")
    massa = _publicar_sovada(api, farinha, agua, residual)
    pao = _produto(api, "Pão de canela com base")
    antes = len(api.get("/ingredientes").json()["ingredientes"])
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Farinha de trigo",
                    "quantidade_g": 500,
                    "percentual": 100,
                    "faixa_min": 100,
                    "faixa_max": 100,
                    "confianca": "alta",
                    "motivo": "Farinha.",
                },
                {
                    "ingrediente": "Canela",
                    "quantidade_g": 8,
                    "percentual": 1,
                    "faixa_min": 1,
                    "faixa_max": 3,
                    "confianca": "baixa",
                    "motivo": "Inclusão.",
                },
            ]
        )
    )
    resposta = _pedir(api, pao["id"], massa_base_id=massa["id"], massa_base_quantidade=500)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    nomes = [linha["nome"] for linha in corpo["linhas"]]
    assert nomes.count("Farinha de trigo") == 0
    assert "Canela" in nomes
    assert any("Farinha de trigo" in aviso and "descartada" in aviso for aviso in corpo["avisos"])
    assert len(api.get("/ingredientes").json()["ingredientes"]) == antes


def test_massa_sem_receita_publicada_avisa(api, falso):
    _produto(api, "Massa crua", uso_venda=False, uso_componente=True)
    massa = next(p for p in api.get("/produtos?filtro=componentes").json()["produtos"] if p["nome"] == "Massa crua")
    pao = _produto(api, "Pão sem base publicada")
    resposta = _pedir(api, pao["id"], massa_base_id=massa["id"], massa_base_quantidade=500)
    assert resposta.status_code == 422
    assert "Monte primeiro" in resposta.json()["detail"]["mensagem"]
    assert falso.calls == []


def test_percentual_recursivo_da_farinha_contida(api):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    agua = api.ingrediente("Água", "g", "Líquidos")
    residual = api.ingrediente("Água residual", "g", "Líquidos")
    sal = api.ingrediente("Sal", "g", "Sal e temperos")
    massa = _publicar_sovada(api, farinha, agua, residual)
    pao = _produto(api, "Pão sobre a sovada")
    salvo = _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": massa["ingrediente_id"], "quantidade": 800, "unidade": "g"},
            {"ingrediente_id": sal, "quantidade": 48, "unidade": "g"},
        ],
    )
    assert salvo.status_code == 200, salvo.text
    linhas = {linha["nome"]: linha for linha in salvo.json()["linhas"]}
    assert linhas["Massa sovada"]["percentual_padeiro"] is None
    with Session(get_engine()) as db:
        contida = farinha_contida(db, massa["id"], Decimal(800))
    assert contida.quantize(Decimal("1"), rounding=ROUND_HALF_UP) == 482
    assert linhas["Sal"]["percentual_padeiro"] == pytest.approx(float(Decimal(48) / contida * 100))


def test_qualificador_nao_liga_fermento_seco_a_fresco(api, falso):
    api.ingrediente("Fermento fresco", "g", "Outros")
    seco = api.ingrediente("Fermento seco", "g", "Outros")
    pao = _produto(api, "Pão com fermento")
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Fermento seco",
                    "quantidade_g": 5,
                    "percentual": 1,
                    "confianca": "alta",
                    "motivo": "Fermento da receita.",
                }
            ]
        )
    )
    resposta = _pedir(api, pao["id"])
    assert resposta.status_code == 200, resposta.text
    linha = next(item for item in resposta.json()["linhas"] if "ermento" in item["nome"])
    assert linha["ingrediente_id"] == seco
    assert linha["nome"] == "Fermento seco"


def test_desconhecido_fica_a_decidir_e_nao_cria_ingrediente(api, falso):
    pao = _produto(api, "Pão de castanha")
    antes = api.get("/ingredientes").json()["ingredientes"]
    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Castanha que ninguém cadastrou",
                    "quantidade_g": 40,
                    "percentual": 8,
                    "faixa_min": 5,
                    "faixa_max": 12,
                    "confianca": "baixa",
                    "motivo": "Inclusão.",
                }
            ]
        )
    )
    resposta = _pedir(api, pao["id"])
    assert resposta.status_code == 200, resposta.text
    linha = resposta.json()["linhas"][0]
    assert linha["a_decidir"] is True
    assert linha["ingrediente_id"] is None
    depois = api.get("/ingredientes").json()["ingredientes"]
    assert len(depois) == len(antes)


def test_aplicar_estima_e_mudar_quantidade_confere_sem_publicar(api, falso):
    canela = api.ingrediente("Canela", "g", "Outros")
    pao = _produto(api, "Pão estimado")
    aplicado = api.post(
        f"/receitas/{pao['id']}/aplicar-sugestao",
        {
            "linhas": [
                {
                    "ingrediente_id": canela,
                    "quantidade": 8,
                    "unidade": "g",
                    "origem": "estimado",
                    "faixa_min": 1,
                    "faixa_max": 3,
                }
            ],
            "rendimento_g": 800,
            "perda_pct": 0,
            "modo_de_fazer": ["Asse."],
            "confirmar_sem_fermento": True,
        },
    )
    assert aplicado.status_code == 200, aplicado.text
    ficha = aplicado.json()
    assert ficha["situacao"] == "rascunho"
    assert ficha["linhas"][0]["origem"] == "estimado"
    assert ficha["publicada"] is None
    mudou = _put(
        api,
        pao["id"],
        linhas=[
            {
                "ingrediente_id": canela,
                "quantidade": 12,
                "unidade": "g",
                "origem": "estimado",
                "faixa_min": 1,
                "faixa_max": 3,
            }
        ],
        rendimento_quantidade=800,
        rendimento_unidade="g",
    )
    assert mudou.status_code == 200, mudou.text
    assert mudou.json()["linhas"][0]["origem"] == "conferido"
    assert mudou.json()["situacao"] == "rascunho"


def test_limite_de_30_e_sem_credencial(api, monkeypatch):
    pao = _produto(api, "Pão do limite")
    monkeypatch.delenv("GESTAO_GIGIO_GATEWAY", raising=False)
    monkeypatch.delenv("GESTAO_GIGIO_AWS_ACCESS_KEY_ID", raising=False)
    definir_gateway(None)
    situacao = api.get("/gigio/situacao")
    assert situacao.status_code == 200
    assert situacao.json()["disponivel"] is False
    recusado = _pedir(api, pao["id"])
    assert recusado.status_code == 503

    monkeypatch.setenv("GESTAO_GIGIO_GATEWAY", "fake")
    definir_gateway(FakeGateway())
    for _ in range(30):
        ok = _pedir(api, pao["id"], descricao=f"Pão {_}")
        assert ok.status_code == 200, ok.text
    estourou = _pedir(api, pao["id"], descricao="mais uma")
    assert estourou.status_code == 429
    definir_gateway(None)


def test_auditoria_sem_custo_e_isolamento(api, duas_orgs, monkeypatch):
    dona, outra = duas_orgs
    monkeypatch.setenv("GESTAO_GIGIO_GATEWAY", "fake")
    definir_gateway(FakeGateway())
    farinha = dona.ingrediente("Farinha de trigo", "g", "Farinhas")
    pao = _produto(dona, "Pão da casa A")
    resposta = _pedir(
        dona,
        pao["id"],
        linhas_fixas=[{"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"}],
    )
    assert resposta.status_code == 200, resposta.text
    with Session(get_engine()) as db:
        registro = db.scalar(select(GigioSugestao).order_by(GigioSugestao.criado_em.desc()))
        texto = json.dumps(registro.entrada, ensure_ascii=False).lower()
        assert "custo" not in texto
        assert "preco" not in texto
        assert "preço" not in texto
        assert registro.usuario_id is not None
    assert outra.get(f"/receitas/{pao['id']}").status_code == 404
    assert outra.get("/gigio/situacao").json()["usadas"] == 0
    definir_gateway(None)


def test_padroes_nascem_com_a_organizacao(api):
    nomes = {p["nome"]: p for p in api.get("/padroes").json()["padroes"]}
    assert nomes["Hidratação"]["percentual"] == 60
    assert nomes["Água residual do fermento"]["percentual"] == 6
    assert "além da hidratação" in nomes["Água residual do fermento"]["observacao"]
    assert nomes["Leite em pó ou farinha láctea"]["percentual"] == 10
    assert nomes["Levain"]["percentual"] == 20
    assert nomes["PFF"]["percentual"] == 20
    editado = api.c.patch(
        f"/api/v1/padroes/{nomes['Levain']['id']}",
        json={
            "nome": "Levain",
            "termo": "levain",
            "percentual": 25,
            "observacao": "A casa usa 25 %.",
            "ativo": True,
        },
        headers=api.h,
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["percentual"] == 25


def test_ensaio_nao_troca_farinha_por_um_parecido(api, falso):
    api.ingrediente("Farinha de Trigo sarraceno", "g", "Farinhas")
    from app.domain.gigio.servico import ensaiar
    from app.models.organizacao import Organizacao

    falso.script.append(
        _resposta(
            [
                {
                    "ingrediente": "Canela",
                    "quantidade_g": 8,
                    "percentual": 1,
                    "faixa_min": 1,
                    "faixa_max": 3,
                    "confianca": "baixa",
                    "motivo": "Inclusão.",
                }
            ]
        )
    )
    with Session(get_engine()) as db:
        org = db.scalars(select(Organizacao).where(Organizacao.nome_curto == "loja")).one()
        resultado = ensaiar(
            db,
            org.id,
            titulo="Pão de Canela",
            familia="Pão Sovado",
            descricao="Pão de canela.",
            base=[{"nome": "Farinha de trigo", "quantidade_g": 500}],
        )
        db.rollback()
    assert resultado["linhas"][0]["nome"] == "Farinha de trigo"
    assert "Farinha de Trigo sarraceno" not in [linha["nome"] for linha in resultado["linhas"]]
    assert "Farinha de trigo:" in falso.calls[0].system_prompt
    assert "sarraceno" not in falso.calls[0].system_prompt
