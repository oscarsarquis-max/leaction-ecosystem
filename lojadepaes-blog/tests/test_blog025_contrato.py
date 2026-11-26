"""BLOG-025 — contrato cms.normalize receita + enquete detalhe/produto."""
from app import cms, rn


def test_normalize_receita_fields_once():
    row = cms.normalize(
        {
            "slug": "pao-da-vizinha",
            "titulo": "Pão",
            "secao": "receita",
            "idioma": "pt",
            "sistema_destino": "lepain",
            "status": "publicado",
            "autor_nome": "Ana",
            "autor_cidade": "SP",
            "autor_instagram": "@ana",
            "ingredientes": "farinha\nágua",
            "preparo": "misture",
            "historia": "era uma vez",
            "dica": "paciência",
            "tempo": "3 h",
            "rendimento": "1 pão",
            "nivel": "fácil",
        }
    )
    assert row["autor_nome"] == "Ana"
    assert row["ingredientes"] == "farinha\nágua"
    assert row["nivel"] == "fácil"
    assert list(row.keys()).count("autor_nome") == 1
    assert cms.story_path(row) == "/pt/receitas/pao-da-vizinha"


def test_map_enquete_detalhe_sem_produto_antes_do_voto():
    body = {
        "id": 9,
        "pergunta_pt": "Que cheiro tem o seu domingo?",
        "pergunta_en": "What does your Sunday smell like?",
        "opcoes": [
            {
                "id": "a",
                "pt": "Crosta quente",
                "en": "Warm crust",
                "detalhe_pt": "trigo tostado",
                "detalhe_en": "toasted wheat",
                "produto_nome": "NÃO MOSTRAR",
                "produto_url": "https://lojadepaes.com.br/paes/x",
            }
        ],
        "votou": False,
        "fecha_em": "2026-12-01T12:00:00Z",
    }
    mapped = rn.map_enquete(body, "pt")
    assert mapped["opcoes"][0]["detalhe"] == "trigo tostado"
    assert "produto" not in mapped["opcoes"][0]


def test_map_enquete_produto_depois_do_voto():
    body = {
        "id": 9,
        "pergunta_pt": "Pergunta",
        "pergunta_en": "Q",
        "opcoes": [
            {
                "id": "a",
                "pt": "Crosta",
                "en": "Crust",
                "detalhe": "aroma",
                "produto_nome": "Pão de fermentação",
                "produto_url": "https://lojadepaes.com.br/paes/fermentacao-natural",
            }
        ],
        "votou": True,
        "resultado": [{"id": "a", "pct": 100}],
        "total": 1,
    }
    mapped = rn.map_enquete(body, "pt")
    assert mapped["votou"] is True
    assert mapped["opcoes"][0]["produto"]["nome"] == "Pão de fermentação"
