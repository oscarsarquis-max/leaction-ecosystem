from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.accompaniment_context import infer_exclusions_from_text
from app.domain.accompaniments import gigio_lookup
from app.domain.builder_proposal import compact_builder_capabilities, propose_from_slugs
from app.domain.custom_loaf import public_builder_catalog
from app.domain.errors import AuthError, NotFoundError
from app.domain.gigio.editorial import published_notes
from app.domain.gigio.pairing import lookup_pairing_references
from app.domain.gigio.policy import strip_instructions
from app.domain.house_fidelity import HOW_IT_WORKS, RULES_VERSION, current_campaign
from app.domain.products import public_detail, public_list
from app.domain.showcase import public_showcase
from app.domain.schedule import preview_calendar
from app.domain.storefront_orders import public_order_view, require_order_token
from app.domain.week_recipes import (
    featured_published,
    public_view,
    published_by_slug,
    search_published,
)

_SHOWCASE_BROWSE = frozenset(
    {
        "vitrine",
        "paes",
        "pães",
        "pão",
        "pao",
        "ideia",
        "ideias",
        "sugestao",
        "sugestão",
        "sugestoes",
        "sugestões",
    }
)


_SEARCH_STOP = frozenset(
    {
        "quero",
        "comprar",
        "combina",
        "combinar",
        "hora",
        "servir",
        "como",
        "para",
        "com",
        "uma",
        "uns",
        "pelo",
        "pela",
        "este",
        "esta",
        "isso",
        "aquele",
        "naquele",
        "rustico",
        "rústico",
    }
)


def _search_tokens(query: str) -> list[str]:
    tokens = []
    for raw in query.replace("-", " ").split():
        token = raw.strip(".,;:!?")
        if len(token) < 4 or token in _SEARCH_STOP:
            continue
        tokens.append(token)
    return tokens


def asks_published_showcase(text: str) -> bool:
    folded = strip_instructions(text or "").casefold()
    return "vitrine" in folded


def _showcase_browse(query: str) -> bool:
    folded = query.casefold()
    if "vitrine" not in folded:
        return False
    tokens = _search_tokens(query)
    return bool(tokens) and all(token in _SHOWCASE_BROWSE for token in tokens)


def _matches_query(hay: str, query: str) -> bool:
    if not query:
        return True
    if query in hay:
        return True
    tokens = _search_tokens(query)
    return bool(tokens) and any(token in hay for token in tokens)


TOOL_SPECS = [
    {
        "name": "lookup_products",
        "description": (
            "Lista pães publicados. Nunca inclui rascunho. "
            "q vazio não consulta a vitrine. Para a vitrine em exposição, use q=vitrine. "
            "Busca por nome que não encontra o pão não significa que a vitrine inteira está vazia."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
            }
        },
    },
    {
        "name": "lookup_product",
        "description": "Detalhe de um pão publicado pelo slug.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            }
        },
    },
    {
        "name": "lookup_recipes",
        "description": "Busca receitas editoriais publicadas, inclusive a receita em destaque.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
            }
        },
    },
    {
        "name": "lookup_recipe",
        "description": "Receita publicada pelo slug, com ingredientes e modo de preparo.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            }
        },
    },
    {
        "name": "lookup_editorial",
        "description": "Explicações aprovadas sobre preparos, farinhas e conceitos (fermentação, sova, levain).",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"topic_key": {"type": "string"}},
            }
        },
    },
    {
        "name": "lookup_builder",
        "description": (
            "Capacidades reais do Criador (Fazedor de Pães): slugs de preparo, farinha, "
            "complemento e formato. Sem pão na vitrine não encerra a orientação. "
            "Depois use propose_builder só com estes slugs."
        ),
        "inputSchema": {"json": {"type": "object", "properties": {}}},
    },
    {
        "name": "propose_builder",
        "description": (
            "Valida uma composição do Criador com slugs de lookup_builder. "
            "Use quando for propor um pão personalizado. Não invente slug, URL ou preço. "
            "note é observação livre para A Loja avaliar, não escolha estruturada."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "flour": {"type": "string"},
                    "preparation": {"type": "string"},
                    "inclusions": {"type": "array", "items": {"type": "string"}},
                    "shape": {"type": "string"},
                    "note": {"type": "string"},
                },
            }
        },
    },
    {
        "name": "lookup_schedule",
        "description": "Calendário atual: dias abertos, lotados e aviso de mesmo dia.",
        "inputSchema": {"json": {"type": "object", "properties": {}}},
    },
    {
        "name": "lookup_fidelity",
        "description": "Regras vigentes da fidelidade da casa.",
        "inputSchema": {"json": {"type": "object", "properties": {}}},
    },
    {
        "name": "lookup_order",
        "description": "Status mínimo do pedido da sessão autenticada. Sem token não funciona.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"reference": {"type": "string"}},
            }
        },
    },
    {
        "name": "lookup_accompaniments",
        "description": (
            "Complementos do perfil A Loja (vinhos, queijos, frios, azeites, cervejas, batatas) para a mesa desta resposta. "
            "Informe categories só com o que esta resposta realmente recomenda. "
            "dishes (leitao, porco, salada, frios, peixe, sardinha, camarao, lagosta, hamburguer) quando o prato estiver claro. "
            "wine_style só se o cliente pediu esse estilo. beer_style e potato_form só se o cliente restringiu. "
            "slug só se um pão publicado foi identificado. "
            "Não invente IDs, preço ou produto. Não use para pagamento, endereço, pedido ou restrição alimentar. "
            "Não use se a mensagem atual mudou de assunto (carro, agradecimento, reclamação, Pix) "
            "mesmo que o histórico tivesse uma mesa. "
            "Não use esta ferramenta para fontes editoriais — use lookup_pairing_references."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "occasion": {"type": "string"},
                    "categories": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["vinhos", "queijos", "frios", "azeites", "cervejas", "batatas"]},
                    },
                    "wine_style": {"type": "string", "enum": ["tinto", "branco", "rose", "espumante"]},
                    "beer_style": {"type": "string", "enum": ["lager", "pilsen", "ipa", "stout"]},
                    "potato_form": {"type": "string", "enum": ["fritar", "chips", "palha"]},
                    "dishes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["leitao", "porco", "salada", "frios", "peixe", "sardinha", "camarao", "lagosta", "hamburguer"],
                        },
                    },
                },
            }
        },
    },
    {
        "name": "lookup_pairing_references",
        "description": (
            "Referências especializadas publicadas com proveniência. "
            "O campo references fundamenta harmonização. O campo evaluations traz nota de guia "
            "só para o rótulo e safra identificados. O campo catalogs localiza um guia, sem nota. "
            "Não misture as três evidências. Sem item pertinente, oriente de forma geral sem alegar "
            "consulta especializada. Não invente fonte, safra, prêmio ou qualidade. "
            "Estilo não certifica uma garrafa nem herda pontuação. Fonte comercial não é avaliação "
            "independente. Não abra compra nem use a URL da fonte como CTA comercial."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["vinhos", "queijos", "azeites", "frios"]},
                    },
                    "dishes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["leitao", "porco", "salada", "frios", "peixe", "sardinha", "camarao", "lagosta"],
                        },
                    },
                    "q": {"type": "string"},
                },
            }
        },
    },
]


def _catalog_item(item) -> dict:
    cents = item.from_price.cents if item.from_price else None
    return {
        "name": item.name,
        "slug": item.slug,
        "href": f"/paes/{item.slug}",
        "summary": strip_instructions(item.short_description or ""),
        "price": _money(cents),
        "available": bool(item.is_available),
    }


def _money(cents: int | None) -> str | None:
    if cents is None:
        return None
    return f"R$ {cents / 100:.2f}".replace(".", ",")


def execute_tool(
    name: str,
    args: dict,
    *,
    session: Session,
    settings: Settings,
    order_reference: str | None,
    order_token: str | None,
    is_admin: bool,
) -> dict:
    del is_admin
    allowed = {str(spec.get("name") or "") for spec in TOOL_SPECS}
    if name not in allowed:
        return {"error": "unknown_tool", "items": []}
    if name == "lookup_products" and not str(args.get("q") or "").strip():
        return {
            "error": "empty_query",
            "completed": False,
            "items": [],
            "note": "Consulta não realizada. Isto não informa se a vitrine tem pães.",
        }
    if name == "lookup_products":
        listing = public_list(session, 1, 20)
        query = strip_instructions(str(args.get("q") or "")).casefold()
        browse = _showcase_browse(query)
        if browse:
            shown = public_showcase(session)
            items = [_catalog_item(item) for item in shown.items]
            payload = {
                "items": items[:12],
                "count": len(items),
                "mode": "showcase",
                "published_count": len(listing.items),
                "completed": True,
            }
            if not items and listing.items:
                payload["note"] = (
                    "A vitrine em exposição não tem pães agora. Há pães publicados fora dessa seleção."
                )
            elif not items:
                payload["note"] = "A vitrine em exposição não tem pães agora."
            return payload
        items = []
        for item in listing.items:
            hay = f"{item.name} {item.short_description or ''}".casefold()
            if not _matches_query(hay, query):
                continue
            items.append(_catalog_item(item))
        if not items:
            return {
                "items": [],
                "count": 0,
                "mode": "search",
                "completed": True,
                "published_count": len(listing.items),
                "note": (
                    "Nenhum pão publicado corresponde a esse nome. Isso não esvazia a vitrine."
                    if listing.items
                    else "Não há pão publicado agora."
                ),
            }
        return {"items": items[:5], "count": len(items), "mode": "search", "completed": True}
    if name == "lookup_product":
        slug = strip_instructions(str(args.get("slug") or ""))
        try:
            detail = public_detail(session, slug)
        except NotFoundError:
            return {"found": False, "reason": "Este pão não está publicado na vitrine."}
        return {
            "found": True,
            "name": detail.name,
            "slug": detail.slug,
            "href": f"/paes/{detail.slug}",
            "summary": strip_instructions(detail.short_description or ""),
            "description": strip_instructions(detail.long_description or "")[:800],
            "price": _money(detail.from_price.cents if detail.from_price else None),
            "available": detail.is_available,
        }
    if name == "lookup_recipes":
        featured = featured_published(session)
        search = search_published(session, strip_instructions(str(args.get("q") or "")), 1, 8)
        items = []
        if featured is not None:
            view = public_view(session, featured)
            items.append(
                {
                    "title": view["title"],
                    "slug": view["slug"],
                    "href": view["href"],
                    "summary": strip_instructions(view.get("summary") or ""),
                    "featured": True,
                }
            )
        for row in search.get("items") or []:
            if featured is not None and row.get("slug") == featured.slug:
                continue
            items.append(
                {
                    "title": row.get("title"),
                    "slug": row.get("slug"),
                    "href": row.get("href") or f"/receitas/{row.get('slug')}",
                    "summary": strip_instructions(row.get("summary") or ""),
                    "featured": False,
                }
            )
        return {"items": items, "archive_href": "/receitas"}
    if name == "lookup_recipe":
        slug = strip_instructions(str(args.get("slug") or ""))
        try:
            recipe = published_by_slug(session, slug)
        except NotFoundError:
            return {"found": False, "reason": "Esta receita não está publicada."}
        view = public_view(session, recipe)
        return {
            "found": True,
            "title": view["title"],
            "href": view["href"],
            "summary": strip_instructions(view.get("summary") or ""),
            "ingredients": view.get("ingredients") or [],
            "method_text": view.get("method_text") or "",
            "source": "acervo de A Loja",
        }
    if name == "lookup_editorial":
        topic = strip_instructions(str(args.get("topic_key") or "")) or None
        notes = published_notes(session, topic)
        return {
            "notes": [
                {"topic_key": row.topic_key, "title": row.title, "body": row.body, "version": row.version}
                for row in notes
            ]
        }
    if name == "lookup_builder":
        catalog = public_builder_catalog(session)
        compact = compact_builder_capabilities(catalog)
        compact["href"] = "/#criacao"
        compact["note"] = "A rotulagem do criador não autoriza inferir fórmula técnica."
        compact["next"] = "Para propor um pão, chame propose_builder com estes slugs."
        return compact
    if name == "propose_builder":
        inclusions = args.get("inclusions") if isinstance(args.get("inclusions"), list) else []
        return propose_from_slugs(
            session,
            settings,
            flour=str(args.get("flour") or ""),
            preparation=str(args.get("preparation") or ""),
            inclusions=[str(item) for item in inclusions],
            shape=str(args.get("shape") or ""),
            note=str(args.get("note") or ""),
        )
    if name == "lookup_schedule":
        preview = preview_calendar(session, settings)
        open_days = [
            {"date": day.local_date.isoformat(), "label": day.accessible_label, "status": day.status}
            for day in preview.days
            if day.eligible_for_selection
        ][:8]
        return {
            "business_date": preview.days[0].local_date.isoformat() if preview.days else None,
            "same_day_rule": "Pedidos pelo calendário são para os próximos dias. A data de hoje não entra no pedido normal.",
            "date_request": "É possível sugerir uma data avulsa, inclusive hoje; A Loja avalia e não confirma na hora.",
            "capacity_note": "A vaga só fica reservada quando A Loja aceitar o pedido.",
            "preferred_time": "Horário preferido não é hora confirmada.",
            "open_days": open_days,
            "notice": preview.notice,
        }
    if name == "lookup_fidelity":
        campaign = current_campaign(session)
        return {
            "rules_version": RULES_VERSION,
            "active": bool(settings.house_fidelity_active and campaign and campaign.status == "active"),
            "how_it_works": HOW_IT_WORKS,
        }
    if name == "lookup_order":
        reference = strip_instructions(str(args.get("reference") or order_reference or ""))
        if not order_token or not reference:
            return {
                "authorized": False,
                "reason": "Para ver um pedido específico, abra o link protegido que você recebeu. "
                "Número LP, e-mail ou CPF digitados aqui não liberam acesso.",
            }
        try:
            order = require_order_token(session, settings, reference, order_token)
        except (AuthError, NotFoundError):
            return {"authorized": False, "reason": "Não foi possível ler este pedido nesta sessão."}
        view = public_order_view(session, order)
        return {
            "authorized": True,
            "reference": view["public_reference"],
            "visitor_state": view["visitor_state"],
            "next_action": view["notice"],
            "confirmed": view["confirmed"],
            "financially_settled": view["financially_settled"],
            "payment_available": view["payment_available"],
            "href": f"/pedido/{view['public_reference']}",
        }
    if name == "lookup_accompaniments":
        query_text = strip_instructions(str(args.get("q") or args.get("occasion") or ""))
        return gigio_lookup(
            session,
            settings,
            slug=strip_instructions(str(args.get("slug") or "")),
            occasion=strip_instructions(str(args.get("occasion") or "")),
            categories=args.get("categories"),
            wine_style=strip_instructions(str(args.get("wine_style") or "")),
            beer_style=strip_instructions(str(args.get("beer_style") or "")),
            potato_form=strip_instructions(str(args.get("potato_form") or "")),
            dishes=args.get("dishes"),
            query_text=query_text,
            exclusions=infer_exclusions_from_text(query_text),
        )
    if name == "lookup_pairing_references":
        pair_q = strip_instructions(str(args.get("q") or ""))
        return lookup_pairing_references(
            session,
            enabled=bool(settings.gigio_pairing_refs_enabled),
            categories=args.get("categories"),
            dishes=args.get("dishes"),
            query=pair_q,
            exclusions=infer_exclusions_from_text(pair_q),
        )
    return {"error": "ferramenta desconhecida"}

