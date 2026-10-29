from decimal import Decimal
from uuid import uuid4

from app.core.config import get_settings
from app.domain.accompaniments import gigio_lookup, public_catalog
from app.domain.gigio.service import _cited_links, _links_from_tool
from app.domain.gigio.tools import execute_tool
from app.domain.marketplace_client import HubOffer
from app.domain.marketplace_links import (
    keep_image_url,
    keep_official_ml_url,
    keep_official_outbound_url,
    outbound_cta,
)
from app.domain.recipe_bases import create_recipe_base
from app.models.accompaniments import AccompanimentItem
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import draft_order, priced_catalog

assert admin_client


def _bread(db: Session, name: str = "Pão de fermentação") -> Product:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Base")
    product = Product(
        name=name,
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    db.add(
        ProductVariant(
            product_id=product.id,
            display_name="500 g",
            presentation_type="weight",
            net_weight_grams=500,
            physical_units=1,
            price_cents=7000,
            currency="BRL",
            is_active=True,
        )
    )
    db.flush()
    return product


def _offer(**kwargs) -> HubOffer:
    return HubOffer(
        id=kwargs.get("id", "MLBTEST123"),
        title=kwargs.get("title", "Azeite da casa"),
        description=kwargs.get("description", "Azeite extra virgem para a mesa."),
        image_url=kwargs.get("image_url", "https://http2.mlstatic.com/demo.jpg"),
        price_amount=kwargs.get("price_amount", Decimal("42.90")),
        price_currency=kwargs.get("price_currency", "BRL"),
        price_label=kwargs.get("price_label", "R$ 42,90"),
        link=kwargs.get("link", "https://www.mercadolivre.com.br/p/MLBTEST123?attr=keep"),
        source=kwargs.get("source", "mercadolivre"),
        category=kwargs.get("category", "azeites"),
        availability_verified=kwargs.get("availability_verified", True),
        availability_checked_at=kwargs.get("availability_checked_at", "2026-10-07T21:00:00+00:00"),
    )


def _overlay(db: Session, *, offer_id: str, slug: str | None = None, title: str = "narrativa") -> AccompanimentItem:
    row = AccompanimentItem(
        hub_offer_id=offer_id,
        snapshot_title=title,
        occasion="Café da manhã",
        story_title="Café com fatias mornas",
        story_lead="Toste o pão e acrescente o azeite na hora.",
        why_pairs="A gordura do azeite equilibra a crosta.",
        serving_tip="Sirva ainda morno.",
        related_product_slugs=[slug] if slug else [],
        related_recipe_slugs=[],
        sort_order=1,
        published=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mock_hub(monkeypatch, offers: list[HubOffer], *, ok: bool = True) -> None:
    payload = {"ok": ok, "offers": offers if ok else [], "error": None if ok else "down"}
    monkeypatch.setattr("app.domain.marketplace_client.fetch_hub_profile_catalog", lambda *_a, **_k: payload)
    monkeypatch.setattr("app.domain.marketplace_client.fetch_hub_offers", lambda *_a, **_k: payload)
    monkeypatch.setattr(
        "app.domain.marketplace_client.fetch_hub_offer_by_id",
        lambda _settings, offer_id: next((item for item in offers if item.id == offer_id), None) if ok else None,
    )


def test_flags_off_hide_public_and_gigio(client: TestClient, db: Session, monkeypatch) -> None:
    bread = _bread(db)
    offer = _offer()
    _overlay(db, offer_id=offer.id, slug=bread.slug)
    _mock_hub(monkeypatch, [offer])
    ops = client.get("/api/v1/operations").json()
    assert ops["accompaniments_visible"] is False
    hidden = client.get("/api/v1/accompaniments").json()
    assert hidden["enabled"] is False
    assert hidden["items"] == []
    assert hidden["commission_note"] is None
    product = client.get(f"/api/v1/accompaniments/for-product/{bread.slug}").json()
    assert product["enabled"] is False
    tool = execute_tool(
        "lookup_accompaniments",
        {"slug": bread.slug},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert tool["available"] is False
    showcase = client.get("/api/v1/catalog/showcase")
    assert showcase.status_code == 200


def test_public_flag_on_shows_hub_item_and_keeps_attribution(
    client: TestClient, db: Session, monkeypatch
) -> None:
    bread = _bread(db)
    offer = _offer()
    row = _overlay(db, offer_id=offer.id, slug=bread.slug)
    _mock_hub(monkeypatch, [offer])
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    payload = client.get("/api/v1/accompaniments").json()
    assert payload["enabled"] is True
    assert payload["source_status"] == "hub"
    assert payload["title"] == "Para acompanhar seu pão"
    assert payload["items"][0]["outbound_href"] == offer.link
    assert "attr=keep" in payload["items"][0]["outbound_href"]
    assert payload["items"][0]["outbound_label"] == "Ver no Mercado Livre"
    assert payload["items"][0]["why_pairs"] == row.why_pairs
    assert payload["commission_note"]
    assert client.get("/api/v1/operations").json()["accompaniments_visible"] is True
    related = client.get(f"/api/v1/accompaniments/for-product/{bread.slug}").json()
    assert related["enabled"] is True
    assert related["items"][0]["name"] == "Azeite da casa"
    get_settings.cache_clear()


def test_local_overlay_is_not_a_competing_catalog(db: Session, monkeypatch) -> None:
    _overlay(db, offer_id="ONLYLOCAL")
    _mock_hub(monkeypatch, [])
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    catalog = public_catalog(db, get_settings())
    assert catalog["enabled"] is False
    assert catalog["items"] == []
    get_settings.cache_clear()


def test_invalid_or_missing_link_is_not_an_offer(db: Session, monkeypatch) -> None:
    _mock_hub(
        monkeypatch,
        [
            _offer(id="BAD1", link="javascript:alert(1)"),
            _offer(id="BAD2", link="https://evil.example/p/1"),
            _offer(id="BAD3", link="https://lista.mercadolivre.com.br/vinho-tinto"),
        ],
    )
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    catalog = public_catalog(db, get_settings())
    assert catalog["enabled"] is False
    assert catalog["items"] == []
    assert keep_official_ml_url("https://www.mercadolivre.com.br/p/MLB1?src=hub") == (
        "https://www.mercadolivre.com.br/p/MLB1?src=hub"
    )
    assert keep_official_outbound_url("https://www.amazon.com.br/dp/B00TEST?tag=loja-20") == (
        "https://www.amazon.com.br/dp/B00TEST?tag=loja-20"
    )
    assert keep_image_url(
        "/marketplace-api/image?url=https%3A%2F%2Fhttp2.mlstatic.com%2FD_NQ_NP_1.jpg"
    ) == "https://http2.mlstatic.com/D_NQ_NP_1.jpg"
    assert keep_image_url("/marketplace-api/image?url=https%3A%2F%2Fexample.com%2Fx.jpg") is None
    get_settings.cache_clear()


def test_missing_price_is_not_invented(db: Session, monkeypatch) -> None:
    _mock_hub(
        monkeypatch,
        [_offer(price_amount=None, price_label="Consulte")],
    )
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    catalog = public_catalog(db, get_settings())
    assert catalog["items"][0]["price_label"] is None
    assert catalog["items"][0]["price_fresh"] is False
    get_settings.cache_clear()


def test_amazon_item_uses_amazon_cta(db: Session, monkeypatch) -> None:
    offer = _offer(
        id="B00VINHO1",
        title="Vinho da mesa",
        link="https://www.amazon.com.br/dp/B00VINHO1?tag=loja-20",
        source="amazon",
        category="vinhos",
    )
    _mock_hub(monkeypatch, [offer])
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    catalog = public_catalog(db, get_settings())
    item = catalog["items"][0]
    assert item["outbound_href"] == offer.link
    assert item["outbound_label"] == outbound_cta("amazon")
    assert item["marketplace"] == "Amazon"
    assert "Amazon" in item["external_notice"]
    assert item["occasion"] == "Vinhos"
    get_settings.cache_clear()


def test_hub_failure_does_not_break_shop_or_checkout(client: TestClient, db: Session, monkeypatch) -> None:
    catalog = priced_catalog(db)
    _overlay(db, offer_id="MLBFAIL")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_MARKETPLACE_URL", "http://127.0.0.1:9/api/marketplace")
    get_settings.cache_clear()

    def _boom(*_a, **_k):
        raise TimeoutError("slow hub")

    monkeypatch.setattr("app.domain.marketplace_client.fetch_hub_profile_catalog", _boom)
    vitrine = client.get("/api/v1/accompaniments")
    assert vitrine.status_code == 200
    assert vitrine.json()["enabled"] is False
    assert vitrine.json()["source_status"] == "unavailable"
    assert vitrine.json()["items"] == []
    assert client.get("/api/v1/catalog/showcase").status_code == 200
    assert client.get("/api/v1/operations").status_code == 200
    assert client.get("/api/v1/operations").json()["accompaniments_visible"] is False
    order = draft_order(db, catalog)
    assert order.public_reference.startswith("LP")
    get_settings.cache_clear()


def test_draft_product_stays_hidden_and_hub_item_without_overlay_still_shows(db: Session, monkeypatch) -> None:
    draft_bread = _bread(db)
    draft_bread.editorial_status = EditorialStatus.DRAFT.value
    db.commit()
    offer = _offer(id="MLBGELEIA", title="Geleia")
    _overlay(db, offer_id=offer.id, slug=draft_bread.slug)
    _mock_hub(monkeypatch, [offer])
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    catalog = public_catalog(db, get_settings())
    names = [item["name"] for item in catalog["items"]]
    assert "Geleia" in names
    geleia = next(item for item in catalog["items"] if item["hub_offer_id"] == offer.id)
    assert geleia["related_breads"] == []
    get_settings.cache_clear()


def test_gigio_tool_uses_hub_curation_only_when_flag_on(db: Session, monkeypatch) -> None:
    bread = _bread(db)
    offer = _offer()
    row = _overlay(db, offer_id=offer.id, slug=bread.slug)
    _mock_hub(monkeypatch, [offer])
    off = execute_tool(
        "lookup_accompaniments",
        {"slug": bread.slug},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert off["available"] is False
    monkeypatch.setenv("LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    on = execute_tool(
        "lookup_accompaniments",
        {"slug": bread.slug},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert on["available"] is True
    assert on["items"][0]["outbound_href"] == offer.link
    assert on["cta"]["href"].startswith("/acompanhar")
    assert on["items"][0]["href"].startswith("/acompanhar")
    assert bread.slug in on["cta"]["href"]
    links = _links_from_tool(on)
    cited = _cited_links(f"Sirva com {offer.title} em {on['cta']['href']}", links)
    assert any(item["href"].startswith("/acompanhar") for item in cited)
    get_settings.cache_clear()


def test_gigio_generic_question_does_not_require_offer(db: Session) -> None:
    result = gigio_lookup(db, get_settings(), slug="", occasion="")
    assert result["available"] is False
    culinary = execute_tool(
        "lookup_products",
        {"q": "pão"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert "items" in culinary


def test_admin_overlay_stays_off_public(admin_client: TestClient, db: Session, monkeypatch) -> None:
    csrf = login(admin_client)
    offer = _offer(
        id="MLBADMIN1",
        title="Azeite buscado",
        link="https://www.mercadolivre.com.br/p/MLBADMIN1?tag=loja",
    )
    _mock_hub(monkeypatch, [offer])
    created = admin_client.post(
        "/api/v1/admin/accompaniments",
        json={"hub_offer_id": "MLBADMIN1", "occasion": "Entrada"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["outbound_href"] == offer.link
    listed = admin_client.get("/api/v1/admin/accompaniments").json()
    assert listed["curation_home"]
    assert listed["hub_items"][0]["hub_offer_id"] == "MLBADMIN1"
    assert listed["overlays"][0]["hub_offer_id"] == "MLBADMIN1"
    public = admin_client.get("/api/v1/accompaniments").json()
    assert public["enabled"] is False


def test_admin_rejects_id_outside_loja_profile(admin_client: TestClient, monkeypatch) -> None:
    csrf = login(admin_client)
    _mock_hub(monkeypatch, [_offer(id="MLBIN")])
    created = admin_client.post(
        "/api/v1/admin/accompaniments",
        json={"hub_offer_id": "MLBITLEGACY"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 422
