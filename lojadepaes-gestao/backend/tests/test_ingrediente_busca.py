"""GESTAO-005: buscar antes de cadastrar e sugerir o ingrediente pela entrada.

Comparação de nomes (pura), catálogo de referência (YAML -> banco) e API (busca, sugestão e cadastro),
com Postgres de verdade.
"""

import textwrap

import pytest
from app.cli import main as cli
from app.domain import busca
from app.domain.catalogo import CatalogoInvalido, carregar_catalogo, interpretar, ler_catalogo
from app.models.estoque import CATEGORIAS_INGREDIENTE, CatalogoIngrediente
from sqlalchemy import func, select, text

from tests.conftest import entrar
from tests.test_estoque import ONTEM, Api, farinha

# ---------------------------------------------------------------- comparação de nomes


@pytest.mark.parametrize(
    "a, b",
    [
        ("farinha 00", "Farinha de Trigo Tipo 00"),
        ("Farinha de Trigo Tipo 00", "FARINHA TRIGO 00"),
        ("farinha 00", "FARINHA TRIGO 00"),
        ("Ovos", "ovo"),
        ("Açúcar cristal", "acucar CRISTAL"),
        ("Nozes", "noz"),
        ("Leite integral 1 L", "leite integral"),
        ("Manteiga sem sal 200 g", "Manteiga sem sal"),
        ("Fermento 500g", "fermento"),
    ],
)
def test_nomes_que_se_acham(a, b):
    assert busca.pontuar(a, b) >= busca.LIMIAR_BUSCA
    assert busca.pontuar(b, a) >= busca.LIMIAR_BUSCA


@pytest.mark.parametrize(
    "a, b",
    [
        ("Farinha de trigo tipo 00", "FARINHA TRIGO 00"),
        ("Açúcar CRISTAL", "cristal acucar"),
        ("Ovos", "ovo"),
        ("Leite 1 kg", "leite"),
        ("Sal 1,5 L", "sal"),
    ],
)
def test_acento_caixa_plural_ordem_palavra_vazia_e_peso_nao_contam(a, b):
    assert busca.chave_de_comparacao(a) == busca.chave_de_comparacao(b)


def test_numero_do_produto_conta():
    # "tipo 00" nunca vira "tipo 0" nem "tipo 1"
    assert busca.pontuar("Farinha de trigo tipo 00", "Farinha de trigo tipo 0") == 0
    assert busca.pontuar("Farinha de trigo tipo 1", "Farinha de trigo tipo 00") == 0
    assert busca.chave_de_comparacao("Farinha tipo 1") != busca.chave_de_comparacao(
        "Farinha tipo 0"
    )


def test_peso_no_nome_sai_mas_numero_de_produto_fica():
    assert busca.sem_peso("Fermento Biológico Seco Lievito Caputo 500 g").strip() == (
        "fermento biologico seco lievito caputo"
    )
    assert busca.sem_peso("Farinha Nita 00 25 kg").split() == ["farinha", "nita", "00"]


def test_digitando_vale_palavra_incompleta():
    assert busca.pontuar_digitando("farinha de tri", "Farinha de trigo") >= 85
    assert busca.pontuar_digitando("zzz", "Farinha de trigo") == 0


# ---------------------------------------------------------------- catálogo (YAML -> banco)


def _yaml(corpo: str) -> str:
    return textwrap.dedent(corpo).lstrip("\n")


YAML_OK = _yaml(
    """
    versao: 7
    ingredientes:
      - {nome: "Insumo de teste A", categoria: Outros, unidade: g, apelidos: ["apelido a"]}
      - {nome: "Insumo de teste B", categoria: Outros, unidade: ml, apelidos: []}
    """
)


def test_catalogo_oficial_tem_71_ingredientes_em_12_categorias_e_valida():
    c = ler_catalogo()
    assert c.versao == 2 and len(c.entradas) == 71
    assert len({e.categoria for e in c.entradas}) == 12
    assert {e.unidade for e in c.entradas} <= {"g", "ml", "un"}
    assert {e.categoria for e in c.entradas} <= set(CATEGORIAS_INGREDIENTE)


def test_os_71_itens_estao_carregados_no_banco(db):
    assert db.scalar(select(func.count()).select_from(CatalogoIngrediente)) == 71
    # global: a tabela não tem organização
    assert "organizacao_id" not in CatalogoIngrediente.__table__.c
    assert {v for (v,) in db.execute(select(CatalogoIngrediente.versao).distinct())} == {2}


def test_carga_e_idempotente_rodando_duas_vezes(db):
    primeira = carregar_catalogo(db)
    segunda = carregar_catalogo(db)
    assert (primeira.inseridos, primeira.alterados, primeira.iguais) == (0, 0, 71)  # já carregado
    assert (segunda.inseridos, segunda.alterados, segunda.iguais) == (0, 0, 71)
    assert db.scalar(select(func.count()).select_from(CatalogoIngrediente)) == 71
    db.rollback()


def test_carga_do_zero_insere_depois_nao_altera_nada(db, tmp_path):
    arq = tmp_path / "c.yaml"
    arq.write_text(YAML_OK, encoding="utf-8")
    try:
        um = carregar_catalogo(db, arq)
        dois = carregar_catalogo(db, arq)
        assert (um.inseridos, um.alterados, um.iguais, um.versao) == (2, 0, 0, 7)
        assert (dois.inseridos, dois.alterados, dois.iguais) == (0, 0, 2)
        # muda um apelido: só ele é alterado; o que sumiu do arquivo não é apagado
        so_a = YAML_OK.split('  - {nome: "Insumo de teste B')[0].replace(
            '["apelido a"]', '["apelido a", "outro apelido"]'
        )
        arq.write_text(so_a, encoding="utf-8")
        tres = carregar_catalogo(db, arq)
        assert (tres.inseridos, tres.alterados, tres.iguais) == (0, 1, 0)
        assert tres.fora_do_arquivo == 72  # os 71 oficiais + o B: continuam no banco, nada se apaga
        a = db.scalar(
            select(CatalogoIngrediente).where(CatalogoIngrediente.nome == "Insumo de teste A")
        )
        assert a.apelidos == ["apelido a", "outro apelido"] and a.versao == 7
    finally:
        db.rollback()


@pytest.mark.parametrize(
    "corpo, trecho",
    [
        (
            """
            versao: 1
            ingredientes:
              - {nome: "A", categoria: Farinhas, unidade: g, apelidos: []}
              - {nome: "B", categoria: Doces, unidade: g, apelidos: []}
            """,
            "linha 4: categoria fora da lista",
        ),
        (
            """
            versao: 1
            ingredientes:
              - {nome: "A", categoria: Farinhas, unidade: kg, apelidos: []}
            """,
            "linha 3: unidade fora de g, ml ou un",
        ),
        (
            """
            versao: 1
            ingredientes:
              - {nome: "Farinha de trigo", categoria: Farinhas, unidade: g, apelidos: []}
              - {nome: "farinha  de TRIGO", categoria: Farinhas, unidade: g, apelidos: []}
            """,
            "linha 4: nome repetido",
        ),
        (
            """
            versao: 1
            ingredientes:
              - {nome: "Açúcar refinado", categoria: "Açúcares e mel", unidade: g, apelidos: ["açúcar"]}
              - {nome: "Açúcar cristal", categoria: "Açúcares e mel", unidade: g, apelidos: ["Acucar"]}
            """,
            "linha 4: o termo “Acucar” aponta para dois nomes",
        ),
        (
            """
            versao: 1
            ingredientes:
              - {nome: "A", categoria: Farinhas, unidade: g, apelidos: []
            """,
            "linha",
        ),
        ("ingredientes: []\n", "versao"),
    ],
)
def test_yaml_invalido_falha_com_a_linha_do_erro(corpo, trecho):
    with pytest.raises(CatalogoInvalido) as erro:
        interpretar(_yaml(corpo))
    assert trecho in " | ".join(erro.value.erros)


def test_comando_carregar_catalogo_falha_com_linha_e_nao_grava(tmp_path, capsys, db):
    arq = tmp_path / "ruim.yaml"
    arq.write_text(
        _yaml(
            """
            versao: 2
            ingredientes:
              - {nome: "Novo ingrediente", categoria: Farinhas, unidade: g}
              - {nome: "Outro", categoria: "Não existe", unidade: g}
            """
        ),
        encoding="utf-8",
    )
    assert cli(["carregar-catalogo", "--arquivo", str(arq)]) == 1
    erro = capsys.readouterr().err
    assert "linha 4" in erro and "categoria fora da lista" in erro
    assert db.scalar(select(func.count()).select_from(CatalogoIngrediente)) == 71  # nada entrou


def test_comando_carregar_catalogo_saida_e_idempotente(capsys):
    assert cli(["carregar-catalogo"]) == 0
    saida = capsys.readouterr().out
    assert "versão 2" in saida and "0 inseridos, 0 alterados, 71 iguais" in saida


# ---------------------------------------------------------------- API


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


def novo(api, nome, base="g", **extra):
    return api.post("/ingredientes", {"nome": nome, "unidade_base": base, **extra})


def test_nome_igual_normalizado_e_409_ja_existe_e_devolve_o_existente(api):
    criado = novo(api, "Farinha de trigo tipo 00", categoria="Farinhas").json()
    igual = novo(api, "  FARINHA de  Trigo tipo 00 ", categoria="Farinhas")
    assert igual.status_code == 409
    detalhe = igual.json()["detail"]
    assert detalhe["codigo"] == "ja_existe"
    assert detalhe["existente"]["id"] == criado["id"]
    assert detalhe["existente"]["categoria"] == "Farinhas"
    # mesmo com a confirmação, o nome igual nunca passa
    assert novo(api, "Farinha de trigo tipo 00", confirmado_inexistente=True).status_code == 409


def test_parecido_exige_confirmado_inexistente_e_grava_quem_e_quando(api, db):
    novo(api, "Farinha de trigo tipo 00", categoria="Farinhas")
    sem = novo(api, "Farinha trigo 00", categoria="Farinhas")
    assert sem.status_code == 409
    detalhe = sem.json()["detail"]
    assert detalhe["codigo"] == "ingrediente_parecido"
    assert detalhe["parecidos"][0]["nome"] == "Farinha de trigo tipo 00"

    com = novo(api, "Farinha trigo 00", categoria="Farinhas", confirmado_inexistente=True)
    assert com.status_code == 201, com.text
    linha = db.execute(
        text(
            "SELECT confirmado_inexistente_por, confirmado_inexistente_em FROM ingredientes "
            "WHERE nome = 'Farinha trigo 00'"
        )
    ).one()
    assert (
        linha.confirmado_inexistente_por is not None and linha.confirmado_inexistente_em is not None
    )
    # o primeiro (sem parecido, sem confirmação) não tem quem confirmou
    primeiro = db.execute(
        text(
            "SELECT confirmado_inexistente_por FROM ingredientes WHERE nome = 'Farinha de trigo tipo 00'"
        )
    ).scalar()
    assert primeiro is None


def test_apelido_parecido_tambem_exige_confirmacao(api):
    novo(api, "Farinha de trigo tipo 00", categoria="Farinhas", apelidos=["farinha 00"])
    assert novo(api, "Farinha 00", categoria="Farinhas").status_code == 409


def test_categoria_invalida_e_recusada_e_padrao_e_outros(api):
    assert novo(api, "Algo", categoria="Doces").status_code == 422
    assert novo(api, "Algo").json()["categoria"] == "Outros"


def test_colar_planilha_nunca_cria_ingrediente(api):
    linha = farinha()  # só o NOME do ingrediente, sem escolher um que existe
    nome = linha.pop("ingrediente_nome")
    assert nome
    analise = api.post("/entradas/verificar", {"linhas": [{**linha, "ingrediente_nome": nome}]})
    a = analise.json()["linhas"][0]
    assert a["a_decidir"] and "sem_ingrediente" in [p["codigo"] for p in a["pendencias"]]
    resposta = api.post(
        "/entradas",
        {
            "chave": "colar-1234",
            "data": ONTEM,
            "local_id": api.local_id(),
            "motivo": "contagem",
            "linhas": [{**linha, "ingrediente_nome": nome}],
        },
    )
    assert resposta.status_code == 422
    assert resposta.json()["detail"]["codigo"] == "parecido_nao_decidido"
    assert api.get("/ingredientes").json()["ingredientes"] == []
    assert api.get("/catalogo").json()["itens"] == []


def test_busca_acha_por_nome_e_apelido_com_categoria_saldo_e_itens(api):
    farinha_id = novo(
        api, "Farinha de trigo tipo 00", categoria="Farinhas", apelidos=["farinha 00", "caputo 00"]
    ).json()["id"]
    api.entrada([farinha(ingrediente_nome="Farinha de trigo tipo 00")])
    achados = api.get("/ingredientes/busca", q="caputo 00").json()
    assert [i["id"] for i in achados["da_padaria"]] == [farinha_id]
    f = achados["da_padaria"][0]
    assert f["categoria"] == "Farinhas" and f["saldo"] == 25000 and f["itens"] == 1
    assert f["achado_por"] == "caputo 00"
    por_nome = api.get("/ingredientes/busca", q="farinha de tri").json()
    assert [i["id"] for i in por_nome["da_padaria"]] == [farinha_id]


def test_busca_mostra_o_catalogo_so_do_que_ainda_nao_existe(api):
    antes = api.get("/ingredientes/busca", q="farinha 00").json()
    assert antes["da_padaria"] == []
    assert antes["do_catalogo"][0]["nome"] == "Farinha de trigo tipo 00"
    assert antes["do_catalogo"][0]["categoria"] == "Farinhas"
    novo(api, "Farinha de trigo tipo 00", categoria="Farinhas")
    depois = api.get("/ingredientes/busca", q="farinha 00").json()
    assert [i["nome"] for i in depois["da_padaria"]] == ["Farinha de trigo tipo 00"]
    assert "Farinha de trigo tipo 00" not in [c["nome"] for c in depois["do_catalogo"]]
    # a organização não muda o catálogo
    assert api.get("/ingredientes/busca", q="tipo 00").status_code == 200


def test_busca_vazia_lista_a_padaria_sem_o_catalogo(api):
    novo(api, "Sal fino", categoria="Sal e temperos")
    corpo = api.get("/ingredientes/busca", q="").json()
    assert [i["nome"] for i in corpo["da_padaria"]] == ["Sal fino"] and corpo["do_catalogo"] == []


def test_sugestao_por_item_parecido_diz_qual_item_usa_o_ingrediente(api):
    api.entrada([farinha(item_nome="Farinha Nita 00", marca="Nita", ingrediente_nome="Farinha 00")])
    resp = api.get("/ingredientes/sugestao", item="Farinha Caputo 00 1 kg").json()
    # o nome do ingrediente "Farinha 00" está no nome do item (nível 2) e vem antes do item parecido
    assert resp["sugestoes"][0]["origem"] == "ingrediente"
    assert resp["sugestoes"][0]["ingrediente"]["nome"] == "Farinha 00"


def test_sugestao_item_que_ja_existe_trava_o_ingrediente(api):
    api.entrada([farinha(item_nome="Farinha de trigo", marca="Dona Benta")])
    resp = api.get("/ingredientes/sugestao", item="Farinha de trigo", marca="Dona Benta").json()
    primeira = resp["sugestoes"][0]
    assert primeira["origem"] == "item_existente" and primeira["travado"] is True
    assert primeira["ingrediente"]["nome"] == "Farinha de trigo"


def test_sugestao_por_nome_ou_apelido_do_ingrediente_da_padaria(api):
    novo(api, "Farinha de trigo tipo 00", categoria="Farinhas", apelidos=["tipo 00"])
    resp = api.get("/ingredientes/sugestao", item="Farinha FARINHA Trigo 00 25 kg").json()
    primeira = resp["sugestoes"][0]
    assert (
        primeira["origem"] == "ingrediente"
        and primeira["ingrediente"]["nome"] == "Farinha de trigo tipo 00"
    )


def test_sugestao_do_catalogo_para_fermento_com_marca_e_peso(api):
    resp = api.get(
        "/ingredientes/sugestao", item="Fermento Biológico Seco Lievito Caputo 500 g"
    ).json()
    assert 1 <= len(resp["sugestoes"]) <= 3
    primeira = resp["sugestoes"][0]
    assert primeira["origem"] == "catalogo" and primeira["ingrediente"] is None
    assert primeira["catalogo"]["nome"] == "Fermento biológico seco"
    assert primeira["catalogo"]["categoria"] == "Fermentos"
    assert primeira["motivo"].startswith("O nome do item traz")


def test_sugestao_vem_com_no_maximo_tres_e_sem_item_nao_sugere(api):
    resp = api.get("/ingredientes/sugestao", item="Farinha de trigo").json()
    assert len(resp["sugestoes"]) <= 3
    assert api.get("/ingredientes/sugestao", item="").json()["sugestoes"] == []


def test_busca_e_sugestao_isolam_as_organizacoes(duas_orgs):
    a, b = duas_orgs
    novo(a, "Farinha de trigo tipo 00", categoria="Farinhas", apelidos=["tipo 00"])
    a.entrada(
        [
            farinha(
                item_nome="Farinha Nita 00",
                marca="Nita",
                ingrediente_nome="Farinha de trigo tipo 00",
            )
        ]
    )
    assert [i["nome"] for i in a.get("/ingredientes/busca", q="tipo 00").json()["da_padaria"]] == [
        "Farinha de trigo tipo 00"
    ]
    # B não vê nada de A: nem na busca, nem na sugestão, nem na lista
    vista_por_b = b.get("/ingredientes/busca", q="tipo 00").json()
    assert vista_por_b["da_padaria"] == []
    assert (
        vista_por_b["do_catalogo"][0]["nome"] == "Farinha de trigo tipo 00"
    )  # o catálogo é de todos
    sug = b.get("/ingredientes/sugestao", item="Farinha Caputo 00").json()["sugestoes"]
    assert all(s["ingrediente"] is None for s in sug) and sug[0]["origem"] == "catalogo"
    assert b.get("/ingredientes").json()["ingredientes"] == []
    # e o mesmo nome convive nas duas
    assert novo(b, "Farinha de trigo tipo 00", categoria="Farinhas").status_code == 201


def test_editar_categoria_e_apelidos_e_filtrar_por_categoria(api):
    f = novo(api, "Farinha de trigo", categoria="Farinhas").json()
    novo(api, "Sal fino", categoria="Sal e temperos")
    editado = api.patch(
        f"/ingredientes/{f['id']}",
        {
            "nome": "Farinha de trigo tipo 1",
            "categoria": "Farinhas",
            "apelidos": ["tipo 1", " Tipo 1 ", "", "w300"],
        },
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["nome"] == "Farinha de trigo tipo 1"
    assert editado.json()["apelidos"] == ["tipo 1", "w300"]
    assert api.patch(f"/ingredientes/{f['id']}", {"categoria": "Doces"}).status_code == 422
    lista = api.get("/ingredientes", categoria="Farinhas").json()
    assert [i["nome"] for i in lista["ingredientes"]] == ["Farinha de trigo tipo 1"]
    assert lista["categorias"] == [
        {"nome": "Farinhas", "total": 1},
        {"nome": "Sal e temperos", "total": 1},
    ]
    assert lista["ingredientes"][0]["categoria"] == "Farinhas"
