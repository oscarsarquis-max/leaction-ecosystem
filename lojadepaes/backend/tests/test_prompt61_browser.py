from __future__ import annotations

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
from tests.test_prompt59_browser import _composition, _marked_jpeg

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-61"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5091


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def test_home_contact_strip(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
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
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    token = uuid4().hex[:8]
    base = create_recipe_base(db, code=f"rb-{token}", name="Massa 61")
    product = Product(
        name="Pão isolado 61",
        slug=f"pao-61-{token}",
        short_description="crosta",
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
            price_cents=2490,
            currency="BRL",
            is_active=True,
        )
    )
    recipe = create_recipe(
        db,
        "test",
        {
            "title": "Receita isolada 61",
            "summary": "Regressão do cartão.",
            "featured_image_alt": "Receita isolada",
            "ingredients": ["2 fatias"],
            "steps": ["Servir."],
            "slug": f"receita-61-{token}",
        },
    )
    attach_image(db, settings, recipe.id, "test", _marked_jpeg(800, 800, (200, 180, 150), (80, 40, 40)), "Receita isolada")
    publish_recipe(db, recipe.id, "test")
    feature_recipe(db, recipe.id, "test")
    ensure_schedule_settings(db)
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(25000)
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_role("heading", name="Fale com A Loja").wait_for()
            whatsapp = page.get_by_role("link", name="Converse pelo WhatsApp")
            instagram = page.get_by_role("link", name="Acompanhe no Instagram")
            assert whatsapp.get_attribute("href") == "https://wa.me/5585999831861"
            assert instagram.get_attribute("href") == "https://www.instagram.com/loja.de.paes/"
            assert "text=" not in (whatsapp.get_attribute("href") or "")
            assert whatsapp.get_attribute("rel") == "noopener noreferrer"
            assert instagram.get_attribute("target") == "_blank"
            assert page.get_by_text("(85) 99983-1861").count() == 1
            assert page.get_by_text("@loja.de.paes").count() == 1
            page.get_by_role("button", name="Enviar solicitação").wait_for()
            card = _composition(page)
            assert card["formOpen"] is True
            assert page.locator(".home-contact").evaluate(
                "el => el.compareDocumentPosition(document.querySelector('footer')) & Node.DOCUMENT_POSITION_FOLLOWING"
            )

            for width, height, tag in ((1440, 900, "1440"), (768, 1024, "768"), (390, 844, "390"), (320, 720, "320")):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(80)
                overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")
                assert overflow is False
                for link in (whatsapp, instagram):
                    box = link.bounding_box()
                    assert box is not None
                    assert box["width"] >= 44
                    assert box["height"] >= 44
                    if width <= 390:
                        assert box["x"] >= 16
                        assert box["x"] + box["width"] <= width - 16
                page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(80)
                covered = page.evaluate(
                    """() => {
                      const g = document.querySelector('.gigio-launch')?.getBoundingClientRect();
                      const links = [...document.querySelectorAll('.home-contact a')].map(el => el.getBoundingClientRect());
                      if (!g) return false;
                      return links.some(a => !(g.right <= a.left || a.right <= g.left || g.bottom <= a.top || a.bottom <= g.top));
                    }"""
                )
                if width <= 390:
                    assert covered is False
                page.screenshot(path=EVIDENCE / f"isolated-home-{tag}.png", full_page=True)
                page.locator(".home-contact").screenshot(path=EVIDENCE / f"isolated-contact-{tag}.png")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
