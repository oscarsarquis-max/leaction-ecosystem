import pytest
from app.domain import cnpj
from app.domain.normalizacao import normalizar, rotulo_padrao_lote, sao_parecidos

# --- CNPJ ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "valor", ["11.222.333/0001-81", "11222333000181", "12.ABC.345/01DE-35", "12abc34501de35"]
)
def test_cnpj_valido_numerico_e_alfanumerico(valor):
    assert cnpj.validar(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "11.222.333/0001-80",
        "00000000000000",
        "11111111111111",
        "12.ABC.345/01DE-3A",
        "1234",
        "12.ABC.345/01DE-36",
    ],
)
def test_cnpj_invalido(valor):
    assert not cnpj.validar(valor)
    with pytest.raises(cnpj.CnpjInvalido):
        cnpj.normalizar(valor)


def test_cnpj_guarda_sem_mascara_e_mostra_formatado():
    assert cnpj.normalizar("11.222.333/0001-81") == "11222333000181"
    assert cnpj.normalizar("12.abc.345/01de-35") == "12ABC34501DE35"
    assert cnpj.formatar("11222333000181") == "11.222.333/0001-81"
    assert cnpj.formatar("12ABC34501DE35") == "12.ABC.345/01DE-35"


# --- nomes parecidos -----------------------------------------------------------------------


def test_normalizar_tira_acento_caixa_e_pontuacao():
    assert normalizar("  Açúcar,  CRISTAL! ") == "acucar cristal"


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Farinha Trigo", "Farinha de trigo"),
        ("Fermento biológico", "Fermento biologico seco"),
        ("Ovos", "Ovo"),
    ],
)
def test_parecidos(a, b):
    assert sao_parecidos(normalizar(a), normalizar(b))


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Açúcar cristal", "Açúcar refinado"),
        ("Farinha integral", "Farinha de trigo integral"),
        ("Sal", "Açúcar"),
    ],
)
def test_nao_parecidos(a, b):
    assert not sao_parecidos(normalizar(a), normalizar(b))


def test_codigo_padrao_de_lote():
    assert rotulo_padrao_lote("2026-11-02", 1) == "E20261102-01"
    assert rotulo_padrao_lote("2026-11-02", 12) == "E20261102-12"
