"""GESTAO-024: rendimento por quantos pães (N), padrão 5/14, faixa próxima."""

from decimal import Decimal

import pytest

from app.domain.perdas import resolver_valores
from tests.conftest import entrar
from tests.test_estoque import Api
from tests.test_receitas import _produto, _put


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro-024", "dono"))


def _ref_forma(minimo=400, maximo=1000):
    return {
        "id": f"ref-forma-{minimo}-{maximo}",
        "tipo": "coccao",
        "formato": "forma",
        "peso_min_g": Decimal(minimo),
        "peso_max_g": Decimal(maximo),
        "faixa_min": Decimal(12),
        "faixa_max": Decimal(16),
        "sugerido": Decimal(14),
        "fonte_titulo": "Busby's",
        "fonte_url": None,
        "nota": None,
    }


def _ref_pequeno():
    return {
        "id": "ref-pequeno",
        "tipo": "coccao",
        "formato": "pequeno",
        "peso_min_g": Decimal(40),
        "peso_max_g": Decimal(120),
        "faixa_min": Decimal(15),
        "faixa_max": Decimal(22),
        "sugerido": Decimal(18),
        "fonte_titulo": "Busby's",
        "fonte_url": None,
        "nota": "baguete",
    }


def _padrao(tipo, pct, *, formato=None, familia_id=None, id_="p1"):
    return {
        "id": id_,
        "tipo": tipo,
        "formato": formato,
        "familia_id": familia_id,
        "peso_min_g": None,
        "peso_max_g": None,
        "percentual": Decimal(pct),
        "observacao": "padrão da casa",
        "ativo": True,
    }


def test_caso_oscar_n1_publica(api):
    farinha = api.ingrediente("Farinha 024", "g", "Farinhas")
    pao = _produto(api, "Pão Rústico 024")
    salvo = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha, "quantidade": 720, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="forma",
        unidades_desejadas=1,
        processo={"percentual": 5, "origem": "manual", "motivo": "padrão da casa"},
        coccao={"percentual": 14, "origem": "manual", "motivo": "padrão da casa"},
    )
    assert salvo.status_code == 200, salvo.text
    corpo = salvo.json()
    perdas = corpo["perdas"]
    assert perdas["unidades"] == 1
    assert perdas["peso_cru_g"] == pytest.approx(684)
    assert perdas["peso_final_g"] == pytest.approx(588)
    assert corpo["peso_unidade_g"] == pytest.approx(588)
    assert corpo["rendimento_quantidade"] == pytest.approx(1)
    pub = api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True})
    assert pub.status_code == 200, pub.text
    assert pub.json()["rendimento_quantidade"] == pytest.approx(1)
    assert pub.json()["rendimento_unidade"] == "un"


def test_n8_divide_cru_e_final(api):
    farinha = api.ingrediente("Farinha N8", "g", "Farinhas")
    pao = _produto(api, "Pão N8")
    salvo = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha, "quantidade": 720, "unidade": "g"}],
        rendimento_quantidade=8,
        rendimento_unidade="un",
        peso_unidade_g=None,
        formato="forma",
        unidades_desejadas=8,
        processo={"percentual": 5, "origem": "manual", "motivo": "teste"},
        coccao={"percentual": 14, "origem": "manual", "motivo": "teste"},
    )
    assert salvo.status_code == 200, salvo.text
    perdas = salvo.json()["perdas"]
    assert perdas["unidades"] == 8
    assert perdas["peso_cru_g"] == pytest.approx(85.5) or perdas["peso_cru_g"] == pytest.approx(86)
    # 720 * 0.95 / 8 = 85.5 → 86 g; final = 86 * 0.86 ≈ 74
    cru = Decimal(str(perdas["peso_cru_g"]))
    assert perdas["peso_final_g"] == pytest.approx(float((cru * Decimal("0.86")).quantize(Decimal(1))))


def test_cru_fora_da_faixa_usa_proxima_com_confianca_baixa():
    # Faixas antigas com buraco; cru 700 cai no meio → mais próxima.
    vista = resolver_valores(
        formato="forma",
        familia_id=None,
        peso_final=None,
        massa_total=Decimal(800),
        unidades_desejadas=1,
        unidades_rendimento=1,
        manual_processo={"percentual": 5, "origem": "manual", "motivo": "t"},
        padroes=[],
        referencias=[_ref_forma(400, 600), _ref_forma(800, 1000)],
    )
    assert vista["coccao"]["percentual"] == pytest.approx(14)
    assert vista["coccao"].get("confianca") == "baixa"
    assert "fora da faixa" in (vista["coccao"]["explicacao"].get("nota") or "")


def test_padroes_processo_5_coccao_14_baguete_18():
    padroes = [_padrao("processo", 5, id_="proc"), _padrao("coccao", 14, id_="coc")]
    refs = [_ref_forma(), _ref_pequeno()]
    # Sem formato: processo geral 5 %, cocção geral 14 %.
    geral = resolver_valores(
        formato=None,
        familia_id=None,
        peso_final=None,
        massa_total=Decimal(1000),
        unidades_desejadas=1,
        unidades_rendimento=1,
        padroes=padroes,
        referencias=refs,
    )
    assert geral["processo"]["percentual"] == pytest.approx(5)
    assert geral["processo"]["origem"] == "padrao"
    assert geral["coccao"]["percentual"] == pytest.approx(14)
    assert geral["coccao"]["origem"] == "padrao"
    # Formato sem referência própria (assadeira sem ref aqui): cai no padrão geral 14 %.
    sem_ref = resolver_valores(
        formato="assadeira",
        familia_id=None,
        peso_final=None,
        massa_total=Decimal(1000),
        unidades_desejadas=1,
        unidades_rendimento=1,
        padroes=padroes,
        referencias=refs,
    )
    assert sem_ref["coccao"]["percentual"] == pytest.approx(14)
    assert sem_ref["coccao"]["origem"] == "padrao"
    # Baguete 80 g: referência do formato 18 % vence o padrão geral.
    baguete = resolver_valores(
        formato="pequeno",
        familia_id=None,
        peso_final=None,
        massa_total=Decimal(800),
        unidades_desejadas=8,
        unidades_rendimento=8,
        padroes=padroes,
        referencias=refs,
    )
    assert baguete["coccao"]["percentual"] == pytest.approx(18)
    assert baguete["coccao"]["origem"] == "referencia"


def test_receita_antiga_com_peso_unidade_sem_n(api):
    farinha = api.ingrediente("Farinha legado", "g", "Farinhas")
    pao = _produto(api, "Pão legado peso")
    salvo = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha, "quantidade": 2000, "unidade": "g"}],
        peso_unidade_g=500,
        formato="forma",
        unidades_desejadas=2,
        processo={"percentual": 5, "origem": "manual", "motivo": "legado"},
        coccao={"percentual": 14, "origem": "manual", "motivo": "legado"},
    )
    assert salvo.status_code == 200, salvo.text
    perdas = salvo.json()["perdas"]
    assert perdas["peso_final_g"] == pytest.approx(500)
    assert perdas["peso_cru_g"] == pytest.approx(581)
    assert perdas["unidades"] >= 1
