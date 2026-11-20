"""GESTAO-021: custos fixos por kg, margem/markup e leitura do preço da Loja."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_engine
from app.domain import custos_preco
from app.main import create_app
from tests.conftest import entrar
from tests.test_estoque import Api, validade_em
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro", "dono"))


def _farinha_com_custo(api, custo_kg=12):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    resp = api.entrada(
        [
            {
                "item_nome": "Farinha teste custo",
                "marca": "Casa",
                "unidade_controle": "massa",
                "ingrediente_nome": "Farinha de trigo",
                "quantidade": 1,
                "unidade": "kg",
                "validade": validade_em(120),
                "custo": custo_kg,
            }
        ]
    )
    assert resp.status_code == 201, resp.text
    return farinha


def _perdas_zero(produto_id: str) -> None:
    """A comanda exige processo e cocção; 0% deixa a massa crua = peso final (exemplo do Oscar)."""
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE receitas SET
                  perda_processo_pct = 0,
                  perda_processo_origem = 'manual',
                  perda_processo_motivo = 'teste custos',
                  perda_coccao_pct = 0,
                  perda_coccao_origem = 'manual',
                  perda_coccao_motivo = 'teste custos'
                WHERE produto_id = :id
                """
            ),
            {"id": produto_id},
        )


def _publicar_pao(api, nome, farinha_id, peso_g=1000):
    pao = _produto(api, nome, confirmado_inexistente=True)
    salvo = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha_id, "quantidade": peso_g, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        perda_percentual=0,
        peso_unidade_g=peso_g,
        formato="livre",
    )
    assert salvo.status_code == 200, salvo.text
    publicada = api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True})
    assert publicada.status_code == 200, publicada.text
    _perdas_zero(pao["id"])
    return pao


def test_exemplo_oscar_rateio_mc_e_sugeridos(api):
    farinha = _farinha_com_custo(api, 12)
    pao = _publicar_pao(api, "Pão exemplo Oscar", farinha, 1000)

    assert api.post("/custos/fixos", {"nome": "Aluguel", "valor_mensal": 3000}).status_code == 200
    params = api.c.put(
        "/api/v1/custos/parametros",
        json={"massa_mensal_kg": 600, "regra": {"tipo": "margem", "valor": 60}},
        headers=api.h,
    )
    assert params.status_code == 200, params.text
    corpo = params.json()
    assert corpo["parametros"]["custo_fixo_total"] == pytest.approx(3000)
    assert corpo["parametros"]["custo_fixo_por_kg"] == pytest.approx(5)

    linha = next(p for p in corpo["produtos"] if p["produto_id"] == pao["id"])
    assert linha["massa_g"] == pytest.approx(1000)
    assert linha["custo_variavel"] == pytest.approx(12)
    assert linha["rateio"] == pytest.approx(5)
    assert linha["custo_total"] == pytest.approx(17)
    assert linha["preco_sugerido"] == pytest.approx(30)

    markup = api.c.put(
        "/api/v1/custos/parametros",
        json={"massa_mensal_kg": 600, "regra": {"tipo": "markup", "valor": 3}},
        headers=api.h,
    )
    assert markup.status_code == 200, markup.text
    linha = next(p for p in markup.json()["produtos"] if p["produto_id"] == pao["id"])
    assert linha["preco_sugerido"] == pytest.approx(51)


def test_precedencia_familia_produto_e_null(api):
    farinha = _farinha_com_custo(api)
    familia = api.post("/familias", {"nome": "Pães de teste"})
    assert familia.status_code == 201, familia.text
    familia_id = familia.json()["id"]
    produto = _produto(
        api,
        "Pão com família",
        familia_id=familia_id,
        confirmado_inexistente=True,
    )
    assert _put(
        api,
        produto["id"],
        linhas=[{"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        perda_percentual=0,
        peso_unidade_g=500,
        formato="livre",
    ).status_code == 200
    assert api.post(f"/receitas/{produto['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200

    assert api.c.put(
        "/api/v1/custos/parametros",
        json={"massa_mensal_kg": 100, "regra": {"tipo": "markup", "valor": 2}},
        headers=api.h,
    ).status_code == 200
    assert api.c.put(
        f"/api/v1/custos/familias/{familia_id}/regra",
        json={"regra": {"tipo": "markup", "valor": 3}},
        headers=api.h,
    ).status_code == 200
    linha = next(p for p in api.get("/custos").json()["produtos"] if p["produto_id"] == produto["id"])
    assert linha["regra_origem"] == "familia"
    assert linha["regra"]["valor"] == pytest.approx(3)

    assert api.c.put(
        f"/api/v1/custos/produtos/{produto['id']}/regra",
        json={"regra": {"tipo": "margem", "valor": 40}},
        headers=api.h,
    ).status_code == 200
    linha = next(p for p in api.get("/custos").json()["produtos"] if p["produto_id"] == produto["id"])
    assert linha["regra_origem"] == "produto"

    assert api.c.put(
        f"/api/v1/custos/produtos/{produto['id']}/regra",
        json={"regra": None},
        headers=api.h,
    ).status_code == 200
    linha = next(p for p in api.get("/custos").json()["produtos"] if p["produto_id"] == produto["id"])
    assert linha["regra_origem"] == "familia"
    assert linha["regra_propria"] is None


def test_validacoes_422(api):
    assert (
        api.c.put(
            "/api/v1/custos/parametros",
            json={"massa_mensal_kg": 0, "regra": None},
            headers=api.h,
        ).status_code
        == 422
    )
    assert (
        api.c.put(
            "/api/v1/custos/parametros",
            json={"massa_mensal_kg": 10, "regra": {"tipo": "margem", "valor": 100}},
            headers=api.h,
        ).status_code
        == 422
    )
    assert (
        api.c.put(
            "/api/v1/custos/parametros",
            json={"massa_mensal_kg": 10, "regra": {"tipo": "markup", "valor": 0}},
            headers=api.h,
        ).status_code
        == 422
    )


def test_apagar_custo_fixo_tira_do_total(api):
    criado = api.post("/custos/fixos", {"nome": "Energia", "valor_mensal": 400})
    assert criado.status_code == 200, criado.text
    fixo_id = criado.json()["custos_fixos"][0]["id"]
    assert criado.json()["parametros"]["custo_fixo_total"] == pytest.approx(400)
    apagado = api.c.delete(f"/api/v1/custos/fixos/{fixo_id}", headers=api.h)
    assert apagado.status_code == 200, apagado.text
    assert apagado.json()["parametros"]["custo_fixo_total"] == pytest.approx(0)
    assert apagado.json()["custos_fixos"] == []


def test_sem_fonte_loja_nao_consulta_gestao_reader(client, monkeypatch):
    """Organização sem Loja integrada: loja=[] e a sessão gestao_reader não é usada."""
    api = Api(client, entrar(client, "sem-loja-021", "dono", org="padaria-sem-loja", fonte_loja=False))
    farinha = _farinha_com_custo(api)
    pao = _publicar_pao(api, "Pão sem Loja", farinha, 500)
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE produtos SET origem_loja_id = gen_random_uuid() WHERE id = :id"),
            {"id": pao["id"]},
        )

    leituras = []

    def _spy(loja, produto, custo_variavel, custo_total):
        leituras.append(loja)
        if loja is not None:
            raise AssertionError("gestao_reader não deveria ser consultado sem fonte_loja")
        return []

    monkeypatch.setattr(custos_preco, "_precos_loja", _spy)
    corpo = api.get("/custos").json()
    linha = next(p for p in corpo["produtos"] if p["produto_id"] == pao["id"])
    assert linha["loja"] == []
    assert leituras, "deveria passar por _precos_loja para o produto publicado"
    assert all(sessao is None for sessao in leituras)


def test_custos_isolados_por_organizacao(client):
    """Custos fixos e regras de uma org não aparecem na outra."""
    a = Api(client, entrar(client, "dona-custos-a", "dono", org="org-custos-a"))
    assert a.post("/custos/fixos", {"nome": "Aluguel A", "valor_mensal": 900}).status_code == 200
    assert a.c.put(
        "/api/v1/custos/parametros",
        json={"massa_mensal_kg": 100, "regra": {"tipo": "markup", "valor": 2}},
        headers=a.h,
    ).status_code == 200
    familia = a.post("/familias", {"nome": "Família A"})
    assert familia.status_code == 201, familia.text
    assert a.c.put(
        f"/api/v1/custos/familias/{familia.json()['id']}/regra",
        json={"regra": {"tipo": "margem", "valor": 40}},
        headers=a.h,
    ).status_code == 200

    with TestClient(create_app(), base_url="http://testserver") as client_b:
        b = Api(client_b, entrar(client_b, "dono-custos-b", "dono", org="org-custos-b", fonte_loja=False))
        corpo_b = b.get("/custos").json()
        assert corpo_b["custos_fixos"] == []
        assert corpo_b["parametros"]["custo_fixo_total"] == pytest.approx(0)
        assert corpo_b["parametros"]["massa_mensal_kg"] is None
        assert corpo_b["parametros"]["regra"] is None
        assert all(f["nome"] != "Família A" for f in corpo_b["familias"])
        assert all(f.get("regra") is None or f["nome"] != "Família A" for f in corpo_b["familias"])

    corpo_a = a.get("/custos").json()
    assert [f["nome"] for f in corpo_a["custos_fixos"]] == ["Aluguel A"]
    assert corpo_a["parametros"]["massa_mensal_kg"] == pytest.approx(100)
    assert corpo_a["parametros"]["regra"]["tipo"] == "markup"
