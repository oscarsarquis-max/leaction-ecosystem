from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import ConfirmationError, NotFoundError
from app.domain import marketplace_client
from app.domain.gigio.pairing import (
    _identity_mentioned,
    evaluation_ready_references,
    reference_admin_view,
    select_published_for_chat,
)
from app.domain.gigio.pairing_match import catalog_match_tier, match_offer_to_evaluation
from app.domain.accompaniment_context import (
    apply_vitrine_query,
    build_vitrine_href,
    describe_context,
    display_offer_title,
    inactive_context,
    infer_exclusions_from_text,
    meal_summary,
    normalize_category,
    parse_vitrine_query,
    select_contextual_cards,
    story_display_title,
)
from app.domain.offer_contract import offer_fits_contract
from app.domain.accompaniment_preview import DEMO_NOTICE, PREVIEW_BANNER, preview_cards
from app.domain.marketplace_client import HubOffer
from app.domain.marketplace_links import (
    keep_official_outbound_url,
    marketplace_label,
    outbound_cta,
    sanitize_plain_text,
    separate_purchase_notice,
)
from app.models.accompaniments import AccompanimentItem
from app.models.enums import EditorialStatus
from app.models.products import Product
from app.models.week_recipes import WeekRecipe

PAGE_TITLE = "Para acompanhar seu pão"
PAGE_INTRO = (
    "Uma seleção de complementos e acessórios para aproveitar seus pães à mesa "
    "ou encontrar uma ideia de presente."
)
COMMISSION_NOTE = "Links comissionados: A Loja pode receber uma comissão pelas compras."
EXTERNAL_NOTICE = (
    "Compra e entrega realizadas separadamente pelo Mercado Livre ou pela Amazon. "
    "Confira preço e disponibilidade no site de compra."
)
DELIVERY_HELP = (
    "Confira a previsão de entrega no Mercado Livre ou na Amazon e informe a data abaixo "
    "para planejar sua fornada. As compras e entregas são separadas."
)
DELIVERY_CLIENT_NOTE = (
    "A data é informada por você; A Loja não confirma automaticamente a entrega do site de compra."
)
HUB_CURATION_HOME = (
    "ActionHub → Marketplace → curadoria do perfil A Loja (vinhos, queijos, frios, azeites, cervejas, batatas). "
    "Preço, foto e link vêm só de lá. Aqui só narrativa e pães/receitas."
)
OCCASION_BY_CATEGORY = {
    "azeites": "Azeites",
    "queijos": "Queijos",
    "frios": "Frios",
    "vinhos": "Vinhos",
    "cervejas": "Cervejas",
    "batatas": "Batatas",
}


def public_vitrine_visible(session: Session, settings: Settings) -> bool:
    del session
    if not settings.public_accompaniments_enabled:
        return False
    if settings.accompaniments_preview_eligible:
        return True
    return bool(marketplace_client.cached_profile_count())


def published_cards(session: Session, settings: Settings, *, refresh: bool = False) -> tuple[list[dict], str]:
    try:
        result = marketplace_client.fetch_hub_profile_catalog(settings, refresh=refresh)
    except Exception:
        result = {"ok": False, "offers": []}
    if result.get("ok"):
        overlays = _overlay_map(session)
        items = []
        for offer in result.get("offers") or []:
            card = _card_from_offer(session, offer, overlays.get(offer.id))
            if card is not None:
                items.append(card)
        if items:
            marketplace_client.remember_profile_count(len(items))
            return items, "hub"
    marketplace_client.remember_profile_count(0)
    if settings.accompaniments_preview_eligible:
        demo = preview_cards(session, _card_from_preview)
        return demo, "local_preview"
    return [], "unavailable" if not result.get("ok") else "empty"


def public_catalog(
    session: Session,
    settings: Settings,
    *,
    refresh: bool = False,
    cats: object = "",
    tipo: object = "",
    pao: object = "",
    ids: object = "",
    mesa: object = "",
    cerveja: object = "",
    forma: object = "",
) -> dict:
    if not settings.public_accompaniments_enabled:
        return _empty_public(enabled=False, source_status="off")
    items, source_status = published_cards(session, settings, refresh=refresh)
    if not items:
        return _empty_public(enabled=False, source_status=source_status)
    query = parse_vitrine_query(
        cats=cats,
        tipo=tipo,
        pao=pao,
        ids=ids,
        mesa=mesa,
        beer_style=cerveja,
        potato_form=forma,
    )
    bread_name = _published_bread_name(session, query.bread_slug) if query.bread_slug else None
    if query.bread_slug and not bread_name:
        query = parse_vitrine_query(
            cats=query.categories,
            tipo=query.wine_style,
            beer_style=query.beer_style,
            potato_form=query.potato_form,
            ids=query.offer_ids,
            mesa=query.dishes,
        )
    visible = apply_vitrine_query(items, query) if query.useful else items
    if query.useful:
        visible = select_contextual_cards(visible, query)
    context = describe_context(query, visible, bread_name=bread_name) if query.useful else inactive_context()
    preview = source_status == "local_preview"
    summary = context.get("summary") or meal_summary(query)
    if context["active"] and summary:
        intro = (
            f"Sugestões para a mesa com {summary}. "
            "Os botões abrem o Mercado Livre ou a Amazon."
        )
    elif context["active"]:
        intro = "Seleção sugerida a partir da conversa com o Gigio. Os botões abrem o Mercado Livre ou a Amazon."
    else:
        intro = PAGE_INTRO
    return {
        "enabled": True,
        "title": context["title"] if context["active"] else PAGE_TITLE,
        "intro": intro,
        "source_status": source_status,
        "preview": preview,
        "demo_notice": PREVIEW_BANNER if preview else None,
        "commission_note": None if preview else COMMISSION_NOTE,
        "external_notice": DEMO_NOTICE if preview else EXTERNAL_NOTICE,
        "delivery_help": {"mode": "manual", "text": DELIVERY_HELP, "client_note": DELIVERY_CLIENT_NOTE},
        "attribution_ready": any(item.get("outbound_href") for item in visible),
        "stories": _group_stories(visible),
        "items": visible,
        "context": context,
    }


def public_for_product(session: Session, settings: Settings, slug: str) -> dict:
    if not settings.public_accompaniments_enabled:
        return {"enabled": False, "items": []}
    cards, _status = published_cards(session, settings, refresh=False)
    wanted = sanitize_plain_text(slug, limit=80).casefold()
    items = [
        item
        for item in cards
        if wanted and wanted in {row.casefold() for row in item.get("related_product_slugs") or []}
    ]
    return {
        "enabled": bool(items),
        "commission_note": COMMISSION_NOTE if items else None,
        "external_notice": EXTERNAL_NOTICE if items else None,
        "items": items[:3],
    }


SUGGESTED_CTA = "Ver acompanhamentos sugeridos"
ALTERNATIVES_CTA = "Ver alternativas para esta combinação"
EXPLORE_CTA = "Explorar a vitrine"
GENERIC_CTA = "Ver todos os acompanhamentos"
HUB_NOTICE = "A consulta aos acompanhamentos não foi concluída."
NO_MATCH_NOTICE = "Não há correspondência comercial para esta sugestão."


def _card_as_offer(item: dict) -> dict:
    return {
        "hub_offer_id": item.get("hub_offer_id") or item.get("id") or "",
        "id": item.get("hub_offer_id") or item.get("id") or "",
        "title": item.get("name") or item.get("source_title") or item.get("title") or "",
        "category": item.get("category") or "",
        "brand": item.get("brand") or "",
    }


def _exact_evaluation_state(session: Session, query_text: str, cards: list[dict]) -> str:
    blob = " ".join((query_text or "").casefold().replace("á", "a").replace("ã", "a").split())
    if not blob:
        return "none"
    offers = [_card_as_offer(item) for item in cards]
    sought = False
    for row in evaluation_ready_references(session):
        if not _identity_mentioned(row, blob):
            continue
        sought = True
        view = reference_admin_view(row)
        if any(match_offer_to_evaluation(offer, view)["correspondence"] == "specific" for offer in offers):
            return "found"
    return "missing" if sought else "none"


def _looks_like_cold_cut(item: dict) -> bool:
    if item.get("category") == "frios":
        return True
    title = str(item.get("name") or item.get("source_title") or item.get("title") or "")
    return offer_fits_contract(title=title, category="frios")


def gigio_lookup(
    session: Session,
    settings: Settings,
    *,
    slug: str = "",
    occasion: str = "",
    categories: object = None,
    wine_style: str = "",
    beer_style: str = "",
    potato_form: str = "",
    ids: object = None,
    dishes: object = None,
    query_text: str = "",
    exclusions: object = None,
) -> dict:
    if not settings.gigio_accompaniments_enabled:
        return {
            "available": False,
            "reason": "Sugestões de complemento estão desligadas.",
            "items": [],
            "cta": None,
            "hub_status": "off",
            "notice": "",
        }
    cards, source_status = published_cards(session, settings, refresh=False)
    wanted = {normalize_category(item) for item in (categories or []) if normalize_category(item)}
    have = {str(item.get("category") or "") for item in cards}
    if wanted - have:
        cards, source_status = published_cards(session, settings, refresh=True)
    if not cards:
        if source_status == "unavailable":
            return {
                "available": False,
                "reason": HUB_NOTICE,
                "items": [],
                "cta": None,
                "hub_status": "unavailable",
                "notice": HUB_NOTICE,
            }
        return {
            "available": False,
            "reason": "Não há complementos publicados para A Loja neste momento.",
            "items": [],
            "cta": None,
            "hub_status": "empty",
            "notice": "",
        }
    query = parse_vitrine_query(
        categories=categories,
        wine_style=wine_style,
        beer_style=beer_style,
        potato_form=potato_form,
        slug=slug,
        ids=ids,
        dishes=dishes,
    )
    bread_name = _published_bread_name(session, query.bread_slug) if query.bread_slug else None
    if query.bread_slug and not bread_name:
        query = parse_vitrine_query(
            categories=query.categories,
            wine_style=query.wine_style,
            beer_style=query.beer_style,
            potato_form=query.potato_form,
            ids=query.offer_ids,
            dishes=query.dishes,
        )
    related_exists = bool(
        query.bread_slug
        and any(query.bread_slug in {str(row) for row in item.get("related_product_slugs") or []} for item in cards)
    )
    if query.bread_slug and not query.categories and not query.wine_style and not query.offer_ids and not related_exists:
        return {
            "available": False,
            "reason": "Não há complementos disponíveis para essa sugestão.",
            "items": [],
            "cta": {"href": "/acompanhar", "label": "Ver todos os acompanhamentos", "kind": "vitrine"},
        }
    occasion_cf = sanitize_plain_text(occasion, limit=80).casefold()
    if occasion_cf and not query.categories:
        occ_cards = [
            item
            for item in cards
            if occasion_cf in str(item.get("occasion") or "").casefold()
            or occasion_cf in str(item.get("story_title") or "").casefold()
        ]
        if occ_cards:
            query = parse_vitrine_query(
                categories={item.get("category") for item in occ_cards if item.get("category")},
                wine_style=query.wine_style,
                slug=query.bread_slug,
                ids=query.offer_ids,
            )
    if not query.useful:
        return {
            "available": False,
            "reason": "Sem critério publicado para abrir a vitrine contextual.",
            "items": [],
            "cta": None,
        }
    matched = apply_vitrine_query(cards, query)
    excluded = {str(item) for item in (exclusions or [])}
    if query_text:
        excluded |= infer_exclusions_from_text(query_text)
    specialized_applied = False
    match_tier = "none"
    catalog_alternatives = False
    if settings.gigio_pairing_refs_enabled:
        refs = select_published_for_chat(
            session,
            enabled=True,
            categories=query.categories,
            dishes=query.dishes,
            query=query_text or " ".join(query.dishes),
            exclusions=excluded,
        )
        if refs:
            specialized_applied = True
            ref_payloads = [
                {
                    "category": row.category,
                    "scope": row.scope,
                    "match_hints": row.match_hints or [],
                    "retrieval_role": row.retrieval_role,
                    "evidence_type": row.evidence_type,
                    "verification_status": row.verification_status,
                    "editorial_status": row.editorial_status,
                    "identity": row.identity or {},
                    "loja_choice": row.loja_choice,
                }
                for row in refs
            ]
            specialized = {row.category for row in refs}
            chosen, match_tier = catalog_match_tier(matched, ref_payloads)
            catalog_alternatives = match_tier == "style" and any(str(row.scope or "") == "product" for row in refs)
            compatible = set(chosen)
            matched = [
                item
                for item in matched
                if item.get("category") not in specialized
                or str(item.get("hub_offer_id") or item.get("id") or "") in compatible
            ]
    if "frios" in excluded:
        matched = [item for item in matched if not _looks_like_cold_cut(item)]
    if "vinhos" in excluded:
        matched = [item for item in matched if item.get("category") != "vinhos"]
    if "cervejas" in excluded:
        matched = [item for item in matched if item.get("category") != "cervejas"]
    if "queijos" in excluded:
        matched = [item for item in matched if item.get("category") != "queijos"]
    matched = select_contextual_cards(matched, query)
    query = parse_vitrine_query(
        categories=query.categories,
        wine_style=query.wine_style,
        beer_style=query.beer_style,
        potato_form=query.potato_form,
        slug=query.bread_slug,
        ids=[item.get("hub_offer_id") for item in matched if item.get("hub_offer_id")],
        dishes=query.dishes,
    )
    context = describe_context(query, matched, bread_name=bread_name, raw_text=query_text)
    exact_state = _exact_evaluation_state(session, query_text, cards) if settings.gigio_pairing_refs_enabled else "none"
    if not matched:
        wine_only = set(query.categories) <= {"vinhos"} and not ({"queijos", "azeites", "frios", "cervejas", "batatas"} & set(query.categories))
        generic = {"href": "/acompanhar", "label": GENERIC_CTA, "kind": "vitrine"}
        return {
            "available": False,
            "reason": NO_MATCH_NOTICE,
            "items": [],
            "cta": None if specialized_applied and wine_only else generic,
            "context": context,
            "hub_status": "no_match",
            "notice": NO_MATCH_NOTICE,
        }
    href = build_vitrine_href(query)
    label = ALTERNATIVES_CTA if exact_state == "missing" or catalog_alternatives else SUGGESTED_CTA
    found_cats = {str(item.get("category") or "") for item in matched}
    missing_wanted = [cat for cat in query.categories if cat not in found_cats]
    notice = ""
    if missing_wanted and found_cats:
        found_labels = [cat for cat in query.categories if cat in found_cats]
        notice = (
            f"Encontrei {', '.join(found_labels)} com disponibilidade verificada; "
            f"não há oferta verificada de {', '.join(missing_wanted)} neste momento."
        )
    payload = []
    for item in matched[:3]:
        payload.append(
            {
                "id": item.get("hub_offer_id") or item["id"],
                "name": item["name"],
                "category": item.get("category") or "",
                "occasion": item.get("occasion") or "",
                "why_pairs": item.get("why_pairs") or "",
                "serving_tip": item.get("serving_tip") or "",
                "href": href,
                "title": item["name"],
                "outbound_href": None if item.get("demo") else item.get("outbound_href"),
                "outbound_label": None if item.get("demo") else (item.get("outbound_label") or outbound_cta(item.get("vendor") or "mercadolivre")),
                "demo": bool(item.get("demo")),
                "price": None if item.get("demo") else item.get("price_label"),
                "price_fresh": item.get("price_fresh"),
                "related_breads": [bread["name"] for bread in item.get("related_breads") or []],
            }
        )
    return {
        "available": True,
        "story_href": href,
        "cta": {"href": href, "label": label, "kind": "vitrine"},
        "context": context,
        "hub_status": source_status,
        "notice": notice,
        "commission_note": COMMISSION_NOTE,
        "external_notice": EXTERNAL_NOTICE,
        "delivery_help": DELIVERY_HELP,
        "items": payload,
        "note": (
            "Responda primeiro à pergunta feita, com a ideia principal completa. "
            "Depois, se fizer sentido, acrescente um complemento breve ('Para completar a mesa…'). "
            "O sistema mostra o botão Ver acompanhamentos sugeridos abaixo, com a seleção desta resposta. "
            "Compra e entrega são separadas. Não invente produto, preço, prazo, safra nem combinação certificada."
            + (
                " Itens desta prévia local são demonstração, sem oferta comercial."
                if any(item.get("demo") for item in payload)
                else ""
            )
        ),
    }


def list_admin(session: Session, settings: Settings | None = None) -> dict:
    rows = session.scalars(select(AccompanimentItem).order_by(AccompanimentItem.sort_order, AccompanimentItem.created_at)).all()
    overlays = [_admin_view(session, row) for row in rows]
    hub_items = []
    hub_ok = False
    if settings is not None:
        result = marketplace_client.fetch_hub_profile_catalog(settings)
        hub_ok = bool(result.get("ok"))
        by_id = {row.hub_offer_id: row for row in rows}
        for offer in result.get("offers") or []:
            row = by_id.get(offer.id)
            hub_items.append(_hub_admin_card(session, offer, row))
    return {
        "curation_home": HUB_CURATION_HOME,
        "hub_ok": hub_ok,
        "hub_items": hub_items,
        "overlays": overlays,
        "items": overlays,
    }


def get_admin(session: Session, item_id: UUID) -> dict:
    row = session.get(AccompanimentItem, item_id)
    if row is None:
        raise NotFoundError("complemento não encontrado")
    return _admin_view(session, row)


def upsert_admin(session: Session, settings: Settings, payload: dict, item_id: UUID | None = None) -> dict:
    hub_id = sanitize_plain_text(payload.get("hub_offer_id"), limit=80)
    if not hub_id:
        raise ConfirmationError("informe o identificador do item no ActionHub")
    offer = marketplace_client.fetch_hub_offer_by_id(settings, hub_id)
    if offer is None:
        raise ConfirmationError("este item não está no perfil A Loja do ActionHub")
    row = session.get(AccompanimentItem, item_id) if item_id else None
    if item_id and row is None:
        raise NotFoundError("complemento não encontrado")
    existing = session.scalar(select(AccompanimentItem).where(AccompanimentItem.hub_offer_id == hub_id))
    if existing is not None and (row is None or existing.id != row.id):
        raise ConfirmationError("este item do Hub já tem narrativa na Loja")
    if row is None:
        row = AccompanimentItem(hub_offer_id=hub_id)
        session.add(row)
    row.hub_offer_id = hub_id
    row.occasion = sanitize_plain_text(payload.get("occasion"), limit=80)
    row.story_title = sanitize_plain_text(payload.get("story_title"), limit=160)
    row.story_lead = sanitize_plain_text(payload.get("story_lead"), limit=600)
    row.why_pairs = sanitize_plain_text(payload.get("why_pairs"), limit=400)
    row.serving_tip = sanitize_plain_text(payload.get("serving_tip"), limit=400)
    row.related_product_slugs = _slug_list(payload.get("related_product_slugs"))
    row.related_recipe_slugs = _slug_list(payload.get("related_recipe_slugs"))
    row.sort_order = max(0, int(payload.get("sort_order") or 0))
    row.published = bool(payload.get("published"))
    _apply_offer(row, offer)
    session.flush()
    return _admin_view(session, row)


def delete_admin(session: Session, item_id: UUID) -> None:
    row = session.get(AccompanimentItem, item_id)
    if row is None:
        raise NotFoundError("complemento não encontrado")
    session.delete(row)
    session.flush()


def search_hub(settings: Settings, query: str) -> dict:
    result = marketplace_client.fetch_hub_profile_catalog(settings)
    term = sanitize_plain_text(query, limit=80).casefold()
    offers = []
    for offer in result.get("offers") or []:
        haystack = " ".join([offer.id, offer.title, offer.category, offer.description]).casefold()
        if term and term not in haystack:
            continue
        offers.append(
            {
                "id": offer.id,
                "title": offer.title,
                "description": offer.description,
                "image_url": offer.image_url,
                "price_label": _price_label(offer.price_amount, offer.price_currency, offer.price_label),
                "link": offer.link,
                "link_valid": bool(offer.link),
                "source": offer.source,
                "vendor": offer.source,
                "outbound_label": outbound_cta(offer.source),
                "category": offer.category,
            }
        )
    return {
        "ok": bool(result.get("ok")),
        "error": result.get("error"),
        "curation_home": HUB_CURATION_HOME,
        "offers": offers[:12],
        "notice": (
            "A seleção de produtos é feita no ActionHub. Aqui só se anexa narrativa e pães."
            if result.get("ok")
            else "O marketplace do ActionHub não respondeu. A vitrine pública não usa cadastro local de preço ou link."
        ),
    }


def _overlay_map(session: Session) -> dict[str, AccompanimentItem]:
    try:
        rows = session.scalars(select(AccompanimentItem)).all()
    except Exception:
        return {}
    return {row.hub_offer_id: row for row in rows}


def _apply_offer(row: AccompanimentItem, offer: HubOffer) -> None:
    row.hub_source = offer.source
    row.snapshot_title = offer.title
    if offer.description:
        row.snapshot_description = offer.description
    row.snapshot_image_url = offer.image_url
    row.snapshot_price_amount = offer.price_amount
    row.snapshot_price_currency = offer.price_currency or "BRL"
    row.snapshot_link = offer.link
    row.snapshot_fetched_at = datetime.now(UTC)


def _card_from_offer(session: Session, offer: HubOffer, overlay: AccompanimentItem | None) -> dict | None:
    link = keep_official_outbound_url(offer.link)
    if not link:
        return None
    raw_title = offer.title.strip()
    title = display_offer_title(raw_title)
    if not title:
        return None
    if not offer.availability_verified:
        return None
    vendor = offer.source or "mercadolivre"
    price_label = _price_label(offer.price_amount, offer.price_currency, offer.price_label)
    slugs = overlay.related_product_slugs if overlay else []
    recipe_slugs = overlay.related_recipe_slugs if overlay else []
    breads = _published_breads(session, slugs)
    recipes = _published_recipes(session, recipe_slugs)
    category = normalize_category(offer.category)
    occasion = ""
    overlay_occasion = overlay.occasion.strip() if overlay and overlay.occasion.strip() else ""
    if overlay_occasion and overlay_occasion.casefold() != "mesa de fim de tarde":
        occasion = overlay_occasion
    else:
        occasion = OCCASION_BY_CATEGORY.get(category or offer.category, category or offer.category or "Sugestões")
    story_title = overlay.story_title.strip() if overlay and overlay.story_title.strip() else occasion
    if story_title.casefold() in {title.casefold(), "mesa de fim de tarde"}:
        story_title = occasion
    story_lead = overlay.story_lead.strip() if overlay else ""
    why_pairs = overlay.why_pairs.strip() if overlay else ""
    serving_tip = overlay.serving_tip.strip() if overlay else ""
    anchor = str(overlay.id) if overlay else offer.id
    return {
        "id": anchor,
        "hub_offer_id": offer.id,
        "category": category,
        "vendor": vendor,
        "marketplace": marketplace_label(vendor),
        "name": title,
        "source_title": raw_title,
        "description": sanitize_plain_text(offer.description, limit=280),
        "image_url": offer.image_url,
        "occasion": occasion,
        "story_title": story_title,
        "story_lead": story_lead,
        "why_pairs": why_pairs,
        "serving_tip": serving_tip,
        "price_label": price_label,
        "price_fresh": price_label is not None,
        "price_as_of": None,
        "outbound_href": link,
        "outbound_label": outbound_cta(vendor),
        "external_notice": separate_purchase_notice(vendor),
        "story_href": f"/acompanhar#{anchor}",
        "related_product_slugs": [bread["slug"] for bread in breads],
        "related_breads": breads,
        "related_recipes": recipes,
        "demo": False,
        "commercial_enabled": True,
    }


def _card_from_preview(session: Session, raw: dict) -> dict | None:
    raw_title = sanitize_plain_text(raw.get("name"), limit=240)
    title = display_offer_title(raw_title)
    if not title:
        return None
    overlay = _overlay_map(session).get(str(raw.get("id") or ""))
    slugs = overlay.related_product_slugs if overlay else list(raw.get("related_product_slugs") or [])
    recipe_slugs = overlay.related_recipe_slugs if overlay else list(raw.get("related_recipe_slugs") or [])
    breads = _published_breads(session, slugs)
    recipes = _published_recipes(session, recipe_slugs)
    occasion = overlay.occasion.strip() if overlay and overlay.occasion.strip() else str(raw.get("occasion") or "")
    story_title = (
        overlay.story_title.strip()
        if overlay and overlay.story_title.strip()
        else str(raw.get("story_title") or occasion or "Sugestões")
    )
    if story_title.casefold() == title.casefold():
        story_title = occasion or "Sugestões"
    story_lead = overlay.story_lead.strip() if overlay else str(raw.get("story_lead") or "")
    why_pairs = overlay.why_pairs.strip() if overlay else str(raw.get("why_pairs") or "")
    serving_tip = overlay.serving_tip.strip() if overlay else str(raw.get("serving_tip") or "")
    anchor = str(overlay.id) if overlay else str(raw.get("id") or "local-demo")
    return {
        "id": anchor,
        "hub_offer_id": str(raw.get("id") or ""),
        "category": normalize_category(raw.get("category") or raw.get("occasion")),
        "vendor": "",
        "marketplace": None,
        "name": title,
        "source_title": raw_title,
        "description": sanitize_plain_text(raw.get("description"), limit=280),
        "image_url": None,
        "occasion": occasion,
        "story_title": story_title,
        "story_lead": story_lead,
        "why_pairs": why_pairs,
        "serving_tip": serving_tip,
        "price_label": None,
        "price_fresh": False,
        "price_as_of": None,
        "outbound_href": None,
        "outbound_label": None,
        "external_notice": DEMO_NOTICE,
        "story_href": f"/acompanhar#{anchor}",
        "related_product_slugs": [bread["slug"] for bread in breads],
        "related_breads": breads,
        "related_recipes": recipes,
        "demo": True,
        "commercial_enabled": False,
    }


def _hub_admin_card(session: Session, offer: HubOffer, row: AccompanimentItem | None) -> dict:
    link = keep_official_outbound_url(offer.link)
    return {
        "hub_offer_id": offer.id,
        "title": offer.title,
        "description": offer.description,
        "image_url": offer.image_url,
        "price_label": _price_label(offer.price_amount, offer.price_currency, offer.price_label),
        "link": offer.link,
        "link_valid": bool(link),
        "outbound_href": link,
        "vendor": offer.source,
        "outbound_label": outbound_cta(offer.source),
        "category": offer.category,
        "overlay": _admin_view(session, row) if row else None,
    }


def _group_stories(items: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for item in items:
        key = item.get("occasion") or "Sugestões"
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(item)
    stories = []
    for key in order:
        first = grouped[key][0]
        stories.append(
            {
                "occasion": key,
                "title": story_display_title(first),
                "lead": first.get("story_lead") or "",
                "items": grouped[key],
            }
        )
    return stories


def _published_bread_name(session: Session, slug: str) -> str | None:
    breads = _published_breads(session, [slug])
    return breads[0]["name"] if breads else None


def _published_breads(session: Session, slugs: object) -> list[dict]:
    wanted = _slug_list(slugs)
    if not wanted:
        return []
    rows = session.scalars(
        select(Product).where(
            Product.slug.in_(wanted),
            Product.editorial_status == EditorialStatus.PUBLISHED.value,
        )
    ).all()
    by_slug = {row.slug: row for row in rows}
    return [{"slug": slug, "name": by_slug[slug].name, "href": f"/paes/{slug}"} for slug in wanted if slug in by_slug]


def _published_recipes(session: Session, slugs: object) -> list[dict]:
    wanted = _slug_list(slugs)
    if not wanted:
        return []
    rows = session.scalars(
        select(WeekRecipe).where(
            WeekRecipe.slug.in_(wanted),
            WeekRecipe.editorial_status == EditorialStatus.PUBLISHED.value,
        )
    ).all()
    by_slug = {row.slug: row for row in rows}
    return [
        {"slug": slug, "title": by_slug[slug].title, "href": f"/receitas/{slug}"}
        for slug in wanted
        if slug in by_slug
    ]


def _admin_view(session: Session, row: AccompanimentItem) -> dict:
    link = keep_official_outbound_url(row.snapshot_link)
    vendor = row.hub_source or "mercadolivre"
    return {
        "id": str(row.id),
        "hub_offer_id": row.hub_offer_id,
        "hub_source": row.hub_source,
        "snapshot_title": row.snapshot_title,
        "snapshot_description": row.snapshot_description,
        "snapshot_image_url": row.snapshot_image_url,
        "snapshot_price_amount": str(row.snapshot_price_amount) if row.snapshot_price_amount is not None else None,
        "snapshot_price_currency": row.snapshot_price_currency,
        "snapshot_link": row.snapshot_link,
        "link_valid": bool(link),
        "outbound_href": link,
        "outbound_label": outbound_cta(vendor),
        "snapshot_fetched_at": row.snapshot_fetched_at.isoformat() if row.snapshot_fetched_at else None,
        "occasion": row.occasion,
        "story_title": row.story_title,
        "story_lead": row.story_lead,
        "why_pairs": row.why_pairs,
        "serving_tip": row.serving_tip,
        "related_product_slugs": _slug_list(row.related_product_slugs),
        "related_recipe_slugs": _slug_list(row.related_recipe_slugs),
        "related_breads": _published_breads(session, row.related_product_slugs),
        "sort_order": row.sort_order,
        "published": row.published,
        "publish_blocked_reason": None if link else "sem destino oficial do Hub",
        "curation_home": HUB_CURATION_HOME,
    }


def _slug_list(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        raw = [part.strip() for part in value.replace(",", " ").split()]
    elif isinstance(value, list):
        raw = [str(part).strip() for part in value]
    else:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        slug = sanitize_plain_text(item, limit=80)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    return out[:8]


def _price_label(amount: Decimal | None, currency: str, fallback: str | None) -> str | None:
    if amount is None:
        return fallback if fallback and fallback.casefold() != "consulte" else None
    if (currency or "BRL").upper() != "BRL":
        return f"{currency} {amount}"
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _empty_public(*, enabled: bool, source_status: str) -> dict:
    return {
        "enabled": enabled,
        "title": PAGE_TITLE,
        "intro": PAGE_INTRO,
        "source_status": source_status,
        "commission_note": None,
        "external_notice": None,
        "delivery_help": {"mode": "manual", "text": DELIVERY_HELP, "client_note": DELIVERY_CLIENT_NOTE},
        "preview": False,
        "demo_notice": None,
        "attribution_ready": False,
        "stories": [],
        "items": [],
        "context": inactive_context(),
    }
