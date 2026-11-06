"""GESTAO-013: função da linha, publicação sem fermento, perdas e rendimento."""

from decimal import Decimal

from app.domain.gigio.gateway import ChatResponse
from app.domain.perdas import massa_necessaria, peso_cru_g, resolver_valores, unidades_de
from app.domain.verificacoes import calibrar_confianca, verificar
from sqlalchemy import text

from tests.test_gigio import _pedir, _produto, _resposta
from tests.test_receitas import _put

pytest_plugins = ["tests.test_gigio"]


def _medicao(cru="95", final="80"):
    return {
        "massa_total_g": Decimal("1000"),
        "pecas": 10,
        "peso_cru_medio_g": Decimal(cru),
        "peso_final_medio_g": Decimal(final),
        "data": "2026-11-06",
    }


def _ref_forma():
    return {
        "id": "ref-forma",
        "tipo": "coccao",
        "formato": "forma",
        "peso_min_g": Decimal(400),
        "peso_max_g": Decimal(600),
        "faixa_min": Decimal(12),
        "faixa_max": Decimal(16),
        "sugerido": Decimal(14),
        "fonte_titulo": "Busby's Bakery",
        "fonte_url": "https://www.busbysbakery.com/?p=10014863",
        "nota": None,
    }


def test_acucar_de_cobertura_fica_e_o_de_massa_sai(api, falso):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    acucar = api.ingrediente("Açúcar", "g", "Açúcares e mel")
    api.ingrediente("Fermento", "g", "Fermentos")
    massa = _produto(api, "Massa com açúcar", uso_venda=False, uso_componente=True, confirmado_inexistente=True)
    salvo = _put(
        api,
        massa["id"],
        linhas=[
            {"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"},
            {"ingrediente_id": acucar, "quantidade": 20, "unidade": "g"},
        ],
        rendimento_quantidade=500,
        rendimento_unidade="g",
    )
    assert salvo.status_code == 200, salvo.text
    assert api.post(f"/receitas/{massa['id']}/publicar", {"confirmar_sem_fermento": True}).status_code == 200

    def linha(funcao):
        return {
            "ingrediente": "Açúcar",
            "quantidade_g": 40,
            "percentual": 8,
            "confianca": "media",
            "motivo": "Calda.",
            "funcao": funcao,
        }

    fermento = {
        "ingrediente": "Fermento",
        "quantidade_g": 5,
        "percentual": 1,
        "confianca": "media",
        "motivo": "Fermento.",
        "funcao": "massa",
    }
    pao = _produto(api, "Pão com calda")
    falso.script.append(_resposta([linha("cobertura"), fermento]))
    cobertura = _pedir(api, pao["id"], massa_base_id=massa["id"], massa_base_quantidade=500)
    assert cobertura.status_code == 200, cobertura.text
    nomes = [item["nome"] for item in cobertura.json()["linhas"]]
    assert "Açúcar" in nomes
    assert not any("Açúcar" in aviso and "descartada" in aviso for aviso in cobertura.json()["avisos"])

    outro = _produto(api, "Pão que repete o açúcar")
    falso.script.append(_resposta([linha("massa"), fermento]))
    repetido = _pedir(api, outro["id"], massa_base_id=massa["id"], massa_base_quantidade=500)
    assert repetido.status_code == 200, repetido.text
    assert not any(item["nome"] == "Açúcar" and item.get("funcao") == "massa" for item in repetido.json()["linhas"])
    assert any("Açúcar" in aviso and "descartada" in aviso for aviso in repetido.json()["avisos"])


def test_publicar_sem_fermento_exige_confirmacao(api):
    farinha = api.ingrediente("Farinha de trigo", "g", "Farinhas")
    pao = _produto(api, "Pão sem fermento na ficha")
    salvo = _put(
        api,
        pao["id"],
        linhas=[{"ingrediente_id": farinha, "quantidade": 500, "unidade": "g"}],
        rendimento_quantidade=1,
        rendimento_unidade="un",
    )
    assert salvo.status_code == 200, salvo.text
    negado = api.post(f"/receitas/{pao['id']}/publicar")
    assert negado.status_code == 422
    assert "fermento" in negado.json()["detail"]["mensagem"].lower()
    confirmado = api.post(f"/receitas/{pao['id']}/publicar", {"confirmar_sem_fermento": True})
    assert confirmado.status_code == 200, confirmado.text
    assert confirmado.json()["situacao"] == "publicada"


def test_sal_total_explica_a_massa_base():
    avisos = verificar(
        [{"nome": "Sal", "categoria": "Sal e temperos", "quantidade_g": Decimal("10.2"), "funcao": "massa"}],
        farinha=Decimal(300),
        familia=None,
        componentes=[
            {
                "nome": "Massa sovada",
                "folhas": [
                    {"nome": "Farinha de trigo", "categoria": "Farinhas", "quantidade_g": Decimal(300)},
                    {"nome": "Sal", "categoria": "Sal e temperos", "quantidade_g": Decimal(6)},
                ],
            }
        ],
    )
    textos = [aviso["mensagem"] for aviso in avisos["avisos"]]
    assert "Sal total 5,4 % (2,0 % da massa-base + 3,4 % desta receita)." in textos


def test_sal_a_2_porcento_fica_media_e_nao_baixa():
    assert calibrar_confianca("baixa", fixa=False, padrao=False, descrita=False, classico=True) == "media"
    assert calibrar_confianca("alta", fixa=False, padrao=False, descrita=False, classico=True) == "media"
    assert calibrar_confianca("baixa", fixa=False, padrao=False, descrita=False) == "baixa"


def test_peso_cru_unidades_e_massa_necessaria():
    assert peso_cru_g(Decimal(500), Decimal(14)) == Decimal(581)
    assert unidades_de(Decimal(1400), Decimal(5), Decimal(581)) == 2
    assert massa_necessaria(10, Decimal(500), Decimal(14), Decimal(5)) == Decimal(6120)


def test_prioridade_medido_padrao_referencia_nada_e_manual():
    ref = _ref_forma()
    padrao = {
        "id": "casa",
        "tipo": "coccao",
        "formato": "forma",
        "familia_id": None,
        "peso_min_g": Decimal(400),
        "peso_max_g": Decimal(600),
        "percentual": Decimal(10),
        "ativo": True,
    }
    duas = [_medicao(), _medicao()]
    tres = [_medicao(), _medicao(), _medicao()]
    base = dict(formato="forma", familia_id=None, peso_final=Decimal(500), massa_total=None, unidades_desejadas=None)

    so_ref = resolver_valores(**base, referencias=[ref])
    assert so_ref["coccao"]["origem"] == "referencia"
    assert so_ref["coccao"]["percentual"] == 14

    com_padrao = resolver_valores(**base, referencias=[ref], padroes=[padrao])
    assert com_padrao["coccao"]["origem"] == "padrao"
    assert com_padrao["coccao"]["percentual"] == 10

    com_duas = resolver_valores(**base, referencias=[ref], padroes=[padrao], medicoes=duas)
    assert com_duas["coccao"]["origem"] == "padrao"

    com_tres = resolver_valores(**base, referencias=[ref], padroes=[padrao], medicoes=tres)
    assert com_tres["coccao"]["origem"] == "medido"
    assert "medido em 3" in com_tres["coccao"]["rotulo"]

    manual = resolver_valores(
        **base,
        referencias=[ref],
        padroes=[padrao],
        medicoes=tres,
        manual_coccao={"percentual": Decimal("8"), "origem": "manual", "motivo": "Forno da casa."},
    )
    assert manual["coccao"]["origem"] == "manual"
    assert manual["coccao"]["percentual"] == 8

    nada = resolver_valores(formato="livre", familia_id=None, peso_final=Decimal(50), massa_total=None, unidades_desejadas=None)
    assert nada["coccao"]["origem"] is None
    assert nada["coccao"]["percentual"] is None
    assert nada["coccao"]["rotulo"] == "sem referência"


def test_gigio_ignora_perda_pct(api, falso):
    api.ingrediente("Fermento", "g", "Fermentos")
    pao = _produto(api, "Pão cuja perda o Gigio inventou")
    falso.script.append(
        ChatResponse(
            text="",
            tool_use=[
                {
                    "id": "t",
                    "name": "sugerir_receita",
                    "input": {
                        "linhas": [
                            {
                                "ingrediente": "Fermento",
                                "quantidade_g": 5,
                                "percentual": 1,
                                "confianca": "media",
                                "motivo": "Fermento.",
                            }
                        ],
                        "perda_pct": 14,
                        "rendimento_g": 800,
                    },
                }
            ],
            model_id="fake",
            input_tokens=3,
            output_tokens=4,
        )
    )
    resposta = _pedir(api, pao["id"], descricao="Pão simples.")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["perda_pct"] is None
    assert any("ignorada" in aviso for aviso in resposta.json()["avisos"])


def test_carga_da_referencia_e_idempotente(db):
    from app.domain.perdas import carregar

    db.execute(text("DELETE FROM perda_referencia"))
    db.commit()
    primeira = carregar(db)
    db.commit()
    segunda = carregar(db)
    db.commit()
    assert primeira.versao == 1
    assert primeira.inseridos == 7
    assert segunda.inseridos == 0
    assert segunda.alterados == 0


def test_padrao_de_perda_nao_vaza_entre_organizacoes(duas_orgs):
    a, b = duas_orgs
    criado = a.post(
        "/perdas/padroes",
        {
            "tipo": "coccao",
            "formato": "livre",
            "peso_min_g": 10,
            "peso_max_g": 20,
            "percentual": 9,
            "observacao": "só desta casa",
        },
    )
    assert criado.status_code == 201, criado.text
    da_outra = b.get("/perdas/padroes").json()["padroes"]
    assert all(item["id"] != criado.json()["id"] for item in da_outra)
    da_casa = a.get("/perdas/padroes").json()["padroes"]
    assert any(item["id"] == criado.json()["id"] for item in da_casa)
