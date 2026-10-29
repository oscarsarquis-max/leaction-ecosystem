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
from app.domain.week_recipes import attach_image, create_recipe, feature_recipe, publish_recipe
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-59"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5089


def _marked_jpeg(width: int, height: int, fill: tuple[int, int, int], mark: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (width, height), fill)
    draw = ImageDraw.Draw(image)
    draw.rectangle([2, 2, width - 3, height - 3], outline=mark, width=6)
    draw.rectangle([8, 8, 36, 36], fill=mark)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
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


def _composition(page) -> dict:
    return page.evaluate(
        """() => {
          const media = document.querySelector('.week-recipe-media');
          const img = document.querySelector('.week-recipe-media img');
          const search = document.querySelector('.week-recipe-search');
          const body = document.querySelector('.week-recipe-body');
          const ms = getComputedStyle(media);
          const is = getComputedStyle(img);
          const mr = media.getBoundingClientRect();
          const ir = img.getBoundingClientRect();
          const sr = search.getBoundingClientRect();
          const br = body.getBoundingClientRect();
          return {
            justify: ms.justifyContent,
            align: ms.alignItems,
            fit: is.objectFit,
            imgH: ir.height,
            leftGap: ir.left - mr.left,
            rightGap: mr.right - ir.right,
            searchGap: sr.top - br.bottom,
            bodyH: br.height,
            columns: getComputedStyle(body).gridTemplateColumns,
            overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
            formOpen: !!document.querySelector('.bake-calendar-request form'),
            fornada: document.querySelectorAll('.fornada-panel').length,
            natural: img.naturalWidth / img.naturalHeight,
            rendered: ir.width / ir.height,
          };
        }"""
    )


def _assert_card(metrics: dict, *, max_h: float) -> None:
    assert metrics["fit"] == "contain"
    assert metrics["justify"] == "center"
    assert metrics["align"] == "center"
    assert metrics["formOpen"] is True
    assert metrics["fornada"] == 0
    assert metrics["overflowX"] is False
    assert metrics["imgH"] <= max_h + 1
    stacked = " " not in str(metrics["columns"]).strip()
    if not stacked:
        assert metrics["bodyH"] <= max_h + 48
    assert abs(metrics["rendered"] - metrics["natural"]) < 0.12
    assert abs(metrics["leftGap"] - metrics["rightGap"]) < 4
    assert metrics["searchGap"] < 40


def test_featured_recipe_card_composition(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 59")
    product = Product(
        name="Pão da casa 59",
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

    recipes = {}
    for title, slug, image, feature in (
        ("Retrato isolado 59", "retrato-59", _marked_jpeg(756, 1344, (210, 170, 130), (160, 40, 40)), True),
        ("Paisagem isolada 59", "paisagem-59", _marked_jpeg(1280, 720, (200, 210, 170), (40, 80, 140)), False),
        ("Quadrada isolada 59", "quadrada-59", _marked_jpeg(800, 800, (190, 200, 180), (80, 80, 40)), False),
    ):
        recipe = create_recipe(
            db,
            "test",
            {
                "title": title,
                "summary": "Texto curto para conferir o alinhamento do cartão.",
                "featured_image_alt": title,
                "ingredients": ["2 fatias"],
                "steps": ["Servir."],
                "slug": slug,
                "prep_time": "15 min",
                "yield_text": "1 porção",
            },
        )
        attach_image(db, settings, recipe.id, "test", image, title)
        publish_recipe(db, recipe.id, "test")
        if feature:
            feature_recipe(db, recipe.id, "test")
        recipes[slug] = recipe.id
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
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Retrato isolado 59").wait_for()
            page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
            page.get_by_role("button", name="Enviar solicitação").wait_for()
            metrics = _composition(page)
            _assert_card(metrics, max_h=320)
            assert " " in metrics["columns"]
            page.locator(".week-recipe").screenshot(path=EVIDENCE / "isolated-portrait-card-1440.png")
            page.locator("#paes").screenshot(path=EVIDENCE / "isolated-1440.png")

            for width, height, name, max_h in (
                (1024, 900, "1024", 320),
                (768, 1024, "768", 320),
                (390, 844, "390", 264),
                (320, 720, "320", 264),
            ):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(250)
                _assert_card(_composition(page), max_h=max_h)
                page.locator("#paes").screenshot(path=EVIDENCE / f"isolated-{name}.png")

            page.set_viewport_size({"width": 1440, "height": 1100})
            for slug, title, shot in (
                ("paisagem-59", "Paisagem isolada 59", "isolated-landscape-card-1440.png"),
                ("quadrada-59", "Quadrada isolada 59", "isolated-square-card-1440.png"),
            ):
                feature_recipe(db, recipes[slug], "test")
                db.commit()
                page.reload()
                page.get_by_role("heading", name=title).wait_for()
                page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
                _assert_card(_composition(page), max_h=320)
                page.locator(".week-recipe").screenshot(path=EVIDENCE / shot)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
