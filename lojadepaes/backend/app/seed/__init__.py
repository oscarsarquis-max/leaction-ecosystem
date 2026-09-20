from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import (
    Allergen,
    BreadShape,
    DoughAllergen,
    DoughIngredientCompatibility,
    DoughShapeCompatibility,
    DoughType,
    Ingredient,
    IngredientAllergen,
    PairingTip,
)
from app.models.content import Article, InspirationPost
from app.models.enums import AllergenPresence, ContentSource, EditorialStatus


def seed_id(kind: str, slug: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"lojadepaes:{kind}:{slug}")


def _get_or_create(session: Session, model, pk: UUID, values: dict) -> object:
    row = session.get(model, pk)
    if row is not None:
        return row
    row = model(id=pk, **values)
    session.add(row)
    return row


def seed_demo_catalog(session: Session) -> None:
    doughs = [
        (
            "sourdough-classico",
            {
                "name": "Sourdough clássico",
                "slug": "sourdough-classico",
                "short_description": "Fermentação de 24h, miolo macio e acidez equilibrada.",
                "story": "A essência da casa.",
                "fermentation_hours": 24,
                "sort_order": 0,
                "is_active": True,
                "base_price_cents": None,
                "image_ref": None,
            },
        ),
        (
            "integral",
            {
                "name": "Integral",
                "slug": "integral",
                "short_description": "Sabor profundo de cereais, com miolo mais denso e acolhedor.",
                "story": "Rústico e nutritivo.",
                "fermentation_hours": 24,
                "sort_order": 1,
                "is_active": True,
                "base_price_cents": None,
                "image_ref": None,
            },
        ),
        (
            "multigraos",
            {
                "name": "Multigrãos",
                "slug": "multigraos",
                "short_description": "Uma mistura de sementes para textura em cada fatia.",
                "story": "Textura que surpreende.",
                "fermentation_hours": 24,
                "sort_order": 2,
                "is_active": True,
                "base_price_cents": None,
                "image_ref": None,
            },
        ),
    ]
    extras = [
        ("nozes", {"name": "Nozes", "slug": "nozes", "description": "Crocância delicada", "sort_order": 0}),
        (
            "damasco",
            {"name": "Damasco", "slug": "damasco", "description": "Doçura e maciez", "sort_order": 1},
        ),
        (
            "azeitonas",
            {
                "name": "Azeitonas",
                "slug": "azeitonas",
                "description": "Sabor salgado",
                "sort_order": 2,
            },
        ),
        (
            "alecrim",
            {"name": "Alecrim", "slug": "alecrim", "description": "Aroma do jardim", "sort_order": 3},
        ),
    ]
    shapes = [
        (
            "rustico-de-cesto",
            {
                "name": "Rústico de cesto",
                "slug": "rustico-de-cesto",
                "description": "Crosta marcante, desenho de farinha e fatias generosas.",
                "crust_crumb_notes": (
                    "O cesto dá apoio à massa e deixa as espirais de farinha na crosta."
                ),
                "sort_order": 0,
            },
        ),
        (
            "pao-de-forma",
            {
                "name": "Pão de forma",
                "slug": "pao-de-forma",
                "description": "Topo abaulado e fatias regulares para os seus rituais.",
                "crust_crumb_notes": (
                    "A forma sustenta o crescimento. Fatias práticas para torradas e sanduíches."
                ),
                "sort_order": 1,
            },
        ),
    ]

    dough_rows = []
    for slug, values in doughs:
        dough_rows.append(_get_or_create(session, DoughType, seed_id("dough", slug), values))
    ingredient_rows = []
    for slug, values in extras:
        payload = {
            **values,
            "is_active": True,
            "surcharge_cents": None,
            "image_ref": None,
        }
        ingredient_rows.append(_get_or_create(session, Ingredient, seed_id("ingredient", slug), payload))
    shape_rows = []
    for slug, values in shapes:
        payload = {**values, "is_active": True, "image_ref": None}
        shape_rows.append(_get_or_create(session, BreadShape, seed_id("shape", slug), payload))

    session.flush()
    for dough in dough_rows:
        for ingredient in ingredient_rows:
            exists = session.scalar(
                select(DoughIngredientCompatibility.id).where(
                    DoughIngredientCompatibility.dough_type_id == dough.id,
                    DoughIngredientCompatibility.ingredient_id == ingredient.id,
                )
            )
            if exists is None:
                session.add(
                    DoughIngredientCompatibility(dough_type_id=dough.id, ingredient_id=ingredient.id)
                )
        for shape in shape_rows:
            exists = session.scalar(
                select(DoughShapeCompatibility.id).where(
                    DoughShapeCompatibility.dough_type_id == dough.id,
                    DoughShapeCompatibility.bread_shape_id == shape.id,
                )
            )
            if exists is None:
                session.add(
                    DoughShapeCompatibility(dough_type_id=dough.id, bread_shape_id=shape.id)
                )

    by_slug = {row.slug: row for row in ingredient_rows}

    def _tip(slug_a: str, slug_b: str | None, message: str, priority: int) -> None:
        first = by_slug[slug_a]
        second = by_slug[slug_b] if slug_b else None
        left, right = first.id, (second.id if second else None)
        if right is not None and left > right:
            left, right = right, left
        stmt = select(PairingTip.id).where(PairingTip.ingredient_id == left)
        if right is None:
            stmt = stmt.where(PairingTip.paired_ingredient_id.is_(None))
        else:
            stmt = stmt.where(PairingTip.paired_ingredient_id == right)
        exists = session.scalar(stmt)
        if exists is None:
            session.add(
                PairingTip(
                    ingredient_id=left,
                    paired_ingredient_id=right,
                    message=message,
                    priority=priority,
                    is_active=True,
                )
            )

    _tip(
        "alecrim",
        "damasco",
        "O alecrim tem aroma intenso. Use pouco para deixar a doçura do damasco aparecer.",
        30,
    )
    _tip("nozes", None, "Nozes e damasco fazem uma dupla de textura e doçura.", 20)
    _tip("alecrim", None, "Alecrim e azeitonas combinam com uma fatia ainda morna.", 10)

    gluten = _get_or_create(
        session, Allergen, seed_id("allergen", "gluten"), {"name": "Glúten", "slug": "gluten"}
    )
    nuts = _get_or_create(
        session, Allergen, seed_id("allergen", "oleaginosas"), {"name": "Oleaginosas", "slug": "oleaginosas"}
    )
    session.flush()
    for dough in dough_rows:
        exists = session.scalar(
            select(DoughAllergen.id).where(
                DoughAllergen.dough_type_id == dough.id,
                DoughAllergen.allergen_id == gluten.id,
                DoughAllergen.presence == AllergenPresence.CONTAINS.value,
            )
        )
        if exists is None:
            session.add(
                DoughAllergen(
                    dough_type_id=dough.id,
                    allergen_id=gluten.id,
                    presence=AllergenPresence.CONTAINS.value,
                    is_reviewed=False,
                )
            )
    nozes = by_slug["nozes"]
    exists = session.scalar(
        select(IngredientAllergen.id).where(
            IngredientAllergen.ingredient_id == nozes.id,
            IngredientAllergen.allergen_id == nuts.id,
            IngredientAllergen.presence == AllergenPresence.CONTAINS.value,
        )
    )
    if exists is None:
        session.add(
            IngredientAllergen(
                ingredient_id=nozes.id,
                allergen_id=nuts.id,
                presence=AllergenPresence.CONTAINS.value,
                is_reviewed=False,
            )
        )

    articles = [
        (
            "levain-um-ingrediente-vivo",
            "Levain: um ingrediente vivo",
            "começo",
            3,
            [
                "O levain é uma cultura de farinha e água que abriga leveduras e bactérias. Com alimento e tempo, ele fermenta a massa e participa da construção de aroma, sabor e textura.",
                "Alimentar o levain significa renovar parte da cultura com farinha e água. O ritmo muda com a temperatura, o tipo de farinha e a proporção usada. Observe o crescimento, as bolhas e o aroma para conhecer o seu.",
                "Para começar, siga uma receita com quantidades e horários definidos, usando um recipiente limpo. Aprender a ler os sinais da cultura é mais útil do que correr contra o relógio.",
            ],
        ),
        (
            "a-delicadeza-de-uma-boa-dobra",
            "A delicadeza de uma boa dobra",
            "técnica",
            2,
            [
                "As dobras ajudam a organizar a estrutura da massa durante a fermentação. O gesto é simples: levantar uma lateral com delicadeza e dobrá-la sobre o centro.",
                "Com as mãos levemente úmidas, repita o gesto nas outras laterais. Evite rasgar a massa. Depois, cubra e deixe descansar conforme a receita, para que ela relaxe antes da próxima série.",
                "A massa muda a cada descanso. Mais coesão e elasticidade são sinais para observar; o número de dobras depende da farinha, da hidratação e do processo escolhido.",
            ],
        ),
        (
            "como-guardar-seu-pao",
            "Como guardar seu pão",
            "cuidado",
            2,
            [
                "Espere o pão esfriar antes de guardá-lo. O vapor preso em uma embalagem pode deixar a crosta úmida. No dia a dia, um local seco e protegido ajuda a preservar a qualidade.",
                "Para guardar por mais tempo, corte em fatias e congele em uma embalagem bem fechada. Assim, você retira apenas o que vai comer e aquece direto na torradeira ou no forno.",
                "A geladeira costuma acelerar o ressecamento do miolo. Se aparecer mofo, descarte o pão inteiro: retirar apenas a parte visível não é suficiente.",
            ],
        ),
    ]
    for slug, title, category, minutes, paragraphs in articles:
        _get_or_create(
            session,
            Article,
            seed_id("article", slug),
            {
                "title": title,
                "slug": slug,
                "summary": paragraphs[0][:280],
                "body_markdown": "\n\n".join(paragraphs),
                "category": category,
                "cover_image_ref": None,
                "editorial_status": EditorialStatus.PUBLISHED.value,
                "estimated_reading_minutes": minutes,
            },
        )

    stories = [
        (
            "o-ritual-da-manha",
            "Uma fatia. Um café. Uma pausa.",
            "Pão de fermentação natural, manteiga e um começo sem pressa.",
        ),
        (
            "da-crosta-ao-miolo",
            "O encanto dos pequenos detalhes.",
            "Sementes, texturas e sabores que transformam uma fatia.",
        ),
        (
            "feito-com-as-maos",
            "Cada corte, uma assinatura.",
            "A beleza de uma fornada que nunca sai igual à outra.",
        ),
    ]
    for slug, title, caption in stories:
        _get_or_create(
            session,
            InspirationPost,
            seed_id("inspiration", slug),
            {
                "title": title,
                "slug": slug,
                "caption": caption,
                "image_ref": None,
                "credit": None,
                "source_url": None,
                "source_kind": ContentSource.EDITORIAL.value,
                "editorial_status": EditorialStatus.PUBLISHED.value,
            },
        )
