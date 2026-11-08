# ruff: noqa: F811
"""GESTAO-005A: a sugestão não pode errar o ingrediente.

Qualificadores (seco/fresco, 00/1/integral, com/sem sal...) decidem; a ordem de confiança manda no motivo;
e só há destaque (clique/Enter) quando existe certeza.
"""

import pytest
from app.domain import busca

from tests.test_estoque import farinha
from tests.test_ingrediente_busca import api, novo  # noqa: F401  (fixtures e helper da 005)


def sugestoes(api, item, marca="", **extra):
    return api.get("/ingredientes/sugestao", item=item, marca=marca, **extra).json()["sugestoes"]


def nomes(lista):
    return [(s["ingrediente"] or s["catalogo"])["nome"] for s in lista]


# ---------------------------------------------------------------- os qualificadores (puro)


@pytest.mark.parametrize(
    "item, candidato",
    [
        ("Fermento biológico seco 500 g", "Fermento biológico fresco"),
        ("Fermento fresco 500 g", "Fermento biológico seco"),
        ("Farinha Caputo 00 1 kg", "Farinha de trigo tipo 1"),
        ("Farinha Caputo 00 1 kg", "Farinha de trigo tipo 0"),
        ("Farinha Caputo 00 1 kg", "Farinha de trigo integral"),
        ("Farinha de trigo especial 5 kg", "Farinha de trigo tipo 00"),
        ("Manteiga com sal 200 g", "Manteiga sem sal"),
        ("Manteiga sem sal 200 g", "Manteiga com sal"),
        ("Chocolate branco 1 kg", "Chocolate meio amargo"),
        ("Chocolate ao leite 1 kg", "Chocolate meio amargo"),
        ("Gergelim preto 500 g", "Gergelim branco"),
        ("Canela em pó 100 g", "Canela em flocos"),
        ("Açúcar mascavo 1 kg", "Açúcar demerara"),
        ("Açúcar cristal 5 kg", "Açúcar refinado"),
    ],
)
def test_qualificador_contraditorio_exclui(item, candidato):
    assert busca.contradiz(busca.qualificadores(item), busca.qualificadores(candidato))


@pytest.mark.parametrize(
    "item, candidato",
    [
        ("Fermento 500 g", "Fermento biológico seco"),  # item sem qualificador não exclui ninguém
        ("Farinha de trigo 5 kg", "Farinha de trigo tipo 1"),
        ("Manteiga 200 g", "Manteiga sem sal"),
        ("Fermento biológico seco 500 g", "Fermento biológico seco"),
        ("Farinha Caputo 00 1 kg", "Farinha de trigo tipo 00"),
        ("Fermento seco", "Farinha de trigo tipo 1"),  # grupos diferentes não se cruzam
        ("Leite integral 1 L", "Leite em pó"),
    ],
)
def test_sem_contradicao_nao_exclui(item, candidato):
    assert not busca.contradiz(busca.qualificadores(item), busca.qualificadores(candidato))


def test_peso_nao_vira_qualificador_de_farinha():
    # "1 kg" é peso, não "tipo 1"
    assert busca.qualificadores("Farinha Caputo 00 1 kg") == {"tipo": frozenset({"00"})}
    assert busca.qualificadores("Farinha de trigo 1 kg") == {}
    assert busca.qualificadores("Manteiga com sal 200 g") == {"sal": frozenset({"com sal"})}


# ---------------------------------------------------------------- a sugestão (API)


def test_fermento_seco_sugere_seco_em_primeiro_e_nao_sugere_fresco_mesmo_com_item_fresco(api):
    # na padaria já existe um item "fresco" (e o ingrediente "fresco" que ele usa)
    api.entrada(
        [
            farinha(
                item_nome="Fermento biológico fresco 500 g",
                marca="Fleischmann",
                ingrediente_nome="Fermento biológico fresco",
                quantidade=2,
            )
        ]
    )
    lista = sugestoes(api, "Fermento biológico seco 500 g")
    assert nomes(lista)[0] == "Fermento biológico seco"
    assert lista[0]["origem"] == "catalogo" and lista[0]["destaque"] is True
    assert lista[0]["nivel"] == 2
    assert lista[0]["motivo"].startswith("O nome do item traz")
    assert "Fermento biológico fresco" not in nomes(lista)
    assert all("fresco" not in n.lower() for n in nomes(lista))
    # ...mas ele continua na busca, em "Na sua padaria"
    achados = api.get("/ingredientes/busca", q="Fermento biológico seco").json()["da_padaria"]
    assert "Fermento biológico fresco" in [i["nome"] for i in achados]


def test_fermento_fresco_com_item_seco_na_padaria_faz_o_inverso(api):
    api.entrada(
        [
            farinha(
                item_nome="Fermento biológico seco 500 g",
                marca="Lievito",
                ingrediente_nome="Fermento biológico seco",
            )
        ]
    )
    lista = sugestoes(api, "Fermento fresco 500 g", marca="Fleischmann")
    assert nomes(lista)[0] == "Fermento biológico fresco"
    assert "Fermento biológico seco" not in nomes(lista)
    assert lista[0]["destaque"] is True


def test_farinha_caputo_00_sugere_tipo_00_e_nao_tipo_1_nem_integral(api):
    # mesmo com ingredientes "tipo 1" e "integral" já cadastrados na padaria
    novo(api, "Farinha de trigo tipo 1", categoria="Farinhas", apelidos=["farinha tipo 1"])
    novo(api, "Farinha integral", categoria="Farinhas")
    lista = sugestoes(api, "Farinha Caputo 00 1 kg")
    assert nomes(lista)[0] == "Farinha de trigo tipo 00"
    assert lista[0]["destaque"] is True and lista[0]["nivel"] == 2
    assert lista[0]["origem"] == "catalogo"
    assert "tipo 1" not in " ".join(nomes(lista)) and "integral" not in " ".join(nomes(lista)).lower()


def test_manteiga_com_sal_nao_sugere_manteiga_sem_sal(api):
    lista = sugestoes(api, "Manteiga com sal 200 g")
    assert nomes(lista)[0] == "Manteiga com sal"
    assert "Manteiga sem sal" not in nomes(lista)
    assert lista[0]["destaque"] is True
    # e a que já está na padaria também sai, mesmo sendo a "manteiga" da casa
    novo(api, "Manteiga sem sal", categoria="Gorduras", apelidos=["manteiga"])
    depois = sugestoes(api, "Manteiga com sal 200 g")
    assert "Manteiga sem sal" not in nomes(depois)
    assert nomes(depois)[0] == "Manteiga com sal"


def test_item_sem_qualificador_nao_exclui_ninguem_e_nada_fica_em_destaque(api):
    novo(api, "Fermento biológico seco", categoria="Fermentos")
    novo(api, "Fermento biológico fresco", categoria="Fermentos")
    lista = sugestoes(api, "Fermento 500 g")
    assert {"Fermento biológico seco", "Fermento biológico fresco"} <= set(nomes(lista))
    assert not any(s["destaque"] for s in lista)


def test_dois_candidatos_proximos_nada_fica_em_destaque(api):
    # dois ingredientes da padaria com o mesmo nome no item: sem folga para um deles
    novo(api, "Leite integral", categoria="Laticínios", base="ml", apelidos=["leite"])
    novo(
        api,
        "Leite de caixinha",
        categoria="Laticínios",
        base="ml",
        apelidos=["leite"],
        confirmado_inexistente=True,
    )
    lista = sugestoes(api, "Leite 1 L")
    assert len(lista) >= 2
    assert not any(s["destaque"] for s in lista)


def test_o_mais_especifico_ganha_destaque(api):
    # "Sal grosso" (2 palavras) está à frente de "sal" (1 palavra)
    lista = sugestoes(api, "Sal grosso 1 kg")
    assert nomes(lista)[0] == "Sal marinho"
    assert lista[0]["destaque"] is True
    assert lista[0]["motivo"].startswith("O nome do item traz “sal grosso”")


def test_destaque_so_na_primeira_e_nunca_em_item_parecido_ou_semelhanca(api):
    # a única ligação é por item parecido (nível 3): vem, mas sem destaque
    api.entrada(
        [farinha(item_nome="Pizza pronta Nita", marca="Nita", ingrediente_nome="Base de pizza")]
    )
    lista = sugestoes(api, "Pizza pronta Nita congelada")
    assert lista and lista[0]["origem"] == "item_parecido" and lista[0]["nivel"] == 3
    assert not any(s["destaque"] for s in lista)
    assert sum(1 for s in lista if s["destaque"]) <= 1


def test_item_que_ja_existe_sempre_tem_destaque_e_trava(api):
    api.entrada([farinha(item_nome="Fermento biológico fresco", marca="Fleischmann", ingrediente_nome="Fermento fresco da casa")])
    lista = sugestoes(api, "Fermento biológico fresco", marca="Fleischmann")
    assert lista[0]["nivel"] == 1 and lista[0]["travado"] is True and lista[0]["destaque"] is True


def test_motivo_segue_a_ordem_de_confianca(api):
    api.entrada(
        [farinha(item_nome="Farinha Nita 00", marca="Nita", ingrediente_nome="Farinha de pizza")]
    )
    lista = sugestoes(api, "Farinha Caputo 00 1 kg")
    niveis = [s["nivel"] for s in lista]
    assert niveis == sorted(niveis)
    assert lista[0]["nivel"] == 2  # o catálogo "caputo 00" está contido no nome do item
    assert any(s["nivel"] == 3 and s["motivo"].endswith("usa este") for s in lista)


# ---------------------------------------------------------------- o diálogo "Cadastrar novo"


def test_so_catalogo_devolve_o_candidato_com_nome_e_categoria_para_o_dialogo(api):
    lista = sugestoes(api, "Fermento biológico seco 500 g", so_catalogo="true")
    assert [s["origem"] for s in lista] == ["catalogo"] * len(lista)
    primeira = lista[0]
    assert primeira["destaque"] is True
    assert primeira["catalogo"]["nome"] == "Fermento biológico seco"
    assert primeira["catalogo"]["categoria"] == "Fermentos"
    assert primeira["catalogo"]["unidade_base"] == "g"


def test_so_catalogo_sem_certeza_nao_destaca(api):
    lista = sugestoes(api, "Fermento", so_catalogo="true")
    assert len(lista) >= 2 and not any(s["destaque"] for s in lista)
    assert {"Fermento biológico seco", "Fermento biológico fresco"} <= set(nomes(lista))
