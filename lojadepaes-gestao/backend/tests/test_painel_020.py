"""GESTAO-020: o que acabou, pendências, necessidade, indicadores e o preço informado."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from app.db.escopo import ativar_escopo
from app.db.session import get_engine
from app.domain.estoque import hoje_em
from app.domain.producao import calcular_foto, somar_pesagem
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.conftest import criar_org, entrar
from tests.test_custos_021 import _farinha_com_custo, _publicar_pao
from tests.test_estoque import Api, farinha, validade_em
from tests.test_receitas import _produto, _put

FUSO = "America/Sao_Paulo"


@pytest.fixture()
def api(client, loja):
    return Api(client, entrar(client, "padeiro-020", "dono"))


def _hoje():
    return hoje_em(FUSO)


def _vincular(produto_id: str, loja_id) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE produtos SET origem_loja_id = :loja WHERE id = :id"),
            {"loja": loja_id, "id": produto_id},
        )


def _painel(api, **p):
    resposta = api.get("/hoje", **p)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _nomes(lista):
    return [item["nome"] for item in lista]


def _pendencia(corpo, codigo):
    return next((p for p in corpo["pendencias"] if p["codigo"] == codigo), None)


def _levain(api):
    """Preparo da casa (componente): nasce junto um ingrediente ligado ao produto."""
    levain = _produto(
        api, "Levain", uso_venda=False, uso_componente=True, confirmado_inexistente=True
    )
    ing = next(i for i in api.get("/ingredientes").json()["ingredientes"] if i["nome"] == "Levain")
    return levain, ing


# --- 1 e 2: o que acabou ----------------------------------------------------------------------


def test_agua_e_levain_nao_acabam_e_mel_sem_entrada_nao_acabou(api):
    api.entrada([farinha()])  # há movimento no estoque, mas não de água, levain nem mel
    agua = api.ingrediente("Água", "g", "Líquidos")
    _levain(api)
    api.ingrediente("Mel", "g", "Açúcares e mel")

    corpo = _painel(api)

    assert agua
    assert corpo["acabaram"] == []
    assert corpo["sem_saldo"] == []
    pendencia = _pendencia(corpo, "sem_entrada")
    assert pendencia is not None
    assert pendencia["texto"] == "Mel ainda sem entrada"
    assert pendencia["estado"] == "atencao"
    assert pendencia["href"] == "/ingredientes?filtro=sem_saldo"
    # o fluxo da lateral também deixa água e levain de fora do "sem saldo"
    assert "Água" not in str(corpo["fluxo"]["etapas"][1]["frase"])


def test_sem_entrada_com_varios_cita_o_primeiro_por_nome_e_conta_o_resto(api):
    api.entrada([farinha()])
    api.ingrediente("Mel", "g", "Açúcares e mel")
    api.ingrediente("Azeite", "ml", "Gorduras")
    api.ingrediente("Cacau", "g", "Chocolates e cacau")
    pendencia = _pendencia(_painel(api), "sem_entrada")
    assert pendencia["texto"] == "Azeite e mais 2 sem entrada"


def test_ingrediente_que_teve_entrada_e_foi_zerado_acabou(api):
    linha = api.entrada([farinha()]).json()["linhas"][0]
    assert _painel(api)["acabaram"] == []
    ajuste = api.post(
        f"/ingredientes/{linha['ingrediente_id']}/ajustes",
        {"lote_id": linha["lote_id"], "saldo_contado_base": 0, "motivo": "acabou"},
    )
    assert ajuste.status_code == 201, ajuste.text

    corpo = _painel(api)

    assert [s["nome"] for s in corpo["acabaram"]] == ["Farinha de trigo"]
    assert corpo["sem_saldo"] == corpo["acabaram"]
    assert _pendencia(corpo, "sem_entrada") is None  # teve entrada: não é "nunca entrou"


def test_proximo_passo_de_receitas_conta_quantos_faltam(api):
    primeiro = _produto(api, "Pão sem receita 1", confirmado_inexistente=True)
    assert primeiro
    fluxo = api.get("/fluxo").json()
    receitas = next(e for e in fluxo["etapas"] if e["id"] == "receitas")
    assert receitas["estado"] == "falta"
    # com tudo antes em falta o próximo passo não é o de receitas; chega lá pela etapa:
    api.entrada([farinha()])
    _produto(api, "Pão sem receita 2", confirmado_inexistente=True)
    passo = api.get("/fluxo").json()["proximo_passo"]
    assert passo["etapa"] == "receitas"
    assert passo["titulo"] == "Monte a primeira receita"

    farinha_id = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    publicado = _produto(api, "Pão publicado", confirmado_inexistente=True)
    assert _put(
        api,
        publicado["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    ).status_code == 200
    assert api.post(f"/receitas/{publicado['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200

    passo = api.get("/fluxo").json()["proximo_passo"]
    assert passo["etapa"] == "receitas"
    assert passo["titulo"] == "2 produtos sem receita publicada"
    _produto(api, "Pão sem receita 3", confirmado_inexistente=True)
    assert api.get("/fluxo").json()["proximo_passo"]["titulo"] == "3 produtos sem receita publicada"


# --- 3: vínculo da demanda --------------------------------------------------------------------


def test_demanda_ganha_vinculo_com_a_situacao_da_receita(api, loja):
    dia = _hoje() + timedelta(days=1)
    base = loja.base("TRAD")
    farinha_id = _farinha_com_custo(api)

    publicado = _publicar_pao(api, "Pão Publicado 020", farinha_id, 500)
    rascunho = _produto(api, "Pão Rascunho 020", confirmado_inexistente=True)
    assert _put(
        api,
        rascunho["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        peso_unidade_g=500,
        formato="livre",
    ).status_code == 200
    vazio = _produto(api, "Pão Vazio 020", confirmado_inexistente=True)

    pedido = loja.pedido("V1", "confirmed", dia)
    for gestao, nome in ((publicado, "Pão Publicado 020"), (rascunho, "Pão Rascunho 020"), (vazio, "Pão Vazio 020")):
        produto_loja, (variante,) = loja.produto(nome, base, [("Un", 1)])
        _vincular(gestao["id"], produto_loja)
        loja.item(pedido, produto=produto_loja, variante=variante, quantidade=2, unidades=2, base=base)
    desconhecido, (variante,) = loja.produto("Pão Só da Loja 020", base, [("Un", 1)])
    loja.item(pedido, produto=desconhecido, variante=variante, quantidade=1, unidades=1, base=base)
    massa = loja.massa("Massa do criador 020", base)
    loja.item(pedido, massa=massa, nome_massa="Massa do criador 020", nome_forma="Bola", quantidade=3)

    corpo = _painel(api)
    itens = {i["produto_ou_massa"]: i for f in corpo["fornadas"] for i in f["itens"]}

    assert itens["Pão Publicado 020"]["vinculo"] == {
        "produto_id": publicado["id"],
        "produto": "Pão Publicado 020",
        "receita": "publicada",
    }
    assert itens["Pão Rascunho 020"]["vinculo"]["receita"] == "rascunho"
    assert itens["Pão Vazio 020"]["vinculo"]["receita"] == "sem_receita"
    assert itens["Pão Só da Loja 020"]["vinculo"] is None
    assert itens["Massa do criador 020"]["origem"] == "criador"
    assert itens["Massa do criador 020"]["vinculo"] is None
    assert "NOME-SINTETICO" not in str(corpo)

    # catálogo sem vínculo vira pendência que falta; o criador não conta
    sem_vinculo = _pendencia(corpo, "demanda_sem_vinculo")
    assert sem_vinculo["texto"] == "1 item da Loja sem produto no Gestão"
    assert sem_vinculo["estado"] == "falta" and sem_vinculo["href"] == "/producao"


# --- 4: necessidade ---------------------------------------------------------------------------


def test_necessidade_soma_receitas_publicadas_e_abre_a_massa_base(api, loja, db):
    dia = _hoje() + timedelta(days=1)
    base = loja.base("TRAD")
    farinha_id = _farinha_com_custo(api, 12)  # 1 kg em estoque
    agua = api.ingrediente("Água", "g", "Líquidos")
    fermento = api.ingrediente("Fermento", "g", "Fermentos")

    simples = _publicar_pao(api, "Pão simples 020", farinha_id, 1000)

    massa = _produto(api, "Massa base 020", uso_venda=False, uso_componente=True)
    ingrediente_massa = api.ingrediente("Massa base 020")
    assert _put(
        api,
        massa["id"],
        linhas=[
            {"ingrediente_id": farinha_id, "quantidade": 700, "unidade": "g"},
            {"ingrediente_id": agua, "quantidade": 300, "unidade": "g"},
        ],
        rendimento_quantidade=1000,
        rendimento_unidade="g",
        modo_fazer=["misturar"],
    ).status_code == 200
    assert api.post(f"/receitas/{massa['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200
    composto = _produto(api, "Pão composto 020")
    assert _put(
        api,
        composto["id"],
        linhas=[
            {"ingrediente_id": ingrediente_massa, "quantidade": 1000, "unidade": "g", "funcao": "massa"},
            {"ingrediente_id": fermento, "quantidade": "1.2", "unidade": "g", "funcao": "massa"},
        ],
        formato="forma_enriquecida",
        rendimento_quantidade=2,
        rendimento_unidade="un",
        peso_unidade_g=None,
        unidades_desejadas=10,
        modo_fazer=["dividir", "assar"],
    ).status_code == 200
    assert api.post(f"/receitas/{composto['id']}/publicar").status_code == 200
    rascunho = _produto(api, "Pão rascunho 020", confirmado_inexistente=True)
    assert _put(
        api,
        rascunho["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": 500, "unidade": "g"}],
        peso_unidade_g=500,
        formato="livre",
    ).status_code == 200

    pedido = loja.pedido("N1", "confirmed", dia)
    for gestao, nome, quantidade in (
        (simples, "Pão simples 020", 4),
        (composto, "Pão composto 020", 4),
        (rascunho, "Pão rascunho 020", 3),
    ):
        produto_loja, (variante,) = loja.produto(nome, base, [("Un", 1)])
        _vincular(gestao["id"], produto_loja)
        loja.item(
            pedido, produto=produto_loja, variante=variante, quantidade=quantidade,
            unidades=quantidade, base=base,
        )
    massa_loja = loja.massa("Massa do criador 020", base)
    loja.item(pedido, massa=massa_loja, nome_massa="Massa do criador 020", nome_forma="Bola", quantidade=2)

    corpo = _painel(api)
    necessidade = corpo["necessidade"]
    por_nome = {i["ingrediente"]: i for i in necessidade["itens"]}

    # a conta da Gestão é a mesma da comanda: calcular_foto para 4 pães de cada receita
    org = criar_org("loja")
    ativar_escopo(db, org)
    pesagem = {}
    for produto in (simples, composto):
        foto = calcular_foto(db, UUID(produto["id"]), 4)
        for folha in somar_pesagem([foto]):
            pesagem[folha["nome"]] = pesagem.get(folha["nome"], Decimal(0)) + Decimal(folha["quantidade_g"])

    assert set(por_nome) == {"Farinha de trigo", "Fermento"}  # água não controla estoque
    for nome in ("Farinha de trigo", "Fermento"):
        assert por_nome[nome]["precisa"] == pytest.approx(float(pesagem[nome]), abs=0.01)
        assert por_nome[nome]["unidade_base"] == "g"
    assert por_nome["Farinha de trigo"]["precisa"] > 4000  # 4 do simples (1 kg cada) + a massa base
    assert por_nome["Farinha de trigo"]["tem"] == pytest.approx(1000)
    assert por_nome["Farinha de trigo"]["falta"] == pytest.approx(por_nome["Farinha de trigo"]["precisa"] - 1000)
    assert por_nome["Fermento"]["tem"] == 0
    assert por_nome["Fermento"]["falta"] == pytest.approx(por_nome["Fermento"]["precisa"])

    # rascunho (3) e criador (2) ficam de fora e dizem por quê
    assert necessidade["fora_da_conta"] == 5
    fora = {i["nome"].split(" · ")[0]: i for i in necessidade["fora_da_conta_itens"]}
    assert fora["Pão rascunho 020"]["motivo"] == "rascunho" and fora["Pão rascunho 020"]["paes_fisicos"] == 3
    assert fora["Massa do criador 020"]["motivo"] == "sem_vinculo"


def test_necessidade_sem_fonte_loja_e_vazia_e_com_loja_fora_do_ar_e_nula(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    sem_loja = Api(client, entrar(client, "sem-loja-020a", "dono", org="padaria-020a", fonte_loja=False))
    corpo = _painel(sem_loja)
    assert corpo["necessidade"] == {"itens": [], "fora_da_conta": 0, "fora_da_conta_itens": []}
    assert corpo["fornadas"] == []

    def falha(*_a, **_k):
        raise OperationalError("SELECT", {}, Exception("loja fora do ar"))

    monkeypatch.setattr("app.api.v1.hoje.consultar_demanda", falha)
    com_loja = Api(client, entrar(client, "com-loja-020a", "dono", org="padaria-020b"))
    corpo = _painel(com_loja)
    assert corpo["compatibilidade"]["ok"] is False
    assert corpo["necessidade"] is None
    assert "loja fora do ar" not in str(corpo)


# --- 5: pendências ----------------------------------------------------------------------------


def test_pendencias_falta_antes_de_atencao_singular_plural_e_ausentes_quando_zero(api, loja):
    assert _painel(api)["pendencias"] == []

    api.entrada([farinha(validade=None)])  # entrada com lote sem validade
    _produto(api, "Chocolate pronto", modalidade="comprado", unidade_venda="un")
    _produto(api, "Pão A 020", confirmado_inexistente=True)
    base = loja.base("TRAD")
    produto_loja, (variante,) = loja.produto("Pão da Loja 020", base, [("Un", 1)])
    pedido = loja.pedido("P1", "confirmed", _hoje() + timedelta(days=1))
    loja.item(pedido, produto=produto_loja, variante=variante, quantidade=2, unidades=2, base=base)

    corpo = _painel(api)
    codigos = [p["codigo"] for p in corpo["pendencias"]]
    assert codigos == [
        "produtos_sem_receita",
        "demanda_sem_vinculo",
        "comprado_sem_item",
        "entradas_pendentes",
    ]
    assert [p["estado"] for p in corpo["pendencias"]] == ["falta", "falta", "atencao", "atencao"]
    textos = {p["codigo"]: p for p in corpo["pendencias"]}
    assert textos["produtos_sem_receita"]["texto"] == "1 produto sem receita publicada"
    assert textos["produtos_sem_receita"]["acao"] == "Ver produtos"
    assert textos["produtos_sem_receita"]["href"] == "/produtos?filtro=pendentes"
    assert textos["comprado_sem_item"]["texto"] == "1 produto comprado sem item de estoque"
    assert textos["entradas_pendentes"]["texto"] == "1 entrada sem validade"
    assert textos["entradas_pendentes"]["href"] == "/entradas?filtro=pendentes"
    assert textos["entradas_pendentes"]["acao"] == "Ver entradas"

    _produto(api, "Pão B 020", confirmado_inexistente=True)
    _produto(api, "Biscoito pronto", modalidade="comprado", unidade_venda="un")
    api.entrada([farinha(validade=None, item_nome="Sal 020", ingrediente_nome="Sal 020", marca="")])
    corpo = _painel(api)
    textos = {p["codigo"]: p["texto"] for p in corpo["pendencias"]}
    assert textos["produtos_sem_receita"] == "2 produtos sem receita publicada"
    assert textos["comprado_sem_item"] == "2 produtos comprados sem item de estoque"
    assert textos["entradas_pendentes"] == "2 entradas sem validade"


def test_pendencia_de_custo_parcial_e_so_de_receita_publicada(api):
    farinha_id = _farinha_com_custo(api, 12)
    sal = api.ingrediente("Sal 020 sem custo", "g", "Sal e temperos")  # nunca entrou: sem custo
    pao = _produto(api, "Pão com custo parcial", confirmado_inexistente=True)
    assert _put(
        api,
        pao["id"],
        linhas=[
            {"ingrediente_id": farinha_id, "quantidade": 1000, "unidade": "g"},
            {"ingrediente_id": sal, "quantidade": 20, "unidade": "g"},
        ],
        rendimento_quantidade=2,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="livre",
    ).status_code == 200
    assert _pendencia(_painel(api), "custo_parcial") is None  # rascunho não conta
    assert api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200

    pendencia = _pendencia(_painel(api), "custo_parcial")
    assert pendencia["texto"] == "1 receita com custo parcial"
    assert pendencia["estado"] == "atencao" and pendencia["href"] == "/receitas"
    assert _pendencia(_painel(api), "produtos_sem_receita") is None


# --- 6: indicadores ---------------------------------------------------------------------------


def test_indicadores_contam_receitas_e_so_as_entradas_do_mes(api):
    farinha_id = _farinha_com_custo(api, 12)  # entrada de hoje: não conta nas do mês de valor 0
    # _farinha_com_custo lança a entrada com a data de ontem; refazemos o que importa abaixo
    _publicar_pao(api, "Pão publicado 020", farinha_id, 500)
    _produto(api, "Pão rascunho ind 020", confirmado_inexistente=True)
    _produto(api, "Cobertura de pão", uso_venda=False, uso_componente=True)  # componente não é "produzido de venda"

    corpo = _painel(api)
    inicio = _hoje().replace(day=1)
    do_mes = [
        e for e in api.get("/entradas").json()["entradas"] if e["data"] >= inicio.isoformat()
    ]
    ind = corpo["indicadores"]
    assert ind["receitas_publicadas"] == 1
    assert ind["produtos_produzidos"] == 3
    assert ind["entradas_mes_qtd"] == len(do_mes)

    base_qtd = ind["entradas_mes_qtd"]
    base_valor = ind["entradas_mes_valor"]

    hoje = _hoje().isoformat()
    assert api.entrada(
        [farinha(item_nome="Açúcar 020", ingrediente_nome="Açúcar 020", marca="", quantidade=2, custo=10)],
        data=hoje,
    ).status_code == 201
    assert api.entrada(
        [farinha(item_nome="Aveia 020", ingrediente_nome="Aveia 020", marca="", quantidade=1, custo=5)],
        data=hoje,
    ).status_code == 201
    mes_passado = (inicio - timedelta(days=1)).isoformat()
    assert api.entrada(
        [farinha(item_nome="Milho 020", ingrediente_nome="Milho 020", marca="", quantidade=100, custo=9)],
        data=mes_passado,
    ).status_code == 201

    ind = _painel(api)["indicadores"]
    assert ind["entradas_mes_qtd"] == base_qtd + 2  # a do mês passado ficou de fora
    assert ind["entradas_mes_valor"] == pytest.approx(base_valor + 20 + 5)


def test_indicadores_zerados_sem_nada(api):
    assert _painel(api)["indicadores"] == {
        "receitas_publicadas": 0,
        "produtos_produzidos": 0,
        "entradas_mes_qtd": 0,
        "entradas_mes_valor": 0,
    }


# --- 7: preço informado -----------------------------------------------------------------------


def _preparar_custos(api, nome="Pão preço 020"):
    """Pão de 500 g com farinha a R$ 12/kg: custo variável 6; rateio de R$ 4/kg = 2."""
    farinha_id = _farinha_com_custo(api, 12)
    pao = _publicar_pao(api, nome, farinha_id, 500)
    assert api.post("/custos/fixos", {"nome": "Aluguel", "valor_mensal": 400}).status_code == 200
    params = api.c.put(
        "/api/v1/custos/parametros", json={"massa_mensal_kg": 100, "regra": None}, headers=api.h
    )
    assert params.status_code == 200, params.text
    return pao


def _preco(api, produto_id, preco):
    return api.c.put(f"/api/v1/custos/produtos/{produto_id}/preco", json={"preco": preco}, headers=api.h)


def _linha_custos(corpo, produto_id):
    return next(p for p in corpo["produtos"] if p["produto_id"] == produto_id)


def test_preco_informado_sem_loja_calcula_como_a_loja(api):
    pao = _preparar_custos(api)
    antes = _linha_custos(api.get("/custos").json(), pao["id"])
    assert antes["preco_manual"] is None and antes["preco_proprio"] is None
    assert antes["custo_variavel"] == pytest.approx(6)
    assert antes["rateio"] == pytest.approx(2)

    resposta = _preco(api, pao["id"], 20)
    assert resposta.status_code == 200, resposta.text
    linha = _linha_custos(resposta.json(), pao["id"])
    assert linha["preco_manual"] == pytest.approx(20)
    proprio = linha["preco_proprio"]
    assert proprio["variante"] == "Preço informado"
    assert proprio["unidades"] == 1 and proprio["campo_unidades"] == "preco_manual"
    assert proprio["preco"] == pytest.approx(20) and proprio["preco_por_unidade"] == pytest.approx(20)
    assert proprio["mc"] == pytest.approx(14)
    assert proprio["mc_pct"] == pytest.approx(70)
    assert proprio["markup"] == pytest.approx(2.5)
    assert proprio["resultado"] == pytest.approx(12)  # 20 - (6 + 2)
    assert linha["loja"] == []

    # o GET devolve o mesmo
    assert _linha_custos(api.get("/custos").json(), pao["id"])["preco_proprio"] == proprio

    limpo = _preco(api, pao["id"], None)
    assert limpo.status_code == 200
    linha = _linha_custos(limpo.json(), pao["id"])
    assert linha["preco_manual"] is None and linha["preco_proprio"] is None


@pytest.mark.parametrize("invalido", [0, -5])
def test_preco_informado_precisa_ser_maior_que_zero(api, invalido):
    pao = _preparar_custos(api)
    resposta = _preco(api, pao["id"], invalido)
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert detalhe["codigo"] == "preco_invalido"
    assert detalhe["mensagem"] == "O preço precisa ser maior que zero."
    assert _linha_custos(api.get("/custos").json(), pao["id"])["preco_manual"] is None


def test_preco_informado_so_quem_lanca_e_produto_existente(client, api):
    pao = _preparar_custos(api)
    assert _preco(api, "00000000-0000-0000-0000-000000000000", 10).status_code == 404
    with TestClient(client.app, base_url="http://testserver") as outro:
        leitor = Api(outro, entrar(outro, "leitor-020", "somente_leitura", org="loja"))
        assert _preco(leitor, pao["id"], 10).status_code == 403


def test_org_sem_fonte_loja_usa_so_o_preco_informado(client):
    api = Api(client, entrar(client, "sem-loja-020b", "dono", org="padaria-020c", fonte_loja=False))
    pao = _preparar_custos(api)
    # mesmo com origem na Loja, sem fonte_loja a Loja não é consultada
    _vincular(pao["id"], "11111111-1111-1111-1111-111111111111")
    linha = _linha_custos(api.get("/custos").json(), pao["id"])
    assert linha["loja"] == [] and linha["preco_proprio"] is None

    resposta = _preco(api, pao["id"], 20)
    assert resposta.status_code == 200, resposta.text
    linha = _linha_custos(resposta.json(), pao["id"])
    assert linha["loja"] == []
    assert linha["preco_proprio"]["resultado"] == pytest.approx(12)


def test_preco_da_loja_tem_precedencia_sobre_o_informado(api, loja):
    pao = _preparar_custos(api)
    produto_loja, _ = loja.produto("Pão preço 020", None, [("Un", 1)])  # R$ 10,00 na Loja
    _vincular(pao["id"], produto_loja)
    resposta = _preco(api, pao["id"], 20)
    assert resposta.status_code == 200, resposta.text
    linha = _linha_custos(resposta.json(), pao["id"])
    assert linha["preco_manual"] == pytest.approx(20)  # guardado, mas a Loja manda
    assert len(linha["loja"]) == 1 and linha["loja"][0]["preco"] == pytest.approx(10)
    assert linha["preco_proprio"] is None
