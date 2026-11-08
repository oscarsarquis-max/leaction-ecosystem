"""Organizações: isolamento, admin da plataforma, escolha de organização e o que a sessão mostra."""

import uuid
from datetime import date, timedelta

import pytest
from app.db.escopo import EscopoViolado, ativar_escopo
from app.models.estoque import Ingrediente, ItemEstoque, Lote, Movimento
from app.models.organizacao import Membro, Organizacao
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.conftest import SENHA, criar_org, criar_usuario, entrar
from tests.test_estoque import ONTEM, Api, farinha, validade_em


@pytest.fixture()
def duas_orgs(client):
    from app.main import create_app
    from fastapi.testclient import TestClient

    a = Api(client, entrar(client, "dona-a", "dono", org="org-a"))
    with TestClient(create_app(), base_url="http://testserver") as client_b:
        b = Api(client_b, entrar(client_b, "dono-b", "dono", org="org-b", fonte_loja=False))
        yield a, b


def test_cada_organizacao_so_ve_o_que_e_seu(duas_orgs):
    a, b = duas_orgs
    ea = a.entrada([farinha()])
    assert ea.status_code == 201, ea.text
    linha = ea.json()["linhas"][0]
    entrada_id = ea.json()["id"]

    assert b.get("/ingredientes").json()["ingredientes"] == []
    assert b.get("/entradas").json()["entradas"] == []
    catalogo = b.get("/catalogo").json()
    assert catalogo["itens"] == [] and catalogo["ingredientes"] == []
    assert [lc["nome"] for lc in catalogo["locais"]] == ["Despensa"]
    assert b.get("/fluxo").json()["etapas"][0]["estado"] == "falta"
    assert [m["usuario"] for m in b.get("/usuarios").json()] == ["dono-b"]

    # ids de outra organização simplesmente não existem
    assert b.get(f"/ingredientes/{linha['ingrediente_id']}").status_code == 404
    assert b.get(f"/entradas/{entrada_id}").status_code == 404
    assert (
        b.patch(f"/ingredientes/{linha['ingrediente_id']}", {"nome": "Invasor"}).status_code == 404
    )
    assert b.patch(f"/lotes/{linha['lote_id']}", {"sem_validade": True}).status_code == 404
    ajuste = b.post(
        f"/ingredientes/{linha['ingrediente_id']}/ajustes",
        {"lote_id": linha["lote_id"], "saldo_contado_base": 1, "motivo": "invasão"},
    )
    assert ajuste.status_code == 404
    proprio = b.post("/ingredientes", {"nome": "Sal", "unidade_base": "g"}).json()["id"]
    assert (
        b.post(
            "/ingredientes/juntar", {"mantem_id": proprio, "remove_id": linha["ingrediente_id"]}
        ).status_code
        == 404
    )

    # nem usar o item de A numa entrada de B
    item_de_a = a.get("/catalogo").json()["itens"][0]["id"]
    roubo = b.entrada(
        [{"item_id": item_de_a, "quantidade": 1, "unidade": "kg", "sem_validade": True}]
    )
    assert roubo.status_code == 422 and "item_inexistente" in str(roubo.json())
    # e o local de A não serve para B
    local_de_a = a.local_id()
    tentativa = b.post(
        "/entradas",
        {
            "chave": "chave-cruzada-1",
            "data": ONTEM,
            "local_id": local_de_a,
            "motivo": "contagem",
            "linhas": [
                farinha(item_nome="Sal", ingrediente_nome="Sal 2", ingrediente_unidade_base="g")
            ],
        },
    )
    assert (
        tentativa.status_code == 422 and tentativa.json()["detail"]["codigo"] == "local_inexistente"
    )

    # A segue intacta
    assert a.saldo(linha["ingrediente_id"]) == 25000
    assert len(a.get("/entradas").json()["entradas"]) == 1


def test_mesmos_nomes_convivem_em_organizacoes_diferentes(duas_orgs):
    a, b = duas_orgs
    assert a.entrada([farinha()]).status_code == 201
    assert b.entrada([farinha()]).status_code == 201  # mesmo item, mesma marca, outro dono
    ia, ib = (x.get("/catalogo").json()["itens"][0]["id"] for x in (a, b))
    assert ia != ib
    assert a.get("/ingredientes").json()["ingredientes"][0]["saldo"] == 25000
    assert b.get("/ingredientes").json()["ingredientes"][0]["saldo"] == 25000


def test_hoje_so_le_a_loja_na_organizacao_fonte(duas_orgs):
    a, b = duas_orgs
    assert a.get("/hoje").json()["fonte_loja"] is True
    corpo_b = b.get("/hoje").json()
    assert (
        corpo_b["fonte_loja"] is False
        and corpo_b["fornadas"] == []
        and corpo_b["compatibilidade"]["ok"]
    )


def test_isolamento_na_camada_do_orm(duas_orgs, db):
    a, b = duas_orgs
    a.entrada([farinha()])
    b.entrada(
        [farinha(item_nome="Sal", ingrediente_nome="Sal", marca="", unidade="kg", quantidade=2)]
    )
    org_a = db.scalar(select(Organizacao.id).where(Organizacao.nome_curto == "org-a"))
    org_b = db.scalar(select(Organizacao.id).where(Organizacao.nome_curto == "org-b"))

    with Session(db.get_bind()) as s:
        assert s.scalar(select(func.count()).select_from(Ingrediente)) == 2  # sem escopo: vê tudo
        ativar_escopo(s, org_a)
        assert [i.nome for i in s.scalars(select(Ingrediente))] == ["Farinha de trigo"]
        # agregação e junção também são filtradas
        assert s.scalar(select(func.count()).select_from(Ingrediente)) == 1
        assert (
            s.scalar(
                select(func.count())
                .select_from(Lote)
                .join(ItemEstoque, ItemEstoque.id == Lote.item_id)
            )
            == 1
        )
        assert s.scalar(select(func.sum(Movimento.quantidade_base))) == 25000
        # consulta direta pelo id de outra organização volta vazia
        id_b = db.scalar(select(Ingrediente.id).where(Ingrediente.organizacao_id == org_b))
        assert (
            s.get(Ingrediente, id_b) is None
            or s.scalar(select(Ingrediente).where(Ingrediente.id == id_b)) is None
        )

        # gravar em outra organização é recusado; sem informar, entra na atual
        s.add(Ingrediente(organizacao_id=org_b, nome="X", nome_normalizado="x", unidade_base="g"))
        with pytest.raises(EscopoViolado):
            s.flush()
        s.rollback()
        ativar_escopo(s, org_a)
        novo = Ingrediente(nome="Y", nome_normalizado="y", unidade_base="g")
        s.add(novo)
        s.flush()
        assert novo.organizacao_id == org_a
        s.rollback()


# --- admin da plataforma ---------------------------------------------------------------------


def test_admin_da_plataforma_nao_lanca_ajusta_nem_junta(client):
    # há uma organização com dados, e o admin existe fora dela
    dono = Api(client, entrar(client, "dono-x", "dono", org="org-x"))
    linha = dono.entrada([farinha()]).json()["linhas"][0]
    local_de_x = dono.local_id()
    client.cookies.clear()

    dados = entrar(client, "oscar", org=None, admin_plataforma=True)
    assert dados["admin_plataforma"] is True and dados["organizacao"] is None
    assert dados["papel"] is None and dados["permissoes"] == [] and dados["organizacoes"] == []
    adm = Api(client, dados)

    def sem_org(resposta):
        assert resposta.status_code == 403, resposta.text
        assert resposta.json()["detail"]["codigo"] == "sem_organizacao"

    sem_org(
        adm.post(
            "/entradas",
            {
                "chave": "chave-do-admin-1",
                "data": ONTEM,
                "local_id": local_de_x,
                "motivo": "contagem",
                "linhas": [farinha()],
            },
        )
    )
    sem_org(adm.post("/entradas/verificar", {"linhas": [farinha()]}))
    sem_org(adm.post("/ingredientes", {"nome": "Sal", "unidade_base": "g"}))
    sem_org(
        adm.post(
            f"/ingredientes/{linha['ingrediente_id']}/ajustes",
            {"lote_id": linha["lote_id"], "saldo_contado_base": 1, "motivo": "teste"},
        )
    )
    sem_org(
        adm.post(
            "/ingredientes/juntar",
            {"mantem_id": linha["ingrediente_id"], "remove_id": linha["ingrediente_id"]},
        )
    )
    sem_org(adm.patch(f"/lotes/{linha['lote_id']}", {"sem_validade": True}))
    for rota in (
        "/hoje",
        "/fluxo",
        "/ingredientes",
        "/entradas",
        "/catalogo",
        "/locais",
        "/usuarios",
    ):
        sem_org(adm.get(rota))
    sem_org(adm.post("/locais", {"nome": "Freezer"}))


def test_admin_nao_pode_escolher_organizacao(client, db):
    entrar(client, "dono-y", "dono", org="org-y")
    client.cookies.clear()
    dados = entrar(client, "oscar", org=None, admin_plataforma=True)
    org_y = db.scalar(select(Organizacao.id).where(Organizacao.nome_curto == "org-y"))
    h = {"X-CSRF-Token": dados["csrf"]}
    resposta = client.post(
        "/api/v1/auth/organizacao", json={"organizacao_id": str(org_y)}, headers=h
    )
    assert resposta.status_code == 403
    assert client.get("/api/v1/ingredientes").status_code == 403


# --- sessão, CNPJ e escolha de organização --------------------------------------------------


def test_sessao_traz_nome_e_cnpj_da_organizacao(client):
    dados = entrar(client, "gestor", "dono", org="boulangerie")
    org = dados["organizacao"]
    assert (
        org["nome_curto"] == "boulangerie" and org["papel"] == "dono" and org["fonte_loja"] is True
    )
    assert len(org["cnpj"]) == 14 and org["cnpj_formatado"] == (
        f"{org['cnpj'][:2]}.{org['cnpj'][2:5]}.{org['cnpj'][5:8]}/{org['cnpj'][8:12]}-{org['cnpj'][12:]}"
    )
    assert dados["precisa_escolher_organizacao"] is False
    de_novo = client.get("/api/v1/auth/sessao").json()
    assert de_novo["organizacao"]["cnpj_formatado"] == org["cnpj_formatado"]


def test_quem_tem_duas_organizacoes_escolhe_no_login_e_troca_no_menu(client, db):
    criar_usuario("dupla", SENHA, "dono", org="org-1")
    org_2 = criar_org("org-2", fonte_loja=False)
    usuario_id = db.scalar(select(Membro.usuario_id))
    with Session(db.get_bind()) as s:
        s.add(Membro(usuario_id=usuario_id, organizacao_id=org_2, papel="operador"))
        s.commit()

    dados = client.post("/api/v1/auth/entrar", json={"usuario": "dupla", "senha": SENHA}).json()
    assert dados["precisa_escolher_organizacao"] is True and dados["organizacao"] is None
    assert {o["nome_curto"] for o in dados["organizacoes"]} == {"org-1", "org-2"}
    h = {"X-CSRF-Token": dados["csrf"]}
    assert (
        client.get("/api/v1/ingredientes").json()["detail"]["codigo"] == "organizacao_nao_escolhida"
    )

    escolha = client.post(
        "/api/v1/auth/organizacao", json={"organizacao_id": str(org_2)}, headers=h
    )
    assert escolha.status_code == 200 and escolha.json()["organizacao"]["nome_curto"] == "org-2"
    assert escolha.json()["papel"] == "operador"
    assert client.get("/api/v1/ingredientes").status_code == 200
    assert client.get("/api/v1/usuarios").status_code == 403  # operador, nessa organização

    h = {"X-CSRF-Token": client.get("/api/v1/auth/sessao").json()["csrf"]}
    troca = client.post(
        "/api/v1/auth/organizacao", json={"organizacao_id": str(uuid.uuid4())}, headers=h
    )
    assert (
        troca.status_code == 403 and troca.json()["detail"]["codigo"] == "organizacao_nao_permitida"
    )


def test_membro_inativo_ou_organizacao_inativa_nao_entra(client, db):
    criar_usuario("fora", SENHA, "dono", org="org-z")
    with Session(db.get_bind()) as s:
        s.execute(Membro.__table__.update().values(ativo=False))
        s.commit()
    dados = client.post("/api/v1/auth/entrar", json={"usuario": "fora", "senha": SENHA}).json()
    assert dados["organizacao"] is None and dados["organizacoes"] == []
    assert client.get("/api/v1/ingredientes").status_code == 403


def test_cnpj_da_organizacao_e_unico_e_valido(db):
    from sqlalchemy.exc import IntegrityError

    org_id = criar_org("primeira")
    cnpj = db.scalar(select(Organizacao.cnpj).where(Organizacao.id == org_id))
    with pytest.raises(IntegrityError):
        db.add(Organizacao(nome="Duplicada", nome_curto="segunda", cnpj=cnpj))
        db.commit()
    db.rollback()
    with pytest.raises(IntegrityError):
        db.add(Organizacao(nome="Minúsculas", nome_curto="terceira", cnpj="12abc34501de35"))
        db.commit()
    db.rollback()


def test_entrada_continua_funcionando_na_data_de_hoje(client):
    api = Api(client, entrar(client, "hoje", "dono", org="org-h"))
    hoje = date.today().isoformat()
    ok = api.entrada([farinha(validade=(date.today() + timedelta(days=30)).isoformat())], data=hoje)
    assert ok.status_code == 201 and validade_em(30)
