# ruff: noqa: F811
"""GESTAO-006: catálogo v2 (71 itens) e as sugestões que ele destrava.

Trigo sarraceno não é trigo; "nuvola" é a farinha de trigo tipo 0.
"""

from pathlib import Path

from app.domain import busca
from app.domain.catalogo import carregar_catalogo, ler_catalogo
from app.models.estoque import CatalogoIngrediente
from sqlalchemy import delete, func, select

from tests.test_estoque import farinha
from tests.test_ingrediente_busca import api, novo  # noqa: F401  (fixtures e helper da 005)

V1 = Path(__file__).parent / "fixtures" / "catalogo-ingredientes-v1.yaml"


def sugestoes(api, item, marca=""):
    return api.get("/ingredientes/sugestao", item=item, marca=marca).json()["sugestoes"]


def nomes(lista):
    return [(s["ingrediente"] or s["catalogo"])["nome"] for s in lista]


# ---------------------------------------------------------------- a carga do catálogo v2


def test_catalogo_v2_tem_71_itens_o_sarraceno_e_os_apelidos_novos():
    c = ler_catalogo()
    por_nome = {e.nome: e for e in c.entradas}
    assert c.versao == 2 and len(c.entradas) == 71
    assert set(por_nome["Farinha de trigo sarraceno"].apelidos) >= {
        "trigo sarraceno",
        "sarraceno",
        "trigo mourisco",
    }
    assert {"nuvola", "farinha para pizza"} <= set(por_nome["Farinha de trigo tipo 0"].apelidos)


def test_de_v1_para_v2_insere_1_e_altera_1_com_versao_2(db):
    """Como em produção: o banco tem a v1 (70) e o `carregar-catalogo` roda com o arquivo v2."""
    db.execute(delete(CatalogoIngrediente))
    try:
        v1 = carregar_catalogo(db, V1)
        assert (v1.versao, v1.inseridos, v1.alterados) == (1, 70, 0)
        v2 = carregar_catalogo(db)
        assert (v2.versao, v2.inseridos, v2.alterados, v2.iguais) == (2, 1, 1, 69)
        assert db.scalar(select(func.count()).select_from(CatalogoIngrediente)) == 71
        tipo0 = db.scalar(
            select(CatalogoIngrediente).where(CatalogoIngrediente.nome == "Farinha de trigo tipo 0")
        )
        assert tipo0.versao == 2 and "nuvola" in tipo0.apelidos
        sarraceno = db.scalar(
            select(CatalogoIngrediente).where(
                CatalogoIngrediente.nome == "Farinha de trigo sarraceno"
            )
        )
        assert sarraceno.versao == 2 and sarraceno.categoria == "Farinhas"
        # o que não mudou fica com a versão em que entrou: nada é tocado
        assert db.scalar(
            select(CatalogoIngrediente.versao).where(
                CatalogoIngrediente.nome == "Farinha de trigo tipo 00"
            )
        ) == 1
        # rodar de novo não muda nada
        outra = carregar_catalogo(db)
        assert (outra.inseridos, outra.alterados, outra.iguais) == (0, 0, 71)
    finally:
        db.rollback()


# ---------------------------------------------------------------- sarraceno não é trigo


def test_sarraceno_e_um_qualificador_que_exclui_farinha_de_trigo_sem_o_termo():
    q = busca.qualificadores("Trigo Sarraceno 500 g")
    assert q == {"grao": frozenset({"sarraceno"})}
    assert busca.qualificadores("Trigo mourisco") == q
    # exclui os "Farinha de trigo ..." sem o termo, mesmo sem outro qualificador no mesmo grupo
    for candidato in ("Farinha de trigo especial", "Farinha de trigo tipo 1", "Farinha de trigo"):
        assert busca.contradiz(q, busca.qualificadores(candidato))
    assert not busca.contradiz(q, busca.qualificadores("Farinha de trigo sarraceno"))
    # item sem o termo não exclui ninguém
    assert not busca.contradiz(
        busca.qualificadores("Farinha de trigo 1 kg"),
        busca.qualificadores("Farinha de trigo sarraceno"),
    )


def test_trigo_sarraceno_sugere_farinha_de_trigo_sarraceno_e_nunca_a_especial(api):
    # a padaria tem a "especial" (com o apelido "farinha de trigo") e um item "Trigo Sarraceno" ligado
    # a ela por engano: esse item não pode avalizar a especial
    novo(api, "Farinha de trigo especial", categoria="Farinhas", apelidos=["farinha de trigo"])
    api.entrada(
        [
            farinha(
                item_nome="Trigo Sarraceno",
                marca="Granel",
                ingrediente_nome="Farinha de trigo especial",
                quantidade=1,
            )
        ]
    )
    for item, marca in (("Trigo Sarraceno", "Yoki"), ("Trigo Sarraceno 500 g", ""), ("Farinha de trigo mourisco", "")):
        lista = sugestoes(api, item, marca)
        assert nomes(lista)[0] == "Farinha de trigo sarraceno", (item, nomes(lista))
        assert lista[0]["origem"] == "catalogo" and lista[0]["destaque"] is True
        assert lista[0]["nivel"] == 2
        assert "Farinha de trigo especial" not in nomes(lista), (item, nomes(lista))


def test_farinha_de_trigo_comum_ainda_sugere_a_especial(api):
    novo(api, "Farinha de trigo especial", categoria="Farinhas", apelidos=["farinha de trigo"])
    lista = sugestoes(api, "Farinha de trigo 5 kg")
    assert nomes(lista)[0] == "Farinha de trigo especial"
    assert lista[0]["destaque"] is True


# ---------------------------------------------------------------- nuvola é o tipo 0


def test_farinha_de_trigo_tipo_nuvola_sugere_tipo_0_em_destaque(api):
    lista = sugestoes(api, "Farinha de Trigo Tipo Nuvola")
    assert nomes(lista)[0] == "Farinha de trigo tipo 0"
    assert lista[0]["destaque"] is True and lista[0]["nivel"] == 2
    assert lista[0]["motivo"].startswith("O nome do item traz “nuvola”")


def test_nuvola_ganha_da_especial_mesmo_com_a_especial_ja_na_padaria(api):
    novo(api, "Farinha de trigo especial", categoria="Farinhas", apelidos=["farinha de trigo"])
    lista = sugestoes(api, "Farinha de Trigo Tipo Nuvola 1 kg", "Antico Molino")
    assert nomes(lista)[0] == "Farinha de trigo tipo 0"
    assert lista[0]["destaque"] is True
    # a genérica pode aparecer depois, nunca em destaque
    assert sum(1 for s in lista if s["destaque"]) == 1


def test_farinha_para_pizza_tambem_leva_ao_tipo_0(api):
    assert nomes(sugestoes(api, "Farinha para pizza 25 kg"))[0] == "Farinha de trigo tipo 0"
