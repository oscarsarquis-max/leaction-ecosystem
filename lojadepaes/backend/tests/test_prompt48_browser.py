from __future__ import annotations

import threading
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.recipe_bases import create_recipe_base
from app.domain.week_recipes import (
    archive_recipe,
    attach_image,
    create_recipe,
    feature_recipe,
    publish_recipe,
    unfeature_recipe,
)
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from PIL import Image
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-48"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5080


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 480), (198, 176, 140)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _payload() -> dict:
    return {
        "title": "Torrada isolada 48",
        "summary": "Só para comprovar o cartão abaixo da promoção.",
        "featured_image_alt": "Torrada isolada",
        "ingredients": ["2 fatias de pão"],
        "steps": ["Tostar e servir."],
    }


def _assert_band_top_aligned(page) -> None:
    metrics = page.evaluate(
        """() => {
          const band = document.querySelector('.shelf-band');
          const cal = document.querySelector('.bake-calendar');
          const side = document.querySelector('.shelf-side');
          const style = band ? getComputedStyle(band) : null;
          return {
            align: style ? style.alignItems : null,
            fornada: document.querySelectorAll('.fornada-panel').length,
            recipe: document.querySelectorAll('.week-recipe').length,
            calH: cal ? cal.getBoundingClientRect().height : 0,
            sideH: side ? side.getBoundingClientRect().height : 0,
            calTop: cal ? cal.getBoundingClientRect().top : 0,
            sideTop: side ? side.getBoundingClientRect().top : 0,
            overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
          };
        }"""
    )
    assert metrics["fornada"] == 0
    assert metrics["align"] == "flex-start"
    assert abs(metrics["calTop"] - metrics["sideTop"]) < 8
    assert metrics["overflowX"] is False
    return metrics


def test_isolated_regression_composition(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.skip("SPA não construída; rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 48")
    product = Product(
        name="Pão da casa",
        slug=f"pao-{uuid4().hex[:8]}",
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
    draft = create_recipe(db, "test", {**_payload(), "title": "Rascunho 48", "slug": "rascunho-48"})
    attach_image(db, settings, draft.id, "test", _jpeg(), "Rascunho")
    published = create_recipe(db, "test", {**_payload(), "title": "Publicada sem destaque", "slug": "publicada-48"})
    attach_image(db, settings, published.id, "test", _jpeg(), "Publicada")
    publish_recipe(db, published.id, "test")
    featured = create_recipe(db, "test", {**_payload(), "slug": "torrada-isolada-48"})
    attach_image(db, settings, featured.id, "test", _jpeg(), "Torrada isolada")
    publish_recipe(db, featured.id, "test")
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            _wait_health(page)

            assert page.request.get(f"http://127.0.0.1:{PORT}/api/v1/catalog/week-recipes/rascunho-48").status == 404
            assert page.request.get(f"http://127.0.0.1:{PORT}/api/v1/catalog/week-recipe").json()["recipe"] is None

            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Nossos pães").wait_for()
            page.get_by_text("Vagas nesta fornada").wait_for(state="hidden", timeout=2000)
            assert page.locator(".fornada-panel").count() == 0
            assert page.locator(".week-recipe").count() == 0
            assert page.get_by_text("Precisa de outra data?").count() > 0
            _assert_band_top_aligned(page)
            page.locator("#paes").screenshot(path=EVIDENCE / "isolado-sem-destaque-1440.png")
            for width, height, name in ((768, 900, "768"), (390, 844, "390"), (320, 720, "320")):
                page.set_viewport_size({"width": width, "height": height})
                page.locator("#paes").screenshot(path=EVIDENCE / f"isolado-sem-destaque-{name}.png")
            page.set_viewport_size({"width": 1440, "height": 1100})

            page.get_by_role("button", name="Sugerir uma data").click()
            page.get_by_label("Data desejada").wait_for()
            assert page.locator(".bake-calendar-request").count() == 1
            page.locator("#paes").screenshot(path=EVIDENCE / "isolado-data-aberta-1440.png")
            page.get_by_role("button", name="Sugerir uma data").click()

            participate = page.get_by_role("button", name="Quero participar")
            if participate.count():
                participate.click()
                page.get_by_label("Nome").wait_for()
                page.locator("#paes").screenshot(path=EVIDENCE / "isolado-fidelidade-aberta-1440.png")

            page.get_by_role("link", name="Escolher meu pão").first.click()
            page.wait_for_url("**/paes/**")
            page.goto(f"http://127.0.0.1:{PORT}/#paes")

            feature_recipe(db, featured.id, "test")
            db.commit()
            page.reload()
            page.get_by_role("heading", name="Torrada isolada 48").wait_for()
            assert page.get_by_text("Receita em destaque").count() > 0
            assert page.locator(".house-fidelity + .week-recipe").count() == 1
            assert page.locator(".fornada-panel").count() == 0
            _assert_band_top_aligned(page)
            page.locator("#paes").screenshot(path=EVIDENCE / "isolado-com-destaque-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#paes").screenshot(path=EVIDENCE / "isolado-com-destaque-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator("#paes").screenshot(path=EVIDENCE / "isolado-com-destaque-320.png")
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.get_by_role("link", name="Ver receita").click()
            page.get_by_role("heading", name="Torrada isolada 48").wait_for()
            assert page.get_by_text("Escolher meu pão").count() == 0

            unfeature_recipe(db, featured.id, "test")
            db.commit()
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Nossos pães").wait_for()
            assert page.locator(".week-recipe").count() == 0
            archive_recipe(db, featured.id, "test")
            db.commit()
            assert page.request.get(f"http://127.0.0.1:{PORT}/api/v1/catalog/week-recipes/torrada-isolada-48").status == 404
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
