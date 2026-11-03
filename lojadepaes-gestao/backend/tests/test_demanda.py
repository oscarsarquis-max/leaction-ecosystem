from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg
import pytest
from app.db.session import get_loja_engine
from app.loja_reader.demanda import consultar_demanda, verificar_contrato
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.orm import Session

from tests.conftest import entrar

SP = ZoneInfo("America/Sao_Paulo")


def hoje() -> date:
    return datetime.now(SP).date()


@pytest.fixture()
def reader():
    with Session(get_loja_engine()) as sessao:
        yield sessao
        sessao.rollback()


def _linhas(reader, dia_de: date, dia_ate: date):
    return consultar_demanda(reader, de=dia_de, ate=dia_ate)


def test_so_conta_aceito_em_producao_e_pronto(loja, reader):
    dia = hoje() + timedelta(days=1)
    base = loja.base("TRAD")
    produto, (variante,) = loja.produto("Pão de Teste", base, [("Unidade", 1)])
    for i, status in enumerate(
        ["confirmed", "in_production", "ready", "cancelled", "draft", "submitted", "completed"]
    ):
        pedido = loja.pedido(
            f"T{i}", status, dia, reserva=status in {"confirmed", "in_production", "ready"}
        )
        loja.item(pedido, produto=produto, variante=variante, quantidade=2, unidades=2, base=base)
    linhas = _linhas(reader, dia, dia)
    assert len(linhas) == 1
    assert linhas[0].quantidade == 6 and linhas[0].paes_fisicos == 6  # 3 pedidos × 2
    assert linhas[0].receita_base == "TRAD" and linhas[0].origem == "catalogo"


def test_sem_reserva_de_capacidade_nao_entra(loja, reader):
    dia = hoje() + timedelta(days=1)
    produto, (variante,) = loja.produto("Pão A", None, [("Un", 1)])
    pedido = loja.pedido("S1", "confirmed", dia, reserva=False)
    loja.item(pedido, produto=produto, variante=variante, quantidade=3, unidades=3)
    assert _linhas(reader, dia, dia) == []


def test_exclusao_gerencial_ativa_tira_o_pedido_e_a_revertida_nao(loja, reader):
    dia = hoje() + timedelta(days=2)
    produto, (variante,) = loja.produto("Pão B", None, [("Un", 1)])
    teste = loja.pedido("E1", "confirmed", dia)
    loja.item(teste, produto=produto, variante=variante, quantidade=5, unidades=5)
    loja.excluir(teste)
    revertido = loja.pedido("E2", "confirmed", dia)
    loja.item(revertido, produto=produto, variante=variante, quantidade=1, unidades=1)
    loja.excluir(revertido, revertida=True)
    linhas = _linhas(reader, dia, dia)
    assert [x.quantidade for x in linhas] == [1]


def test_pacote_multiplica_unidades_e_pendencia_nao_vira_zero(loja, reader):
    dia = hoje() + timedelta(days=1)
    produto, (kit, sem_info) = loja.produto("Kit", None, [("Kit com 4", 4), ("Kit surpresa", None)])
    pedido = loja.pedido("P1", "confirmed", dia)
    loja.item(pedido, produto=produto, variante=kit, quantidade=2, unidades=8)
    loja.item(pedido, produto=produto, variante=sem_info, quantidade=3, unidades=None)
    por_variante = {x.variante_ou_forma: x for x in _linhas(reader, dia, dia)}
    assert por_variante["Kit com 4"].paes_fisicos == 8
    assert por_variante["Kit com 4"].linhas_unidades_pendentes == 0
    assert por_variante["Kit surpresa"].linhas_unidades_pendentes == 1
    assert por_variante["Kit surpresa"].quantidade == 3


def test_criador_entra_pela_massa_e_forma(loja, reader):
    dia = hoje() + timedelta(days=3)
    base = loja.base("INTEGRAL")
    massa = loja.massa("Massa Integral", base)
    pedido = loja.pedido("C1", "in_production", dia)
    loja.item(
        pedido, massa=massa, nome_massa="Massa Integral", nome_forma="Bola", quantidade=2, base=base
    )
    (linha,) = _linhas(reader, dia, dia)
    assert linha.origem == "criador"
    assert linha.produto_ou_massa == "Massa Integral" and linha.variante_ou_forma == "Bola"
    assert linha.receita_base == "INTEGRAL" and linha.paes_fisicos == 2


def test_fornada_legada_usa_a_data_local_de_sao_paulo(loja, reader):
    # 01:30 UTC de d+2 ainda é a noite de d+1 em São Paulo (UTC-3)
    dia_local = hoje() + timedelta(days=1)
    disponivel = datetime(dia_local.year, dia_local.month, dia_local.day, tzinfo=UTC) + timedelta(
        days=1, hours=1, minutes=30
    )
    lote = loja.lote("LEGADO-1", disponivel)
    produto, (variante,) = loja.produto("Pão C", None, [("Un", 1)])
    pedido = loja.pedido("L1", "confirmed", None, lote=lote)
    loja.item(pedido, produto=produto, variante=variante, quantidade=4, unidades=4)
    (linha,) = _linhas(reader, dia_local, dia_local)
    assert linha.fornada_data == dia_local and linha.paes_fisicos == 4


def test_janela_de_datas_e_respeitada(loja, reader):
    produto, (variante,) = loja.produto("Pão D", None, [("Un", 1)])
    for deslocamento in (0, 5, 20):
        pedido = loja.pedido(f"J{deslocamento}", "confirmed", hoje() + timedelta(days=deslocamento))
        loja.item(pedido, produto=produto, variante=variante, quantidade=1, unidades=1)
    datas = [x.fornada_data for x in _linhas(reader, hoje(), hoje() + timedelta(days=13))]
    assert datas == [hoje(), hoje() + timedelta(days=5)]


# --- o papel gestao_reader é mesmo só leitura e não enxerga dado pessoal -----------------


@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT customer_name FROM orders",
        "SELECT customer_email FROM orders",
        "SELECT delivery_street FROM orders",
        "SELECT access_token_hash FROM orders",
        "SELECT * FROM orders",
        "SELECT reason FROM managerial_exclusions",
        "SELECT author_ref FROM managerial_exclusions",
        "SELECT * FROM customer_accounts",
        "SELECT pix_qr_code FROM payment_records",
    ],
)
def test_reader_nao_le_colunas_pessoais(reader, consulta):
    with pytest.raises((ProgrammingError, DBAPIError)) as erro:
        reader.execute(text(consulta))
    assert "permission denied" in str(erro.value).lower()


def test_reader_le_o_que_a_demanda_precisa(loja, reader):
    pedido = loja.pedido("R1", "confirmed", hoje())
    assert pedido
    reader.execute(text("SELECT id, public_reference, status FROM orders")).all()
    reader.execute(
        text("SELECT subject_type, subject_id, reversed_at FROM managerial_exclusions")
    ).all()


@pytest.mark.parametrize(
    "escrita",
    [
        "INSERT INTO recipe_bases (id, code, name, is_active) VALUES (gen_random_uuid(), 'X', 'X', true)",
        "UPDATE orders SET status = 'cancelled'",
        "DELETE FROM order_items",
        "TRUNCATE orders CASCADE",
        "CREATE TABLE intruso (id int)",
    ],
)
def test_reader_nao_escreve(reader, escrita):
    with pytest.raises((ProgrammingError, DBAPIError)):
        reader.execute(text(escrita))


def test_reader_nao_enxerga_o_banco_do_gestao():
    url = get_loja_engine().url.set(database="gestao_test")
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(url.render_as_string(hide_password=False).replace("+psycopg", ""))


def test_contrato_com_a_loja_passa(reader):
    verificar_contrato(reader, fuso="America/Sao_Paulo")


# --- API -----------------------------------------------------------------------------------


def test_hoje_agrupa_por_fornada_com_totais(client, loja):
    base = loja.base("TRAD")
    produto, (variante,) = loja.produto("Pão E", base, [("Un", 1)])
    d1, d2 = hoje() + timedelta(days=1), hoje() + timedelta(days=4)
    for ref, dia, qtd in (("H1", d1, 2), ("H2", d1, 3), ("H3", d2, 7)):
        pedido = loja.pedido(ref, "confirmed", dia, nome_cliente="NAO-PODE-APARECER")
        loja.item(pedido, produto=produto, variante=variante, quantidade=qtd, unidades=qtd)
    entrar(client, "oto", "somente_leitura")
    resposta = client.get("/api/v1/hoje")
    corpo = resposta.json()
    assert resposta.status_code == 200
    assert (
        "NAO-PODE-APARECER" not in resposta.text
        and "sintetico@example.invalid" not in resposta.text
    )
    assert corpo["compatibilidade"]["ok"] is True
    assert corpo["compatibilidade"]["versao_loja"] == "e7b3c9a41d06"
    assert corpo["compatibilidade"]["versao_conhecida"] is True
    assert [f["data"] for f in corpo["fornadas"]] == [d1.isoformat(), d2.isoformat()]
    assert [f["paes_fisicos"] for f in corpo["fornadas"]] == [5, 7]
    assert corpo["total_paes_fisicos"] == 12
    assert corpo["fornadas"][0]["itens"][0]["produto_ou_massa"] == "Pão E"


def test_hoje_nao_grava_nada_na_loja(client, loja):
    entrar(client, "pia", "dono")
    antes = loja.conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    assert client.get("/api/v1/hoje").status_code == 200
    assert loja.conn.execute("SELECT count(*) FROM orders").fetchone()[0] == antes


def test_hoje_respeita_o_horizonte(client, loja):
    produto, (variante,) = loja.produto("Pão F", None, [("Un", 1)])
    pedido = loja.pedido("Z1", "confirmed", hoje() + timedelta(days=10))
    loja.item(pedido, produto=produto, variante=variante, quantidade=1, unidades=1)
    entrar(client, "quim", "dono")
    assert client.get("/api/v1/hoje?dias=7").json()["fornadas"] == []
    assert len(client.get("/api/v1/hoje?dias=14").json()["fornadas"]) == 1


def test_hoje_avisa_e_nao_inventa_numero_quando_a_loja_nao_responde(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def falha(*_a, **_k):
        raise OperationalError("SELECT", {}, Exception("loja fora do ar"))

    monkeypatch.setattr("app.api.v1.hoje.consultar_demanda", falha)
    entrar(client, "rui", "dono")
    corpo = client.get("/api/v1/hoje").json()
    assert corpo["compatibilidade"]["ok"] is False
    assert corpo["fornadas"] == [] and corpo["total_paes_fisicos"] == 0
    assert "loja fora do ar" not in str(corpo)  # nada de detalhe técnico para o usuário


def test_hoje_avisa_quando_a_versao_da_loja_mudou(client, loja):
    loja.conn.execute("UPDATE alembic_version SET version_num = 'nova000000000'")
    try:
        entrar(client, "sol", "dono")
        corpo = client.get("/api/v1/hoje").json()
        assert corpo["compatibilidade"]["ok"] is True
        assert corpo["compatibilidade"]["versao_conhecida"] is False
        assert corpo["compatibilidade"]["mensagem"]
    finally:
        loja.conn.execute("UPDATE alembic_version SET version_num = 'e7b3c9a41d06'")


def test_saude_e_prontidao(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    pronto = client.get("/api/v1/ready")
    assert pronto.status_code == 200
    assert pronto.json() == {
        "status": "ok",
        "gestao_db": True,
        "sessao": True,
        "loja_leitura": True,
    }
