"""Entradas, saldo, ajuste, junção, ledger e fluxo, pela API, com Postgres de verdade."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.conftest import entrar

ONTEM = (date.today() - timedelta(days=1)).isoformat()


def validade_em(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).isoformat()


class Api:
    def __init__(self, client, dados):
        self.c = client
        self.h = {"X-CSRF-Token": dados["csrf"]}

    def get(self, rota, **p):
        return self.c.get(f"/api/v1{rota}", params=p)

    def post(self, rota, corpo=None):
        return self.c.post(f"/api/v1{rota}", json=corpo or {}, headers=self.h)

    def patch(self, rota, corpo):
        return self.c.patch(f"/api/v1{rota}", json=corpo, headers=self.h)

    def local_id(self) -> str:
        return self.get("/locais").json()[0]["id"]

    def entrada(self, linhas, *, chave=None, motivo="compra_sem_nota", data=ONTEM, **extra):
        corpo = {
            "chave": chave or uuid.uuid4().hex,
            "data": data,
            "local_id": self.local_id(),
            "motivo": motivo,
            "linhas": linhas,
            **extra,
        }
        return self.post("/entradas", corpo)

    def saldo(self, ingrediente_id) -> float:
        return next(
            i for i in self.get("/ingredientes").json()["ingredientes"] if i["id"] == ingrediente_id
        )["saldo"]


def farinha(**mudar):
    base = {
        "item_nome": "Farinha de trigo",
        "marca": "Dona Benta",
        "unidade_controle": "massa",
        "ingrediente_nome": "Farinha de trigo",
        "quantidade": 25,
        "unidade": "kg",
        "validade": validade_em(120),
        "custo": 4.5,
    }
    base.update(mudar)
    return base


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def ingrediente_por_nome(api, nome):
    return next(i for i in api.get("/ingredientes").json()["ingredientes"] if i["nome"] == nome)


# --- entrada ---------------------------------------------------------------------------------


def test_entrada_cria_ingrediente_item_lote_e_saldo(api):
    resposta = api.entrada([farinha()])
    assert resposta.status_code == 201, resposta.text
    e = resposta.json()
    assert e["situacao"] == "completa" and e["local"] == "Despensa"
    linha = e["linhas"][0]
    assert linha["lote"] == f"E{date.today() - timedelta(days=1):%Y%m%d}-01"
    assert linha["quantidade_base"] == 25000 and linha["unidade_base"] == "g"
    assert linha["valor_total"] == 112.5  # 25 kg x R$ 4,50 por kg
    ing = ingrediente_por_nome(api, "Farinha de trigo")
    assert ing["saldo"] == 25000 and ing["itens"] == 1 and ing["lotes"] == 1


def test_embalagem_conta_pelo_conteudo(api):
    resposta = api.entrada(
        [
            {
                "item_nome": "Fermento seco 500 g",
                "marca": "Fleischmann",
                "unidade_controle": "embalagem",
                "conteudo_embalagem": 500,
                "ingrediente_nome": "Fermento seco",
                "ingrediente_unidade_base": "g",
                "quantidade": 3,
                "unidade": "emb",
                "validade": validade_em(200),
                "custo": 6,
            }
        ]
    )
    assert resposta.status_code == 201, resposta.text
    linha = resposta.json()["linhas"][0]
    assert linha["quantidade_base"] == 1500 and linha["valor_total"] == 18.0
    assert api.saldo(linha["ingrediente_id"]) == 1500


def test_embalagem_sem_conteudo_e_recusada_na_hora(api):
    linha = {
        "item_nome": "Fermento",
        "unidade_controle": "embalagem",
        "ingrediente_nome": "Fermento",
        "ingrediente_unidade_base": "g",
        "quantidade": 2,
        "unidade": "emb",
        "sem_validade": True,
    }
    analise = api.post("/entradas/verificar", {"linhas": [linha]}).json()["linhas"][0]
    assert analise["incompleta"] and "embalagem_sem_conteudo" in [
        p["codigo"] for p in analise["pendencias"]
    ]
    resposta = api.entrada([linha])
    assert resposta.status_code == 422
    assert api.get("/entradas").json()["entradas"] == []


def test_massa_nao_vira_volume(api):
    leite = api.post("/ingredientes", {"nome": "Leite", "unidade_base": "ml"}).json()
    resposta = api.entrada(
        [
            {
                "item_nome": "Leite em pó",
                "unidade_controle": "massa",
                "ingrediente_id": leite["id"],
                "quantidade": 1,
                "unidade": "kg",
                "sem_validade": True,
            }
        ]
    )
    assert resposta.status_code == 422
    codigos = [p["codigo"] for p in resposta.json()["detail"]["linhas"][0]["pendencias"]]
    assert "unidade_incompativel" in codigos
    assert api.saldo(leite["id"]) == 0


def test_unidade_fora_do_controle_e_recusada(api):
    resposta = api.entrada([farinha(unidade="l")])
    assert resposta.status_code == 422
    assert "unidade_invalida" in str(resposta.json())


def test_entrada_e_atomica(api):
    resposta = api.entrada(
        [farinha(), farinha(item_nome="Sal", ingrediente_nome="Sal", quantidade=0)]
    )
    assert resposta.status_code == 422
    assert api.get("/entradas").json()["entradas"] == []
    assert api.get("/ingredientes").json()["ingredientes"] == []
    assert api.get("/catalogo").json()["itens"] == []


def test_entrada_e_idempotente(api):
    chave = "chave-unica-123"
    primeira = api.entrada([farinha()], chave=chave)
    segunda = api.entrada([farinha()], chave=chave)
    assert primeira.status_code == 201 and segunda.status_code == 200
    assert primeira.json()["id"] == segunda.json()["id"]
    assert len(api.get("/entradas").json()["entradas"]) == 1
    assert ingrediente_por_nome(api, "Farinha de trigo")["saldo"] == 25000


def test_parecido_bloqueia_ate_decidir(api):
    api.entrada([farinha()])
    parecida = farinha(item_nome="Farinha trigo", ingrediente_nome="Farinha trigo", quantidade=5)
    analise = api.post("/entradas/verificar", {"linhas": [parecida]}).json()["linhas"][0]
    assert analise["a_decidir"]
    assert analise["ingrediente_parecidos"][0]["nome"] == "Farinha de trigo"
    assert analise["item_parecidos"][0]["nome"] == "Farinha de trigo"

    recusada = api.entrada([parecida])
    assert recusada.status_code == 422
    assert recusada.json()["detail"]["codigo"] == "parecido_nao_decidido"
    assert len(api.get("/ingredientes").json()["ingredientes"]) == 1

    # "Usar este": aponta para o ingrediente e o item que já existem
    existente = api.get("/catalogo").json()["itens"][0]
    ok = api.entrada(
        [
            {
                "item_id": existente["id"],
                "quantidade": 5,
                "unidade": "kg",
                "validade": validade_em(100),
            }
        ]
    )
    assert ok.status_code == 201
    assert api.saldo(existente["ingrediente_id"]) == 30000


def test_criar_novo_cria_mas_o_par_continua_apontado_ate_alguem_decidir(api):
    api.entrada([farinha()])
    outra = farinha(
        item_nome="Farinha trigo",
        ingrediente_nome="Farinha trigo",
        decisao_item="novo",
        decisao_ingrediente="novo",
    )
    assert api.entrada([outra]).status_code == 201
    corpo = api.get("/ingredientes").json()
    assert len(corpo["ingredientes"]) == 2
    # "Criar novo" cria; quem afirma que são diferentes é "São diferentes" na tela Ingredientes.
    # Até lá, "Farinha de trigo" e "Farinha trigo" aparecem juntas no aviso de parecidos.
    assert [(p["a"]["nome"], p["b"]["nome"]) for p in corpo["pares_parecidos"]] == [
        ("Farinha de trigo", "Farinha trigo")
    ]


def test_ingrediente_criado_com_confirmar_novo_tambem_continua_apontado(api):
    api.post("/ingredientes", {"nome": "Farinha de trigo", "unidade_base": "g"})
    api.post("/ingredientes", {"nome": "Farinha trigo", "unidade_base": "g", "confirmar_novo": True})
    assert len(api.get("/ingredientes").json()["pares_parecidos"]) == 1


def test_nome_repetido_e_recusado_pela_api(api):
    assert api.post("/ingredientes", {"nome": "Sal", "unidade_base": "g"}).status_code == 201
    igual = api.post("/ingredientes", {"nome": "  SAL ", "unidade_base": "g"})
    assert igual.status_code == 409 and igual.json()["detail"]["codigo"] == "ingrediente_ja_existe"
    api.post("/ingredientes", {"nome": "Farinha de trigo", "unidade_base": "g"})
    parecido = api.post("/ingredientes", {"nome": "Farinha trigo", "unidade_base": "g"})
    assert (
        parecido.status_code == 409
        and parecido.json()["detail"]["codigo"] == "ingrediente_parecido"
    )
    forcado = api.post(
        "/ingredientes", {"nome": "Farinha trigo", "unidade_base": "g", "confirmar_novo": True}
    )
    assert forcado.status_code == 201


def test_item_igual_ao_existente_e_recusado(api):
    api.entrada([farinha()])
    de_novo = api.entrada([farinha(ingrediente_nome="Outro nome")])
    assert de_novo.status_code == 422
    assert "item_ja_existe" in str(de_novo.json())


def test_validade_ausente_deixa_a_entrada_pendente_ate_informar(api):
    e = api.entrada([farinha(validade=None)]).json()
    assert e["situacao"] == "pendente" and e["linhas"][0]["validade_pendente"]
    assert [x["id"] for x in api.get("/entradas", filtro="pendentes").json()["entradas"]] == [
        e["id"]
    ]
    assert api.get("/fluxo").json()["etapas"][0]["estado"] == "atencao"

    lote = e["linhas"][0]["lote_id"]
    assert api.patch(f"/lotes/{lote}", {}).status_code == 422
    assert (
        api.patch(f"/lotes/{lote}", {"validade": validade_em(30), "sem_validade": True}).status_code
        == 422
    )
    assert api.patch(f"/lotes/{lote}", {"sem_validade": True}).status_code == 200
    assert api.get("/entradas", filtro="pendentes").json()["entradas"] == []
    assert api.get(f"/entradas/{e['id']}").json()["situacao"] == "completa"


def test_custo_em_branco_e_desconhecido_nao_zero(api):
    e = api.entrada([farinha(custo=None)]).json()
    assert e["linhas"][0]["custo"] is None and e["linhas"][0]["valor_total"] is None
    assert e["valor"] is None
    ing = api.get(f"/ingredientes/{e['linhas'][0]['ingrediente_id']}").json()
    assert ing["custo_medio_base"] is None


def test_filtros_de_entradas_e_data_futura(api):
    api.entrada([farinha()])
    assert len(api.get("/entradas", filtro="sem_nota").json()["entradas"]) == 1
    assert api.get("/entradas", filtro="com_nota").json()["entradas"] == []
    futura = api.entrada([farinha(item_nome="Sal", ingrediente_nome="Sal")], data=validade_em(5))
    assert futura.status_code == 422 and futura.json()["detail"]["codigo"] == "data_futura"
    com_nota = api.post(
        "/entradas",
        {
            "chave": "com-nota-123",
            "data": ONTEM,
            "local_id": api.local_id(),
            "tipo": "com_nota",
            "motivo": "compra_sem_nota",
            "linhas": [farinha()],
        },
    )
    assert (
        com_nota.status_code == 422 and com_nota.json()["detail"]["codigo"] == "tipo_indisponivel"
    )


def test_lote_automatico_sequencial(api):
    e = api.entrada(
        [
            farinha(),
            farinha(item_nome="Sal", ingrediente_nome="Sal", marca="", quantidade=1, custo=None),
        ]
    ).json()
    codigos = [lc["lote"] for lc in e["linhas"]]
    dia = f"{date.today() - timedelta(days=1):%Y%m%d}"
    assert codigos == [f"E{dia}-01", f"E{dia}-02"]


# --- ledger imutável ------------------------------------------------------------------------


def test_movimento_nao_se_altera_nem_se_apaga(api, db):
    api.entrada([farinha()])
    with pytest.raises(DBAPIError) as alterar:
        db.execute(text("UPDATE movimentos SET motivo = 'adulterado'"))
    assert "append_only" in str(alterar.value)
    db.rollback()
    with pytest.raises(DBAPIError) as apagar:
        db.execute(text("DELETE FROM movimentos"))
    assert "append_only" in str(apagar.value)
    db.rollback()
    assert db.execute(text("SELECT count(*) FROM movimentos")).scalar() == 1


# --- ajuste ---------------------------------------------------------------------------------


def test_ajuste_corrige_por_contramovimento_com_motivo(api):
    e = api.entrada([farinha()]).json()
    linha = e["linhas"][0]
    url = f"/ingredientes/{linha['ingrediente_id']}/ajustes"
    base = {"lote_id": linha["lote_id"], "saldo_contado_base": 20000}
    assert api.post(url, {**base, "motivo": ""}).status_code == 422
    assert (
        api.post(url, {**base, "saldo_contado_base": 25000, "motivo": "conferi"}).json()["detail"][
            "codigo"
        ]
        == "sem_diferenca"
    )
    ok = api.post(url, {**base, "motivo": "Contagem do mês"})
    assert ok.status_code == 201, ok.text
    assert api.saldo(linha["ingrediente_id"]) == 20000
    historico = ok.json()["movimentos"]
    assert {m["tipo"] for m in historico} == {"entrada", "ajuste"}
    ajuste = next(m for m in historico if m["tipo"] == "ajuste")
    assert ajuste["quantidade_base"] == -5000 and ajuste["motivo"] == "Contagem do mês"


def test_ajuste_so_no_lote_do_proprio_ingrediente(api):
    a = api.entrada([farinha()]).json()["linhas"][0]
    b = api.entrada([farinha(item_nome="Sal", ingrediente_nome="Sal", marca="")]).json()["linhas"][
        0
    ]
    resposta = api.post(
        f"/ingredientes/{b['ingrediente_id']}/ajustes",
        {"lote_id": a["lote_id"], "saldo_contado_base": 1, "motivo": "teste"},
    )
    assert (
        resposta.status_code == 422
        and resposta.json()["detail"]["codigo"] == "lote_de_outro_ingrediente"
    )


# --- junção ---------------------------------------------------------------------------------


def _dois_ingredientes_parecidos(api):
    a = api.entrada([farinha()]).json()["linhas"][0]
    b = api.entrada(
        [
            farinha(
                item_nome="Farinha trigo tipo 1",
                marca="Outra",
                ingrediente_nome="Farinha trigo",
                decisao_ingrediente="novo",
                decisao_item="novo",
                quantidade=10,
            )
        ]
    ).json()["linhas"][0]
    return a["ingrediente_id"], b["ingrediente_id"]


def test_juntar_soma_o_saldo_inativa_o_vazio_e_nada_se_apaga(api, db):
    mantem, remove = _dois_ingredientes_parecidos(api)
    antes = db.execute(text("SELECT count(*) FROM movimentos")).scalar()
    resposta = api.post("/ingredientes/juntar", {"mantem_id": mantem, "remove_id": remove})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert len(corpo["itens_detalhe"]) == 2 and len(corpo["lotes_detalhe"]) == 2
    assert api.saldo(mantem) == 35000
    ativos = api.get("/ingredientes").json()["ingredientes"]
    assert [i["id"] for i in ativos] == [mantem]
    assert (
        api.get(f"/ingredientes/{remove}").json()["juntado_em_id"] == mantem
    )  # continua consultável
    depois = db.execute(text("SELECT count(*) FROM movimentos")).scalar()
    assert depois == antes + 1  # um movimento de junção por item movido; nada foi apagado
    assert db.execute(text("SELECT count(*) FROM ingredientes")).scalar() == 2
    assert "juncao" in {m["tipo"] for m in corpo["movimentos"]}


def test_juntar_recusa_unidades_diferentes_e_o_mesmo_ingrediente(api):
    a = api.post("/ingredientes", {"nome": "Água", "unidade_base": "ml"}).json()["id"]
    b = api.post("/ingredientes", {"nome": "Sal", "unidade_base": "g"}).json()["id"]
    assert api.post("/ingredientes/juntar", {"mantem_id": a, "remove_id": b}).status_code == 422
    assert api.post("/ingredientes/juntar", {"mantem_id": a, "remove_id": a}).status_code == 422


def test_marcar_distintos_tira_o_par_da_lista(api):
    mantem, remove = _dois_ingredientes_parecidos(api)
    # criados com "criar novo": o par ainda é apontado
    assert len(api.get("/ingredientes").json()["pares_parecidos"]) == 1
    # "São diferentes" é a decisão que tira o par do aviso
    resposta = api.post("/ingredientes/distintos", {"a_id": mantem, "b_id": remove})
    assert resposta.status_code == 204, resposta.text
    assert api.get("/ingredientes").json()["pares_parecidos"] == []
    # e a decisão não se repete se a pessoa clicar de novo
    assert api.post("/ingredientes/distintos", {"a_id": remove, "b_id": mantem}).status_code == 204
    assert api.get("/ingredientes").json()["pares_parecidos"] == []


# --- fluxo e Hoje ---------------------------------------------------------------------------


def estados(api):
    return {e["id"]: e["estado"] for e in api.get("/fluxo").json()["etapas"]}


def test_fluxo_comeca_em_falta_e_aponta_o_proximo_passo(api):
    fluxo = api.get("/fluxo").json()
    assert estados(api) == {
        "entradas": "falta",
        "ingredientes": "falta",
        "produtos": None,
        "receitas": None,
        "producao": None,
    }
    assert (
        fluxo["proximo_passo"]["etapa"] == "entradas"
        and fluxo["proximo_passo"]["acao"] == "Nova entrada"
    )
    hoje = api.get("/hoje").json()
    assert hoje["fluxo"]["proximo_passo"]["etapa"] == "entradas"


def test_fluxo_em_dia_atencao_por_validade_e_por_falta_de_saldo(api):
    e = api.entrada([farinha()]).json()["linhas"][0]
    assert estados(api)["entradas"] == "em_dia" and estados(api)["ingredientes"] == "em_dia"
    assert api.get("/fluxo").json()["proximo_passo"] is None

    perto = api.entrada(
        [
            farinha(
                item_nome="Fermento",
                marca="X",
                ingrediente_nome="Fermento",
                validade=validade_em(3),
                quantidade=2,
            )
        ]
    ).json()["linhas"][0]
    assert estados(api)["ingredientes"] == "atencao"
    fluxo = api.get("/fluxo").json()
    assert "vence" in fluxo["etapas"][1]["frase"]
    hoje = api.get("/hoje").json()
    assert [v["ingrediente"] for v in hoje["vence_em_7_dias"]] == ["Fermento"]
    assert hoje["vence_em_7_dias"][0]["dias"] == 3

    # zera o saldo do fermento: some o alerta de validade, aparece "sem saldo"
    api.post(
        f"/ingredientes/{perto['ingrediente_id']}/ajustes",
        {"lote_id": perto["lote_id"], "saldo_contado_base": 0, "motivo": "acabou"},
    )
    assert [s["nome"] for s in api.get("/hoje").json()["sem_saldo"]] == ["Fermento"]
    assert api.get("/hoje").json()["vence_em_7_dias"] == []
    assert estados(api)["ingredientes"] == "atencao"
    assert e["lote_id"]


def test_filtros_de_ingredientes(api):
    api.entrada([farinha()])
    api.entrada(
        [
            farinha(
                item_nome="Fermento",
                marca="X",
                ingrediente_nome="Fermento",
                validade=validade_em(2),
            )
        ]
    )
    api.post("/ingredientes", {"nome": "Sal", "unidade_base": "g"})

    def nomes(filtro):
        return sorted(
            i["nome"] for i in api.get("/ingredientes", filtro=filtro).json()["ingredientes"]
        )

    assert nomes("todos") == ["Farinha de trigo", "Fermento", "Sal"]
    assert nomes("com_saldo") == ["Farinha de trigo", "Fermento"]
    assert nomes("sem_saldo") == ["Sal"]
    assert nomes("vence7") == ["Fermento"]


def test_local_padrao_unico_e_nome_repetido(api):
    assert api.get("/locais").json()[0]["nome"] == "Despensa"
    freezer = api.post("/locais", {"nome": "Freezer"})
    assert freezer.status_code == 201 and freezer.json()["padrao"] is False
    assert api.post("/locais", {"nome": "  freezer "}).status_code in (409, 422)
    api.patch(f"/locais/{freezer.json()['id']}", {"padrao": True})
    locais = {lc["nome"]: lc["padrao"] for lc in api.get("/locais").json()}
    assert locais == {"Despensa": False, "Freezer": True}
