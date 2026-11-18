# ruff: noqa: F811
"""GESTAO-006: o custo vem do valor pago; corrigir custo; trocar ingrediente; migração que preserva o legado."""

import os
import re
import subprocess
import sys
import uuid
from decimal import Decimal

import psycopg
import pytest
from psycopg import sql

from tests.conftest import ADMIN_URL, APP_PW, HOST_PORT, ROOT, _admin, entrar
from tests.test_estoque import Api, farinha, validade_em

# o cliente e o `api` vêm do conftest e de test_estoque


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def por_kg(custo_base: float) -> float:
    return round(custo_base * 1000, 2)


def pacote(**mudar):
    """Um pacote de 500 g de fermento, vendido em embalagem."""
    base = {
        "item_nome": "Fermento biológico seco 500 g",
        "marca": "Fleischmann",
        "unidade_controle": "embalagem",
        "conteudo_embalagem": 500,
        "ingrediente_nome": "Fermento biológico seco",
        "ingrediente_unidade_base": "g",
        "quantidade": 1,
        "unidade": "emb",
        "validade": validade_em(200),
    }
    base.update(mudar)
    return base


def lote_do_ingrediente(api, ingrediente_id):
    detalhe = api.get(f"/ingredientes/{ingrediente_id}").json()
    return detalhe, detalhe["lotes_detalhe"][0]


# ---------------------------------------------------------------- o valor pago vira custo por unidade


def test_meio_quilo_com_22_99_pagos_da_45_98_por_kg(api):
    """0,5 kg e R$ 22,99 pagos: R$ 45,98 por kg (e não R$ 22,99 por kg, como era)."""
    linha = farinha(item_nome="Fermento seco granel", quantidade=0.5, custo=None, valor_pago=22.99)
    analise = api.verificar([linha]).json()["linhas"][0]
    assert not analise["incompleta"]
    assert analise["modo_custo"] == "valor_pago"
    assert analise["valor_total"] == 22.99
    assert por_kg(analise["custo_unidade_base"]) == 45.98
    assert analise["custo_embalagem"] is None  # item de massa

    resposta = api.entrada([linha])
    assert resposta.status_code == 201, resposta.text
    gravada = resposta.json()["linhas"][0]
    assert gravada["valor_pago"] == 22.99 and gravada["modo_custo"] == "valor_pago"
    assert gravada["custo"] is None and gravada["custo_por"] is None
    assert gravada["valor_total"] == 22.99
    assert resposta.json()["valor"] == 22.99
    detalhe, lote = lote_do_ingrediente(api, gravada["ingrediente_id"])
    assert por_kg(lote["custo_unidade_base"]) == 45.98
    assert detalhe["saldo"] == 500
    # o lote guarda R$/g exatos: 22,99 ÷ 500 g
    assert Decimal(str(lote["custo_unidade_base"])) == Decimal("0.04598")


def test_uma_embalagem_de_500_g_com_22_99_pagos_da_22_99_por_emb_e_45_98_por_kg(api):
    linha = pacote(valor_pago=22.99)
    analise = api.verificar([linha]).json()["linhas"][0]
    assert analise["custo_embalagem"] == 22.99
    assert por_kg(analise["custo_unidade_base"]) == 45.98
    assert analise["valor_total"] == 22.99

    resposta = api.entrada([linha])
    assert resposta.status_code == 201, resposta.text
    g = resposta.json()["linhas"][0]
    assert g["quantidade_base"] == 500 and g["valor_total"] == 22.99
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    assert por_kg(lote["custo_unidade_base"]) == 45.98
    assert lote["valor_do_lote"] == 22.99 and lote["quantidade_comprada_base"] == 500


def test_tres_embalagens_dividem_o_total_pago_pela_quantidade_total(api):
    """O valor pago é o TOTAL da linha: R$ 60 por 3 embalagens de 500 g = R$ 20 por embalagem."""
    analise = api.verificar([pacote(quantidade=3, valor_pago=60)]).json()["linhas"][0]
    assert analise["custo_embalagem"] == pytest.approx(20.0)
    assert por_kg(analise["custo_unidade_base"]) == 40.0
    assert analise["valor_total"] == 60.0


def test_valor_pago_nao_arredonda_antes_de_gravar(api):
    """R$ 10 por 3 kg: 0,003333... por g; o banco guarda 8 casas, a tela mostra 2."""
    resposta = api.entrada([farinha(item_nome="Sal grosso 3 kg", quantidade=3, custo=None, valor_pago=10)])
    g = resposta.json()["linhas"][0]
    assert g["valor_total"] == 10.0  # o valor pago, nunca quantidade x custo arredondado
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    assert lote["custo_unidade_base"] == pytest.approx(10 / 3000, abs=1e-8)
    assert lote["valor_do_lote"] == 10.0


def test_modo_preco_por_unidade_continua_funcionando(api):
    """O modo antigo: R$ 4,50 por kg, 25 kg."""
    linha = farinha()  # custo=4.5 (R$ por kg)
    analise = api.verificar([linha]).json()["linhas"][0]
    assert analise["modo_custo"] == "preco_unidade"
    assert analise["valor_total"] == 112.5
    assert por_kg(analise["custo_unidade_base"]) == 4.5
    g = api.entrada([linha]).json()["linhas"][0]
    assert g["custo"] == 4.5 and g["custo_por"] == "kg"
    assert g["valor_pago"] is None and g["modo_custo"] == "preco_unidade"
    assert g["valor_total"] == 112.5
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    assert por_kg(lote["custo_unidade_base"]) == 4.5


def test_modo_preco_por_unidade_em_embalagem(api):
    analise = api.verificar([pacote(quantidade=2, custo=11.5)]).json()["linhas"][0]
    assert analise["modo_custo"] == "preco_unidade"
    assert analise["custo_embalagem"] == 11.5 and analise["valor_total"] == 23.0
    assert por_kg(analise["custo_unidade_base"]) == 23.0


def test_nao_sei_deixa_o_custo_desconhecido(api):
    linha = farinha(custo=None)
    analise = api.verificar([linha]).json()["linhas"][0]
    assert analise["modo_custo"] is None and analise["custo_unidade_base"] is None
    assert analise["valor_total"] is None
    g = api.entrada([linha]).json()["linhas"][0]
    assert g["valor_pago"] is None and g["modo_custo"] is None and g["valor_total"] is None
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    assert lote["custo_unidade_base"] is None and lote["valor_do_lote"] is None


def test_valor_pago_e_preco_juntos_ou_negativo_sao_recusados(api):
    dupla = api.verificar([farinha(valor_pago=10)]).json()["linhas"][0]  # custo=4.5 tambem
    assert "custo_duplo" in [p["codigo"] for p in dupla["pendencias"] if p["bloqueia"]]
    assert api.entrada([farinha(valor_pago=10)]).status_code == 422
    negativo = api.verificar([farinha(custo=None, valor_pago=-1)]).json()["linhas"][0]
    assert "custo_invalido" in [p["codigo"] for p in negativo["pendencias"] if p["bloqueia"]]


def test_total_da_entrada_e_a_soma_dos_valores_pagos(api):
    resposta = api.entrada(
        [
            farinha(item_nome="Farinha A", quantidade=1, custo=None, valor_pago=10.10),
            farinha(item_nome="Farinha B", quantidade=2, custo=None, valor_pago=20.25),
        ]
    )
    assert resposta.json()["valor"] == pytest.approx(30.35)


# ---------------------------------------------------------------- corrigir custo


def test_corrigir_custo_grava_o_historico_e_nao_muda_o_saldo(api):
    """O caso do Oscar: pacote de 500 g, R$ 22,99, digitado como R$ 22,99 por kg."""
    entrada = api.entrada([pacote(quantidade=0.5, unidade="emb", conteudo_embalagem=1000, custo=22.99)])
    # (item "emb" de 1000 g, meia embalagem = 500 g, no modo antigo: R$ 22,99 por embalagem)
    assert entrada.status_code == 201, entrada.text
    g = entrada.json()["linhas"][0]
    ing_id = g["ingrediente_id"]
    detalhe, lote = lote_do_ingrediente(api, ing_id)
    saldo_antes, movs_antes = detalhe["saldo"], len(detalhe["movimentos"])
    assert por_kg(lote["custo_unidade_base"]) == 22.99
    assert lote["valor_do_lote"] == 11.5  # o que o custo antigo dizia ter sido pago

    corrigido = api.post(
        f"/lotes/{lote['id']}/custo", {"valor_pago": 22.99, "motivo": "Digitei por kg, era o pacote"}
    )
    assert corrigido.status_code == 200, corrigido.text
    novo_lote = corrigido.json()
    assert por_kg(novo_lote["custo_unidade_base"]) == 45.98
    assert novo_lote["valor_pago_atual"] == 22.99
    assert novo_lote["historico"][0]["motivo"] == "Digitei por kg, era o pacote"

    depois = api.get(f"/ingredientes/{ing_id}").json()
    assert depois["saldo"] == saldo_antes  # custo não é saldo
    assert len(depois["movimentos"]) == movs_antes  # e não gera movimento
    assert depois["lotes_detalhe"][0]["saldo"] == lote["saldo"]
    assert depois["lotes_detalhe"][0]["quantidade_comprada_base"] == 500
    h = depois["correcoes_custo"][0]
    assert h["quem"] == "Pessoa" and h["lote"] == lote["codigo"] and h["modo"] == "valor_pago"
    assert por_kg(h["custo_antes"]) == 22.99 and por_kg(h["custo_depois"]) == 45.98
    assert h["valor_pago"] == 22.99 and h["motivo"].startswith("Digitei")
    # a entrada passa a mostrar o valor vigente (o digitado fica guardado)
    linha = api.get(f"/entradas/{entrada.json()['id']}").json()["linhas"][0]
    assert linha["valor_total"] == 22.99 and por_kg(linha["custo_unidade_base"]) == 45.98
    assert linha["custo"] == 22.99 and linha["modo_custo"] == "preco_unidade"


def test_corrigir_custo_pelo_preco_por_unidade_e_dados_do_lote(api):
    g = api.entrada([farinha(custo=None)]).json()["linhas"][0]  # custo desconhecido
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    antes = api.get(f"/lotes/{lote['id']}/custo").json()
    assert antes["custo_unidade_base"] is None and antes["quantidade_comprada_base"] == 25000
    assert antes["historico"] == []
    r = api.post(f"/lotes/{lote['id']}/custo", {"preco_unidade": 5, "motivo": "Achei a nota"})
    assert r.status_code == 200, r.text
    assert por_kg(r.json()["custo_unidade_base"]) == 5.0 and r.json()["valor_pago_atual"] == 125.0
    assert r.json()["historico"][0]["custo_antes"] is None


def test_corrigir_custo_exige_motivo_valor_valido_e_diferenca(api):
    g = api.entrada([farinha()]).json()["linhas"][0]
    _, lote = lote_do_ingrediente(api, g["ingrediente_id"])
    url = f"/lotes/{lote['id']}/custo"
    assert api.post(url, {"valor_pago": 100, "motivo": ""}).status_code == 422
    assert api.post(url, {"valor_pago": 100, "motivo": "ok"}).status_code == 422  # curto demais
    assert api.post(url, {"motivo": "sem valor nenhum"}).status_code == 422
    assert api.post(url, {"valor_pago": 1, "preco_unidade": 1, "motivo": "os dois"}).status_code == 422
    assert api.post(url, {"valor_pago": -5, "motivo": "negativo"}).status_code == 422
    igual = api.post(url, {"valor_pago": 112.5, "motivo": "mesmo valor"})
    assert igual.status_code == 422 and igual.json()["detail"]["codigo"] == "sem_diferenca"
    assert api.get(f"/lotes/{uuid.uuid4()}/custo").status_code == 404
    assert api.get(f"/ingredientes/{g['ingrediente_id']}").json()["correcoes_custo"] == []


def test_corrigir_custo_respeita_papel_e_organizacao(client):
    from app.main import create_app
    from fastapi.testclient import TestClient

    dono = Api(client, entrar(client, "dona", "dono", org="org-a"))
    g = dono.entrada([farinha()]).json()["linhas"][0]
    _, lote = lote_do_ingrediente(dono, g["ingrediente_id"])
    with TestClient(create_app(), base_url="http://testserver") as c2:
        leitor = Api(c2, entrar(c2, "leitor", "somente_leitura", org="org-a"))
        assert leitor.post(f"/lotes/{lote['id']}/custo", {"valor_pago": 1, "motivo": "não pode"}).status_code == 403
        assert leitor.get(f"/lotes/{lote['id']}/custo").status_code == 200
    with TestClient(create_app(), base_url="http://testserver") as c3:
        de_fora = Api(c3, entrar(c3, "fora", "dono", org="org-b", fonte_loja=False))
        assert de_fora.get(f"/lotes/{lote['id']}/custo").status_code == 404
        assert de_fora.post(f"/lotes/{lote['id']}/custo", {"valor_pago": 1, "motivo": "outra casa"}).status_code == 404


# ---------------------------------------------------------------- trocar ingrediente


def _item_do_ingrediente(api, ingrediente_id, nome_item):
    detalhe = api.get(f"/ingredientes/{ingrediente_id}").json()
    return next(i for i in detalhe["itens_detalhe"] if i["nome"] == nome_item)


def test_trocar_ingrediente_leva_os_lotes_ajusta_os_dois_saldos_e_guarda_historico(api):
    errado = api.ingrediente("Farinha de trigo especial", "g", "Farinhas")
    certo = api.ingrediente("Farinha de trigo sarraceno", "g", "Farinhas")
    g = api.entrada(
        [
            farinha(
                item_nome="Trigo Sarraceno",
                marca="Granel",
                ingrediente_id=errado,
                ingrediente_nome=None,
                quantidade=2,
                custo=None,
                valor_pago=18.5,
            )
        ]
    ).json()["linhas"][0]
    assert api.saldo(errado) == 2000 and api.saldo(certo) == 0
    lotes_antes = api.get(f"/ingredientes/{errado}").json()["lotes_detalhe"]
    item = _item_do_ingrediente(api, errado, "Trigo Sarraceno")

    r = api.post(
        f"/itens/{item['id']}/trocar-ingrediente",
        {"ingrediente_id": certo, "motivo": "Sarraceno não é trigo"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == certo  # devolve o ingrediente que passou a ter o item

    # os saldos dos dois se ajustam
    assert api.saldo(errado) == 0 and api.saldo(certo) == 2000
    novo_ing = api.get(f"/ingredientes/{certo}").json()
    velho_ing = api.get(f"/ingredientes/{errado}").json()
    assert [i["nome"] for i in novo_ing["itens_detalhe"]] == ["Trigo Sarraceno"]
    assert velho_ing["itens_detalhe"] == []
    # os lotes foram junto, inteiros: mesmo id, saldo, custo e valor
    lote = novo_ing["lotes_detalhe"][0]
    assert lote["id"] == lotes_antes[0]["id"] and lote["saldo"] == 2000
    assert lote["custo_unidade_base"] == lotes_antes[0]["custo_unidade_base"]
    assert lote["valor_do_lote"] == 18.5
    assert velho_ing["lotes_detalhe"] == []
    # o histórico aparece nos DOIS ingredientes, como movimento de junção (quantidade 0) de troca
    for detalhe, de, para in ((velho_ing, "Farinha de trigo especial", "Farinha de trigo sarraceno"),):
        m = next(m for m in detalhe["movimentos"] if m["tipo"] == "juncao")
        assert m["troca"] is True and m["de"] == de and m["para"] == para
        assert m["quantidade_base"] == 0 and "Sarraceno não é trigo" in m["motivo"]
    m_novo = next(m for m in novo_ing["movimentos"] if m["tipo"] == "juncao")
    assert m_novo["troca"] is True and m_novo["item"] == "Trigo Sarraceno"
    # a entrada original continua apontando para o mesmo lote e item
    assert g["lote_id"] == lote["id"]


def test_trocar_ingrediente_grava_quem_quando_e_porque(api, db):
    from sqlalchemy import text

    errado = api.ingrediente("Farinha de trigo especial", "g", "Farinhas")
    certo = api.ingrediente("Farinha de trigo sarraceno", "g", "Farinhas")
    api.entrada([farinha(item_nome="Trigo Sarraceno", ingrediente_id=errado, ingrediente_nome=None)])
    item = _item_do_ingrediente(api, errado, "Trigo Sarraceno")
    api.post(f"/itens/{item['id']}/trocar-ingrediente", {"ingrediente_id": certo, "motivo": "Sarraceno não é trigo"})
    linha = db.execute(
        text(
            "SELECT t.motivo, t.usuario_id IS NOT NULL, t.criado_em IS NOT NULL, "
            "t.de_ingrediente_id = :e, t.para_ingrediente_id = :c, t.movimento_id IS NOT NULL "
            "FROM trocas_ingrediente t"
        ),
        {"e": errado, "c": certo},
    ).one()
    assert tuple(linha) == ("Sarraceno não é trigo", True, True, True, True, True)


def test_trocar_ingrediente_recusa_unidade_diferente_mesmo_ou_inativo_sem_motivo(api):
    errado = api.ingrediente("Farinha de trigo especial", "g", "Farinhas")
    leite = api.ingrediente("Leite integral", "ml", "Laticínios")
    certo = api.ingrediente("Farinha de trigo sarraceno", "g", "Farinhas")
    api.entrada([farinha(item_nome="Trigo Sarraceno", ingrediente_id=errado, ingrediente_nome=None)])
    item = _item_do_ingrediente(api, errado, "Trigo Sarraceno")
    url = f"/itens/{item['id']}/trocar-ingrediente"
    massa_volume = api.post(url, {"ingrediente_id": leite, "motivo": "teste de unidade"})
    assert massa_volume.status_code == 422
    assert massa_volume.json()["detail"]["codigo"] == "unidade_incompativel"
    mesmo = api.post(url, {"ingrediente_id": errado, "motivo": "mesmo de novo"})
    assert mesmo.json()["detail"]["codigo"] == "mesmo_ingrediente"
    assert api.post(url, {"ingrediente_id": certo, "motivo": ""}).status_code == 422
    assert api.post(url, {"ingrediente_id": str(uuid.uuid4()), "motivo": "não existe"}).status_code == 404
    assert api.post(f"/itens/{uuid.uuid4()}/trocar-ingrediente", {"ingrediente_id": certo, "motivo": "sem item"}).status_code == 404
    # inativo (juntado em outro): não serve
    outro = api.ingrediente("Farinha sarraceno antiga", "g", "Farinhas")
    api.post("/ingredientes/juntar", {"mantem_id": certo, "remove_id": outro})
    assert api.post(url, {"ingrediente_id": outro, "motivo": "inativo"}).json()["detail"]["codigo"] == "ingrediente_inativo"
    # nada mudou
    assert api.saldo(errado) == 25000


def test_trocar_ingrediente_respeita_papel(client):
    from app.main import create_app
    from fastapi.testclient import TestClient

    dono = Api(client, entrar(client, "dona", "dono", org="org-a"))
    errado = dono.ingrediente("Farinha de trigo especial", "g", "Farinhas")
    certo = dono.ingrediente("Farinha de trigo sarraceno", "g", "Farinhas")
    dono.entrada([farinha(item_nome="Trigo Sarraceno", ingrediente_id=errado, ingrediente_nome=None)])
    item = _item_do_ingrediente(dono, errado, "Trigo Sarraceno")
    with TestClient(create_app(), base_url="http://testserver") as c2:
        leitor = Api(c2, entrar(c2, "leitor", "somente_leitura", org="org-a"))
        r = leitor.post(f"/itens/{item['id']}/trocar-ingrediente", {"ingrediente_id": certo, "motivo": "não pode"})
        assert r.status_code == 403
    assert dono.saldo(errado) == 25000


# ---------------------------------------------------------------- a migração preserva o legado


def _alembic(banco: str, destino: str, *, baixar=False) -> None:
    url = f"postgresql+psycopg://gestao_app:{APP_PW}@{HOST_PORT}/{banco}"
    env = {**os.environ, "GESTAO_DATABASE_URL": url}
    comando = "downgrade" if baixar else "upgrade"
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", comando, destino],
        cwd=ROOT / "database",
        env=env,
        check=True,
        capture_output=True,
    )


CONSULTA_LEGADA = """
SELECT l.codigo, i.nome AS item, g.nome AS ingrediente, g.unidade_base,
       (SELECT SUM(m.quantidade_base) FROM movimentos m WHERE m.lote_id = l.id) AS saldo,
       l.custo_unidade_base,
       CASE WHEN g.unidade_base IN ('g','ml') THEN l.custo_unidade_base * 1000
            ELSE l.custo_unidade_base END AS custo_kg_l_un,
       el.quantidade, el.unidade, el.custo_informado, el.custo_por, el.valor_total
FROM lotes l
JOIN itens_estoque i ON i.id = l.item_id
JOIN ingredientes g ON g.id = i.ingrediente_id
JOIN entrada_linhas el ON el.lote_id = l.id
ORDER BY l.codigo
"""


def test_migracao_0004_preserva_custos_e_dados_de_lotes_antigos():
    """Dados no formato atual (0003): depois da 0004 os mesmos valores, byte a byte; e volta."""
    banco = "gestao_migracao_test"
    with _admin() as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(banco)))
        conn.execute(sql.SQL("CREATE DATABASE {} OWNER gestao_app").format(sql.Identifier(banco)))
    try:
        _alembic(banco, "0003_ingrediente_catalogo")
        url = re.sub(r"/[^/]*$", f"/{banco}", ADMIN_URL)
        org, user, local = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        with psycopg.connect(url, autocommit=True) as c:
            c.execute(
                "INSERT INTO organizacoes (id, nome, nome_curto, cnpj) VALUES (%s,'Org','org','12345678000195')",
                (org,),
            )
            c.execute(
                "INSERT INTO usuarios (id, usuario, nome, senha_hash) VALUES (%s,'u','U','x')", (user,)
            )
            c.execute(
                "INSERT INTO locais (id, organizacao_id, nome, nome_normalizado, padrao) VALUES (%s,%s,'D','d',true)",
                (local, org),
            )
            ingredientes = {}
            for nome, base in (("Fermento", "g"), ("Leite", "ml"), ("Ovos", "un")):
                ingredientes[nome] = uuid.uuid4()
                c.execute(
                    "INSERT INTO ingredientes (id, organizacao_id, nome, nome_normalizado, unidade_base) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (ingredientes[nome], org, nome, nome.lower(), base),
                )
            # (item, ingrediente, controle, conteudo, qtd, unidade, qtd_base, custo digitado, por, custo_base, valor)
            legado = [
                ("Fermento 500 g", "Fermento", "embalagem", 500, 0.5, "emb", 250, 22.99, "emb", "0.04598000", 11.50),
                ("Leite 1 L", "Leite", "volume", None, 12, "l", 12000, 4.89, "l", "0.00489000", 58.68),
                ("Ovos", "Ovos", "embalagem", 30, 2, "emb", 60, 18, "emb", "0.60000000", 36.00),
                ("Sem custo", "Fermento", "massa", None, 3, "kg", 3000, None, None, None, None),
            ]
            for n, (item, ing, controle, conteudo, qtd, un, qbase, custo, por, cbase, valor) in enumerate(legado):
                item_id, lote_id, ent_id, mov_id = (uuid.uuid4() for _ in range(4))
                c.execute(
                    "INSERT INTO itens_estoque (id, organizacao_id, ingrediente_id, nome, nome_normalizado, "
                    "unidade_controle, conteudo_embalagem) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (item_id, org, ingredientes[ing], item, item.lower(), controle, conteudo),
                )
                c.execute(
                    "INSERT INTO lotes (id, organizacao_id, item_id, local_id, codigo, sem_validade, "
                    "custo_unidade_base) VALUES (%s,%s,%s,%s,%s,true,%s)",
                    (lote_id, org, item_id, local, f"L{n}", cbase),
                )
                c.execute(
                    "INSERT INTO entradas (id, organizacao_id, data, local_id, tipo, motivo, lancada_por, "
                    "chave_idempotencia) VALUES (%s,%s,'2026-11-01',%s,'sem_nota','compra_sem_nota',%s,%s)",
                    (ent_id, org, local, user, f"chave-{n}-xxxx"),
                )
                c.execute(
                    "INSERT INTO movimentos (id, organizacao_id, tipo, item_id, lote_id, quantidade_base, "
                    "entrada_id, usuario_id) VALUES (%s,%s,'entrada',%s,%s,%s,%s,%s)",
                    (mov_id, org, item_id, lote_id, qbase, ent_id, user),
                )
                c.execute(
                    "INSERT INTO entrada_linhas (id, organizacao_id, entrada_id, posicao, item_id, lote_id, "
                    "movimento_id, quantidade, unidade, quantidade_base, custo_informado, custo_por, valor_total) "
                    "VALUES (%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4(), org, ent_id, item_id, lote_id, mov_id, qtd, un, qbase, custo, por, valor),
                )
            antes = c.execute(CONSULTA_LEGADA).fetchall()
        assert len(antes) == 4

        _alembic(banco, "head")

        with psycopg.connect(url, autocommit=True) as c:
            depois = c.execute(CONSULTA_LEGADA).fetchall()
            assert depois == antes  # idêntico: lote · item · ingrediente · quantidade · custo
            # exemplo: o "22,99 por kg" que o Oscar digitou continua valendo R$ 22,99 por kg (0,0229... não)
            fermento = next(r for r in depois if r[1] == "Fermento 500 g")
            assert fermento[5] == Decimal("0.04598000") and fermento[6] == Decimal("45.98000000")
            # as colunas novas nascem vazias nas linhas antigas
            assert c.execute(
                "SELECT count(*) FROM entrada_linhas WHERE valor_pago IS NOT NULL OR modo_custo IS NOT NULL"
            ).fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM correcoes_custo").fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM trocas_ingrediente").fetchone()[0] == 0

        _alembic(banco, "0003_ingrediente_catalogo", baixar=True)  # e volta sem perder nada
        with psycopg.connect(url, autocommit=True) as c:
            assert c.execute(CONSULTA_LEGADA).fetchall() == antes
    finally:
        with _admin() as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(banco)))


def test_o_banco_de_teste_novo_ja_tem_as_tabelas_da_006(db):
    from sqlalchemy import text

    tabelas = {t for (t,) in db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
    assert {"correcoes_custo", "trocas_ingrediente"} <= tabelas
    colunas = {
        c
        for (c,) in db.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='entrada_linhas'")
        )
    }
    assert {"valor_pago", "modo_custo", "custo_informado", "custo_por", "valor_total"} <= colunas
