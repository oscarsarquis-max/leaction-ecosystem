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
from app.domain.week_recipes import attach_image, create_recipe, feature_recipe, publish_recipe
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_custom_loaf import _wednesday
from tests.test_prompt59_browser import _composition, _marked_jpeg

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-60"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5090

LONG_METHOD = (
    "Despeje o azeite numa frigideira larga e aqueça em fogo médio-alto. "
    "Adicione o pão e frite até dourar o primeiro lado, sem deixar o miolo ressecar. "
    "Vire e frite o outro lado até o mesmo ponto. "
    "Esfregue o alho na superfície ainda quente, cubra com tomate maduro ralado "
    "e finalize com azeite, sal e um queijo curado em lascas. "
    "O parágrafo permanece inteiro: não vira lista nem some no celular estreito. "
    "Palavra-longa-de-verificacao-supercalifragilisticaespialidosa-para-quebra."
)


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _metrics(page) -> dict:
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const vw = window.innerWidth;
          const overflow = document.documentElement.scrollWidth > vw + 1;
          const cs = getComputedStyle(main);
          const nodes = [...main.querySelectorAll('h1,h2,p,li,img,input,textarea,label,button.primary,a.text-button,.selection-total,.bake-calendar,.week-recipe-method')];
          const flush = [];
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) continue;
            if (r.left < 15.5) flush.push({tag: el.tagName, left: Math.round(r.left), text: (el.innerText || el.alt || '').slice(0, 48)});
            if (r.right > vw - 15.5) flush.push({tag: el.tagName, right: Math.round(r.right), text: (el.innerText || el.alt || '').slice(0, 48)});
          }
          return {
            paddingLeft: cs.paddingLeft,
            paddingRight: cs.paddingRight,
            overflowX: overflow,
            flush: flush.slice(0, 8),
          };
        }"""
    )


def _overlap(page, selector: str) -> bool:
    return page.evaluate(
        """(sel) => {
          const gigio = document.querySelector('.gigio-launch');
          const nodes = document.querySelectorAll(sel);
          const el = nodes[nodes.length - 1];
          if (!gigio || !el) return false;
          const a = gigio.getBoundingClientRect();
          const b = el.getBoundingClientRect();
          if (b.width < 2 || b.height < 2) return false;
          const visible = b.bottom > 0 && b.top < window.innerHeight && b.right > 0 && b.left < window.innerWidth;
          if (!visible) return false;
          return !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
        }""",
        selector,
    )


def _assert_mobile_layout(page, *, search: str | None, action: str, check_flush: bool = True) -> dict:
    viewport = page.viewport_size
    assert viewport is not None
    measured = _metrics(page)
    if viewport["width"] <= 390:
        assert measured["overflowX"] is False, measured
        if check_flush:
            assert measured["flush"] == [], measured
            left = float(str(measured["paddingLeft"]).replace("px", "") or "0")
            right = float(str(measured["paddingRight"]).replace("px", "") or "0")
            assert left >= 16
            assert right >= 16
    if search:
        page.locator(search).evaluate("el => el.scrollIntoView({block:'end', inline:'nearest'})")
        page.wait_for_timeout(120)
        assert _overlap(page, search) is False
        page.locator(search).focus()
        page.wait_for_timeout(80)
        assert _overlap(page, search) is False
    page.locator(action).last.evaluate("el => el.scrollIntoView({block:'end', inline:'nearest'})")
    page.wait_for_timeout(120)
    assert _overlap(page, action) is False
    return _metrics(page)


def test_mobile_gutters_and_gigio_clearance(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
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
    base = create_recipe_base(db, code=f"rb-{token}", name="Massa 60")
    product = Product(
        name="Pão isolado 60",
        slug=f"pao-60-{token}",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=2490,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    recipe = create_recipe(
        db,
        "test",
        {
            "title": "Pan con Tomate isolado com título longo para quebra",
            "summary": "Uma torrada com tomate, presunto e queijo curado. Texto longo o bastante para medir o respiro no celular.",
            "featured_image_alt": "Torrada isolada",
            "ingredients": [
                "2 fatias de pão fermentado de trigo",
                "1 tomate maduro bem suculento, cortado ao meio",
                "Azeite de oliva, alho e queijo curado a gosto",
            ],
            "steps": [LONG_METHOD, "Sirva imediatamente, sem deixar esfriar na tábua."],
            "slug": f"receita-60-{token}",
            "prep_time": "15 min",
            "yield_text": "1 porção",
        },
    )
    attach_image(db, settings, recipe.id, "test", _marked_jpeg(756, 1344, (210, 170, 130), (160, 40, 40)), "Torrada isolada")
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
    report: dict = {"card": "kept-320"}

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(25000)
            _wait_health(page)

            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Pan con Tomate isolado").wait_for()
            page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
            page.get_by_role("button", name="Enviar solicitação").wait_for()
            card = _composition(page)
            assert card["fit"] == "contain"
            assert card["justify"] == "center"
            assert card["formOpen"] is True
            assert card["fornada"] == 0
            assert card["imgH"] <= 321
            assert abs(card["leftGap"] - card["rightGap"]) < 4
            page.locator(".week-recipe").screenshot(path=EVIDENCE / "isolated-card-1440.png")
            page.screenshot(path=EVIDENCE / "isolated-home-1440.png", full_page=True)

            created = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": date,
                        "items": [{"variant_id": str(variant.id), "quantity": 1}],
                        "quoted_cents": 2490,
                        "customer_name": "Pedido Isolado Sessenta",
                        "customer_email": "pedido60@example.test",
                        **NEW_ORDER_ADDRESS,
                        "idempotency_key": f"prompt-60-{token}",
                    }
                ),
            )
            assert created.ok, created.text()
            order = created.json()
            reference = order["public_reference"]
            access = order["access_token"]

            selection = [
                {
                    "key": "line-60",
                    "slug": product.slug,
                    "variantId": str(variant.id),
                    "quantity": 2,
                    "adaptation": None,
                    "custom": None,
                }
            ]

            for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (768, 1024, "768"), (1440, 1100, "1440")):
                page.set_viewport_size({"width": width, "height": height})

                page.goto(f"http://127.0.0.1:{PORT}/#paes")
                page.get_by_label("Buscar receitas").wait_for()
                page.get_by_role("button", name="Conversar com Gigio").wait_for()
                if width <= 390:
                    card_box = page.locator(".week-recipe").bounding_box()
                    assert card_box is not None
                    assert card_box["x"] >= 16
                    assert card_box["x"] + card_box["width"] <= width - 16
                    _assert_mobile_layout(page, search="#home-recipe-q", action=".recipe-search-row .primary", check_flush=False)
                page.screenshot(path=EVIDENCE / f"isolated-home-{tag}.png", full_page=True)
                page.locator(".week-recipe").screenshot(path=EVIDENCE / f"isolated-card-{tag}.png")

                page.goto(f"http://127.0.0.1:{PORT}/receitas/{recipe.slug}")
                page.get_by_role("heading", level=1).wait_for()
                page.get_by_text("O parágrafo permanece inteiro").wait_for()
                if width <= 390:
                    report[f"recipe-{tag}"] = _assert_mobile_layout(
                        page, search=None, action="main.week-recipe-page a.text-button"
                    )
                page.screenshot(path=EVIDENCE / f"isolated-recipe-{tag}.png", full_page=True)

                page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
                page.evaluate(
                    """([lines, requested, contact]) => {
                      localStorage.setItem("lojadepaes_selection_v1", JSON.stringify(lines));
                      sessionStorage.setItem("lojadepaes_preferred_date", requested);
                      sessionStorage.setItem("lojadepaes_contact", JSON.stringify(contact));
                    }""",
                    [
                        selection,
                        date,
                        {"name": "Ana Isolada", "email": "ana-isolada@example.test"},
                    ],
                )
                page.reload()
                review = page.locator("main.checkout-page")
                review.get_by_role("heading", name="Revisar e pedir").wait_for()
                qty = review.get_by_role("spinbutton", name="Quantidade")
                qty.wait_for()
                assert qty.input_value() == "2"
                review.get_by_label("Nome de quem pede").fill("Ana Isolada")
                review.get_by_label("E-mail para acompanhar o pedido").fill("ana-isolada@example.test")
                if width <= 390:
                    report[f"review-{tag}"] = _assert_mobile_layout(
                        page, search=None, action="main.checkout-page button.primary"
                    )
                page.screenshot(path=EVIDENCE / f"isolated-review-{tag}.png", full_page=True)

                page.goto(f"http://127.0.0.1:{PORT}/pedido/{reference}?token={access}")
                persisted = page.locator("main.checkout-page")
                persisted.get_by_role("heading", name="Acompanhar pedido").wait_for()
                assert persisted.get_by_role("spinbutton", name="Quantidade").count() == 0
                assert persisted.get_by_role("button", name="Aumentar quantidade").count() == 0
                if width <= 390:
                    report[f"confirm-{tag}"] = _assert_mobile_layout(
                        page, search=None, action="main.checkout-page h1"
                    )
                    persisted.locator("h1").evaluate("el => el.scrollIntoView({block:'end'})")
                    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(80)
                    assert _overlap(page, "main.checkout-page h1") is False or page.evaluate(
                        "() => document.querySelector('main.checkout-page h1').getBoundingClientRect().bottom < window.innerHeight - 16"
                    )
                page.screenshot(path=EVIDENCE / f"isolated-confirm-{tag}.png", full_page=True)

            (EVIDENCE / "isolated-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
