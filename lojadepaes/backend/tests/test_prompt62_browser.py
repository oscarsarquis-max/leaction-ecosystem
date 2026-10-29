from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.domain.showcase import ensure_slots
from app.domain.week_recipes import attach_image, create_recipe, feature_recipe, publish_recipe
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_custom_loaf import _wednesday
from tests.test_prompt59_browser import _composition, _marked_jpeg

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-62"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5092


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _boxes(page) -> dict:
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const vw = window.innerWidth;
          const nodes = [...main.querySelectorAll('h1,h2,p,li,img,a,label,legend,button,input,textarea,fieldset,.eyebrow,.product-summary,.primary')];
          const flush = [];
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) continue;
            if (r.left < 15.5) flush.push({tag: el.tagName, left: Math.round(r.left), text: (el.innerText || el.alt || '').slice(0, 48)});
            if (r.right > vw - 15.5) flush.push({tag: el.tagName, right: Math.round(r.right), text: (el.innerText || el.alt || '').slice(0, 48)});
          }
          const gigio = document.querySelector('.gigio-launch');
          const action = document.querySelector('main.product-page button.primary, main.week-recipe-page a.text-button, .recipe-search-row .primary, main.checkout-page button.primary');
          const g = gigio && gigio.getBoundingClientRect();
          const a = action && action.getBoundingClientRect();
          const overlap = g && a && !(g.right <= a.left || a.right <= g.left || g.bottom <= a.top || a.bottom <= g.top);
          return {
            path: location.pathname,
            paddingLeft: getComputedStyle(main).paddingLeft,
            overflowX: document.documentElement.scrollWidth > vw + 1,
            flush: flush.slice(0, 8),
            gigioAction: Boolean(overlap),
          };
        }"""
    )


def _assert_mobile_product(page) -> dict:
    viewport = page.viewport_size
    assert viewport is not None
    measured = _boxes(page)
    assert measured["overflowX"] is False, measured
    assert measured["flush"] == [], measured
    for name in ("Nossos pães", page.locator("h1").inner_text(), "Adicionar à seleção"):
        loc = page.get_by_role("link", name="Nossos pães") if name == "Nossos pães" else page.get_by_text(name).first
        box = loc.bounding_box()
        assert box is not None, name
        assert box["x"] >= 16, (name, box)
        assert box["x"] + box["width"] <= viewport["width"] - 16, (name, box)
    photo = page.locator("main.product-page img").first
    if photo.count():
        box = photo.bounding_box()
        assert box is not None
        assert box["x"] >= 16
        assert box["x"] + box["width"] <= viewport["width"] - 16
    page.locator("main.product-page button.primary").evaluate("el => el.scrollIntoView({block:'end'})")
    page.wait_for_timeout(80)
    measured = _boxes(page)
    assert measured["gigioAction"] is False, measured
    return measured


def test_product_detail_mobile_gutters(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    token = uuid4().hex[:8]
    base = create_recipe_base(db, code=f"rb-{token}", name="Massa 62")
    products = []
    for name, slug in (
        ("Pão de Canela isolado 62", f"pao-canela-{token}"),
        ("Pão de Frutas isolado 62", f"pao-frutas-{token}"),
    ):
        product = Product(
            name=name,
            slug=slug,
            short_description="Miolo adocicado com coco e canela para medir o respiro no celular.",
            recipe_base_id=base.id,
            featured_image_alt=name,
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
        products.append(product)
    slots = ensure_slots(db)
    slots[0].product_id = products[0].id
    recipe = create_recipe(
        db,
        "test",
        {
            "title": "Receita isolada 62",
            "summary": "Cartão e leitura para regressão.",
            "featured_image_alt": "Receita isolada",
            "ingredients": ["2 fatias"],
            "steps": ["Servir."],
            "slug": f"receita-62-{token}",
        },
    )
    attach_image(db, settings, recipe.id, "test", _marked_jpeg(800, 800, (200, 180, 150), (80, 40, 40)), "Receita isolada")
    publish_recipe(db, recipe.id, "test")
    feature_recipe(db, recipe.id, "test")
    ensure_schedule_settings(db)
    date = _wednesday()
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    report: dict = {"engines": ["chromium"]}

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_default_timeout(25000)
            _wait_health(page)

            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Receita isolada 62").wait_for()
            page.get_by_role("button", name="Enviar solicitação").wait_for()
            card = _composition(page)
            assert card["formOpen"] is True
            assert card["fit"] == "contain"
            assert page.get_by_label("Buscar receitas").count() == 1

            variant_id = page.request.get(f"http://127.0.0.1:{PORT}/api/v1/catalog/products/{products[0].slug}").json()[
                "variants"
            ][0]["id"]
            order = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": date,
                        "items": [{"variant_id": variant_id, "quantity": 1}],
                        "quoted_cents": 7000,
                        "customer_name": "Pedido Isolado 62",
                        "customer_email": "pedido62@example.test",
                        **NEW_ORDER_ADDRESS,
                        "idempotency_key": f"prompt-62-{token}",
                    }
                ),
            )
            assert order.ok, order.text()
            persisted = order.json()

            for width, height, tag in (
                (390, 844, "390"),
                (320, 720, "320"),
                (375, 812, "375"),
                (430, 932, "430"),
                (768, 1024, "768"),
                (1440, 900, "1440"),
            ):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{PORT}/paes/{products[0].slug}")
                page.get_by_role("heading", name="Pão de Canela isolado 62").wait_for()
                if width <= 430:
                    report[f"canela-{tag}"] = _assert_mobile_product(page)
                else:
                    report[f"canela-{tag}"] = _boxes(page)
                    assert report[f"canela-{tag}"]["overflowX"] is False
                page.screenshot(path=EVIDENCE / f"isolated-canela-{tag}.png", full_page=True)

            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"http://127.0.0.1:{PORT}/paes/{products[1].slug}")
            page.get_by_role("heading", name="Pão de Frutas isolado 62").wait_for()
            report["frutas-390"] = _assert_mobile_product(page)
            page.screenshot(path=EVIDENCE / "isolated-other-390.png", full_page=True)

            page.goto(f"http://127.0.0.1:{PORT}/receitas/{recipe.slug}")
            page.get_by_role("heading", name="Receita isolada 62").wait_for()
            report["recipe-390"] = _boxes(page)
            assert report["recipe-390"]["flush"] == []

            page.goto(f"http://127.0.0.1:{PORT}/receitas")
            page.get_by_role("heading", name="Receitas").wait_for()
            report["archive-390"] = _boxes(page)
            assert report["archive-390"]["overflowX"] is False

            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.get_by_role("heading", name="Revisar e pedir").wait_for()
            report["review-390"] = _boxes(page)
            assert report["review-390"]["overflowX"] is False

            page.goto(
                f"http://127.0.0.1:{PORT}/pedido/{persisted['public_reference']}?token={persisted['access_token']}"
            )
            page.get_by_role("heading", name="Acompanhar pedido").wait_for()
            report["confirm-390"] = _boxes(page)
            assert page.get_by_role("spinbutton", name="Quantidade").count() == 0
            page.screenshot(path=EVIDENCE / "isolated-confirm-390.png", full_page=True)

            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_label("Data desejada").wait_for()
            assert page.get_by_role("button", name="Enviar solicitação").count() == 1
            report["home-390"] = _boxes(page)
            assert report["home-390"]["overflowX"] is False
            page.screenshot(path=EVIDENCE / "isolated-home-390.png", full_page=True)
            browser.close()

            webkit_name = "webkit"
            if hasattr(api, webkit_name):
                try:
                    webkit = api.webkit.launch()
                except Exception as exc:
                    report["webkit"] = f"unavailable:{exc.__class__.__name__}"
                else:
                    report["engines"].append("webkit")
                    wpage = webkit.new_page(viewport={"width": 390, "height": 844})
                    wpage.goto(f"http://127.0.0.1:{PORT}/paes/{products[0].slug}")
                    wpage.get_by_role("heading", name="Pão de Canela isolado 62").wait_for()
                    report["webkit-canela-390"] = _assert_mobile_product(wpage)
                    wpage.screenshot(path=EVIDENCE / "isolated-canela-webkit-390.png", full_page=True)
                    webkit.close()
                    report["webkit"] = "playwright-webkit emulated iPhone-width 390; not a physical iPhone or Safari"

        (EVIDENCE / "isolated-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
