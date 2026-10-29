"""Três artigos introdutórios da Biblioteca. Fonte editorial: tabela articles."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.models.content import Article

ARTICLE_VERSION = 1
CALCULATOR_HREF = "/biblioteca/calculadora"

SOURCES = (
    {
        "label": "Hamelman, Bread",
        "detail": "Jeffrey Hamelman. Bread: A Baker's Book of Techniques and Recipes. 2. ed. Wiley, 2012. Porcentagem de padeiro e farinha prefermentada.",
    },
    {
        "label": "Calvel, The Taste of Bread",
        "detail": "Raymond Calvel. The Taste of Bread. Aspen, 2001. Fermentação, trabalho da massa e leitura do ponto.",
    },
    {
        "label": "Embrapa — pão de forma integral",
        "href": "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/413642/1/cbcta170.pdf",
        "detail": "Embrapa Agroindústria de Alimentos. Estudo de processo de pão de forma integral: fermentação, método e farinha.",
    },
    {
        "label": "Anvisa — conservas e mofo",
        "href": "https://www.gov.br/anvisa/pt-br/assuntos/alimentos",
        "detail": "Orientação sanitária: alimento com mofo visível não se aproveita pela retirada da parte aparente.",
    },
)

SEEDS: tuple[dict, ...] = (
    {
        "slug": "o-comeco",
        "kicker": "01 / O começo",
        "title": "Levain e a porcentagem de padeiro",
        "summary": "A cultura viva, o alimento e o jeito de anotar a fórmula sem contar a farinha duas vezes.",
        "reading_minutes": 8,
        "cover": "/images/internal%20levain%201%20bread.png",
        "cover_alt": "Culturas de levain e massa levedada",
        "body_markdown": """
O levain é uma cultura de farinha e água que abriga leveduras e bactérias. Com alimento e tempo, ela fermenta a massa e participa do aroma, do sabor e da estrutura. Não é garantia de ausência de glúten nem de digestão melhor para qualquer pessoa.

Alimentar o levain é renovar parte da cultura com farinha e água. O ritmo muda com a temperatura, o tipo de farinha e a proporção. Observe crescimento, bolhas e aroma. Um recipiente limpo e uma receita com quantidades definidas valem mais do que correr contra o relógio.

## Porcentagem de padeiro

Na notação clássica, a farinha total vale 100%. Água, sal e o restante são frações dessa farinha. Se a fórmula pede 1.000 g de farinha, 70% de hidratação e 2% de sal, a água é 700 g e o sal é 20 g. A soma desses três já descreve a massa-base.

O levain não é um quarto ingrediente “por cima” dessa conta. Ele é feito de farinha e água que já entram nos 100% e na hidratação. Se 20% da farinha total vai para o levain (PFF — farinha prefermentada) e esse levain está a 100% de hidratação, o potinho leva 200 g de farinha e 200 g de água: 400 g de levain. Na tigela final entram 800 g de farinha, 500 g de água, 20 g de sal e os 400 g de levain. A massa pesa 1.720 g. Somar 1.000 + 700 + 20 + 400 = 2.120 g conta a farinha e a água do levain duas vezes.

PFF não é o peso do levain. PFF é só a farinha que foi ao potinho. O peso do levain inclui essa farinha e a água dele.

## Como começar em casa

Escolha uma alimentação estável — por exemplo, partes iguais de farinha e água — e anote horário, temperatura da cozinha e o que você viu. Quando a cultura dobra com aroma ácido e doce, ela costuma estar pronta para a massa. Se cheirar a solvente ou não crescer, alimente de novo e espere; não force uma fornada.

A [calculadora da Biblioteca](/biblioteca/calculadora) faz essas contas sem modelo: você informa farinha, hidratação, sal e o levain por PFF ou por peso. Os números da página não consomem inteligência artificial.

Este texto abre o caderno. Não substitui gestão profissional de padaria, custo de produção nem acompanhamento humano.
""".strip(),
    },
    {
        "slug": "as-maos-na-massa",
        "kicker": "02 / As mãos na massa",
        "title": "Dobras, hidratação e o ponto da massa",
        "summary": "O gesto que organiza a estrutura, a água que muda o toque e o descanso que a receita pede.",
        "reading_minutes": 7,
        "cover": "/images/internal%202%20bread.png",
        "cover_alt": "Massa fermentando na tigela e levain no pote",
        "body_markdown": """
As dobras ajudam a organizar a estrutura durante a fermentação. O gesto é simples: com as mãos levemente úmidas, levante uma lateral e dobre sobre o centro. Repita nas outras laterais sem rasgar. Cubra e deixe a massa relaxar antes da próxima série.

O número de dobras depende da farinha, da hidratação e do processo. Massa mais hidratada pede toque mais delicado; massa mais firme aceita um pouco mais de trabalho. Mais coesão e elasticidade depois do descanso são sinais para observar — não uma meta de “força” a qualquer custo.

## Hidratação na prática

Hidratação é a água em relação à farinha total. Setenta por cento em 1.000 g de farinha são 700 g de água, já contando a água do levain. Se o levain levou 200 g dessa água, a tigela recebe 500 g. A [calculadora](/biblioteca/calculadora) escala a mesma fórmula para outro peso de farinha ou para um alvo de massa, por exemplo 860 g a partir de 1.720 g.

Farinha integral e centeio costumam beber mais água e dar massa mais densa. Isso não autoriza inventar horas de fermentação nem prometer miolo. Siga a receita escolhida e leia o ponto: a massa deve esticar sem rasgar de imediato e guardar gás sem desandar.

## Fermentação e sova não se opõem

Fermentação é o tempo em que os microrganismos transformam açúcares. Sova é o trabalho que organiza o glúten. Uma massa pode fermentar e também ser trabalhada. Sovado não significa fermento comercial nem ausência de levain. Sem a descrição aprovada de um pão da Loja, fale do conceito — não do preparo secreto da casa.

Na experimentação doméstica, mude uma coisa de cada vez: hidratação, tempo ou farinha. Anote. A profundidade personalizada com o Gigio, quando o plano estiver ativo, parte desses números e do artigo — não de uma consultoria ilimitada nem de um sistema de custos.
""".strip(),
    },
    {
        "slug": "a-mesa",
        "kicker": "03 / À mesa",
        "title": "Guardar, fatiar e aproveitar o pão",
        "summary": "Esfriar, proteger a crosta, congelar fatias e o que não se faz com mofo.",
        "reading_minutes": 6,
        "cover": "/images/internal%20recipes%201%20bread.png",
        "cover_alt": "Miolo escuro com inclusões ao corte",
        "body_markdown": """
Espere o pão esfriar antes de guardá-lo. O vapor preso na embalagem amolece a crosta e favorece umidade demais. No dia a dia, um pano ou saco de papel em lugar seco protege sem suar. Corte só o que for comer.

Para guardar mais tempo, fatie e congele em embalagem bem fechada. Retire a fatia e aqueça na torradeira ou no forno. A geladeira costuma ressecar o miolo mais depressa do que o ambiente seco — não é o primeiro recurso para o pão de fermentação natural.

## Mofo não se recorta

Se aparecer mofo, descarte o pão inteiro. Retirar só a parte visível não basta: os filamentos avançam pelo miolo. Essa é orientação sanitária, não um palpite de receita.

Pão amanhecido sem sinal de deterioração ainda serve para torrada, pudim de pão ou farofa. Não aproveite pão com cheiro estranho, viscosidade ou bolor. O Gigio da Loja pode sugerir ideias de mesa com os pães da vitrine — isso é atendimento, não o aprofundamento da Biblioteca.

## O que este pilar não promete

À mesa é cuidado cotidiano. Não é harmonização certificada, não é cardápio profissional e não substitui o pedido da Loja. Se quiser um pão da casa, o calendário e o Criador continuam abertos sem assinatura.

Para adaptar uma fórmula caseira ou entender o que os números da calculadora fazem na sua cozinha, o aprofundamento com o Gigio pede o plano único da Biblioteca. A leitura deste artigo e as contas da calculadora permanecem livres.
""".strip(),
    },
)

SLUGS = tuple(item["slug"] for item in SEEDS)


def ensure_library_articles(session: Session) -> list[Article]:
    now = datetime.now(UTC)
    rows: list[Article] = []
    by_slug = {
        row.slug: row
        for row in session.scalars(select(Article).where(Article.slug.in_(SLUGS)))
    }
    for seed in SEEDS:
        row = by_slug.get(seed["slug"])
        if row is None:
            row = Article(
                title=seed["title"],
                slug=seed["slug"],
                summary=seed["summary"],
                body_markdown=seed["body_markdown"],
                category="biblioteca",
                cover_image_ref=seed["cover"],
                editorial_status="published",
                published_at=now,
                estimated_reading_minutes=seed["reading_minutes"],
            )
            session.add(row)
        else:
            row.title = seed["title"]
            row.summary = seed["summary"]
            row.body_markdown = seed["body_markdown"]
            row.category = "biblioteca"
            row.cover_image_ref = seed["cover"]
            row.editorial_status = "published"
            row.estimated_reading_minutes = seed["reading_minutes"]
            if row.published_at is None:
                row.published_at = now
        rows.append(row)
    session.flush()
    return rows


def list_public_articles(session: Session) -> list[dict]:
    ensure_library_articles(session)
    return [card_view(seed) for seed in SEEDS]


def public_article(session: Session, slug: str) -> dict:
    ensure_library_articles(session)
    seed = next((item for item in SEEDS if item["slug"] == slug), None)
    if seed is None:
        raise NotFoundError("este caderno não está na Biblioteca")
    row = session.scalar(select(Article).where(Article.slug == slug, Article.editorial_status == "published"))
    if row is None:
        raise NotFoundError("este caderno não está na Biblioteca")
    return article_view(row, seed)


def card_view(seed: dict) -> dict:
    return {
        "slug": seed["slug"],
        "kicker": seed["kicker"],
        "title": seed["title"],
        "summary": seed["summary"],
        "reading_label": f"Leitura · {seed['reading_minutes']} min",
        "href": f"/biblioteca/{seed['slug']}",
        "photo": {"src": seed["cover"], "alt": seed["cover_alt"]},
        "calculator_href": CALCULATOR_HREF,
        "version": ARTICLE_VERSION,
    }


def article_view(row: Article, seed: dict) -> dict:
    return {
        **card_view(seed),
        "id": str(row.id),
        "body_markdown": row.body_markdown,
        "sources": [dict(item) for item in SOURCES],
        "version": ARTICLE_VERSION,
    }


def article_context(session: Session, slug: str) -> str:
    if not slug:
        return ""
    try:
        article = public_article(session, slug)
    except NotFoundError:
        return ""
    body = str(article.get("body_markdown") or "")[:1200]
    return (
        f" Artigo da Biblioteca id={article['slug']} versão={article['version']}: {article['title']}. "
        f"Use só este texto e a calculadora da casa. Trecho: {body}"
    )
