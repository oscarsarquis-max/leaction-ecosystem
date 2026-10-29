from __future__ import annotations

import threading
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.bakery_time import bakery_today
from app.domain.recipe_bases import create_recipe_base
from app.domain.week_recipes import attach_image, create_recipe, feature_recipe, publish_recipe
from app.main import create_app
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-58"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5088


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


def _overlap(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return False
    return not (
        a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
        or a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
    )


def _assert_form_open_no_toggle(page) -> None:
    page.get_by_role("heading", name="Precisa de outra data?").wait_for()
    page.get_by_label("Data desejada").wait_for()
    assert page.get_by_role("button", name="Sugerir uma data").count() == 0
    assert page.get_by_role("button", name="Enviar solicitação").count() == 1
    assert page.locator(".bake-calendar-request form").count() == 1
    choose = page.get_by_text("Escolha um dia com o ícone de pão.")
    send = page.get_by_role("button", name="Enviar solicitação")
    if choose.count():
        assert choose.evaluate("el => el.compareDocumentPosition(document.querySelector('.bake-calendar-request'))") & 4


def test_date_request_form_always_visible(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
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
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 58")
    product = Product(
        name="Pão da casa 58",
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
    featured = create_recipe(
        db,
        "test",
        {
            "title": "Torrada isolada 58",
            "summary": "Cartão da coluna direita.",
            "featured_image_alt": "Torrada isolada",
            "ingredients": ["2 fatias de pão"],
            "steps": ["Tostar e servir."],
            "slug": "torrada-isolada-58",
        },
    )
    attach_image(db, settings, featured.id, "test", _jpeg(), "Torrada isolada")
    publish_recipe(db, featured.id, "test")
    feature_recipe(db, featured.id, "test")
    db.commit()

    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    today = bakery_today(settings).isoformat()

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Nossos pães").wait_for()
            page.get_by_text("Dia de produção aberto").wait_for()
            _assert_form_open_no_toggle(page)
            assert page.get_by_text(
                "Sugira uma data. A Loja avalia a possibilidade e responde por e-mail."
            ).count()
            assert page.get_by_text("Receita em destaque").count() > 0
            assert page.locator(".fornada-panel").count() == 0
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            band = page.evaluate(
                """() => {
                  const band = document.querySelector('.shelf-band');
                  const cal = document.querySelector('.bake-calendar--shelf');
                  const side = document.querySelector('.shelf-side');
                  const bandTop = band.getBoundingClientRect().top;
                  return {
                    align: getComputedStyle(band).alignItems,
                    calRel: cal.getBoundingClientRect().top - bandTop,
                    sideRel: side.getBoundingClientRect().top - bandTop,
                    overflowY: getComputedStyle(cal).overflowY,
                  };
                }"""
            )
            assert band["align"] == "flex-start"
            assert abs(band["calRel"] - band["sideRel"]) < 8
            assert band["overflowY"] != "scroll"
            gigio = page.get_by_role("button", name="Conversar com Gigio").bounding_box()
            send = page.get_by_role("button", name="Enviar solicitação").bounding_box()
            assert not _overlap(send, gigio)
            page.locator("#paes").screenshot(path=EVIDENCE / "isolated-1440.png")

            for width, height, name in ((768, 1024, "768"), (390, 844, "390"), (320, 720, "320")):
                page.set_viewport_size({"width": width, "height": height})
                _assert_form_open_no_toggle(page)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
                )
                send = page.get_by_role("button", name="Enviar solicitação")
                send.evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
                gigio = page.get_by_role("button", name="Conversar com Gigio").bounding_box()
                assert not _overlap(send.bounding_box(), gigio)
                field = page.get_by_label("Data desejada").bounding_box()
                assert field and field["width"] >= 180
                page.locator("#paes").screenshot(path=EVIDENCE / f"isolated-{name}.png")

            page.set_viewport_size({"width": 1440, "height": 1100})
            failed = {"used": False}

            def fail_once(route):
                if not failed["used"] and route.request.method == "POST":
                    failed["used"] = True
                    route.fulfill(
                        status=422,
                        content_type="application/json",
                        body='{"detail":"não foi possível enviar agora"}',
                    )
                    return
                route.continue_()

            page.route("**/api/v1/schedule/date-requests", fail_once)
            page.get_by_label("Data desejada").fill(today)
            page.get_by_label("Nome").fill("Bia Isolada")
            page.get_by_label("E-mail").fill("bia58@example.com")
            page.get_by_label("Quantidade pretendida").fill("2")
            page.get_by_label("Mensagem (opcional)").fill("Aniversário isolado")
            page.get_by_role("button", name="Enviar solicitação").click()
            page.get_by_role("alert").wait_for()
            assert page.get_by_label("Nome").input_value() == "Bia Isolada"
            assert page.get_by_label("Mensagem (opcional)").input_value() == "Aniversário isolado"
            page.get_by_role("button", name="Enviar solicitação").click()
            page.get_by_text("ainda não confirma", exact=False).wait_for()
            page.unroute("**/api/v1/schedule/date-requests")
            assert page.get_by_role("button", name="Enviar solicitação").is_enabled()
            db.expire_all()
            row = db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "date_request_received"))
            assert row is not None
            assert "bia58@example.com" in (row.to_address or "")
            assert row.status in {"skipped", "sent", "pending"}

            page.get_by_role("link", name="Escolher meu pão").first.click()
            page.wait_for_url("**/paes/**")
            page.get_by_role("button", name="Adicionar à seleção").click()
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_label("Data desejada").wait_for()
            assert page.get_by_text("Vamos considerar os pães já escolhidos na sua seleção.").count() == 1
            assert page.get_by_label("Quantidade pretendida").count() == 0
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
