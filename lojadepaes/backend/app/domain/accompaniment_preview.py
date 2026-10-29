"""Prévia local da vitrine de complementos. Nunca é oferta comercial."""

from __future__ import annotations

DEMO_NOTICE = (
    "Prévia local: este item é fixture de demonstração. "
    "Não é oferta do ActionHub nem preço ou destino comercial."
)
PREVIEW_BANNER = (
    "Esta página está em prévia local. Complementos sem destino validado do Hub "
    "não abrem compra. O Gigio desta sessão usa o modo de desenvolvimento."
)

LOCAL_DEMO_OFFERS = (
    {
        "id": "local-demo-azeite",
        "name": "Azeite extra virgem (demonstração local)",
        "description": "Fixture desta prévia para contar a história à mesa. Sem preço nem link comercial.",
        "category": "azeites",
        "occasion": "Café da manhã",
        "story_title": "Café com fatias mornas",
        "story_lead": (
            "Toste algumas fatias do pão, leve-as à mesa ainda mornas e acrescente "
            "o azeite na hora de servir. Compra e entrega do complemento, quando existirem "
            "de verdade, são separadas da fornada."
        ),
        "why_pairs": "A gordura do azeite equilibra a crosta crocante e o miolo alveolado.",
        "serving_tip": "Sirva ainda morno. Não é um kit nem uma entrega conjunta.",
        "related_product_slugs": (
            "pao-fermentacao-natural-de-trigo",
            "focaccia-alta-italian-focaccia",
        ),
        "related_recipe_slugs": ("sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread",),
    },
)


def preview_cards(session, overlay_builder) -> list[dict]:
    cards = []
    for raw in LOCAL_DEMO_OFFERS:
        card = overlay_builder(session, raw)
        if card is not None:
            cards.append(card)
    return cards
