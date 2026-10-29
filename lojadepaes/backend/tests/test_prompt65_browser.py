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
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)
from tests.test_prompt59_browser import _marked_jpeg

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-65"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5095


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _section_visible(page, section_id: str) -> bool:
    return page.evaluate(
        """(id) => {
          const el = document.getElementById(id);
          if (!el) return false;
          const r = el.getBoundingClientRect();
          return r.bottom > 0 && r.top < window.innerHeight;
        }""",
        section_id,
    )


def _gigio_covers(page, selector: str) -> bool:
    return page.evaluate(
        """(sel) => {
          const gigio = document.querySelector('.gigio-launch');
          const target = document.querySelector(sel);
          if (!gigio || !target) return false;
          const g = gigio.getBoundingClientRect();
          const t = target.getBoundingClientRect();
          if (t.width < 2 || t.height < 2) return false;
          return !(g.right <= t.left || t.right <= g.left || g.bottom <= t.top || t.bottom <= g.top);
        }""",
        selector,
    )


def _home_return_href(page) -> str | None:
    return page.locator(".home-return a").first.get_attribute("href")


def _login(page) -> None:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD}),
    )
    assert login.ok, login.text()
    body = login.json()
    page.add_init_script(
        f"localStorage.setItem('lojadepaes_admin_csrf', {json.dumps(body['csrf_token'])});"
    )


def test_internal_navigation_returns_home(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    token = uuid4().hex[:8]
    slug = f"receita-65-{token}"
    product_slug = f"pao-65-{token}"
    base = create_recipe_base(db, code=f"rb-{token}", name="Massa 65")
    product = Product(
        name="Pão isolado 65",
        slug=product_slug,
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
            "title": "Torrada isolada 65",
            "summary": "Leitura de prova da navegação.",
            "featured_image_alt": "Torrada isolada",
            "ingredients": ["2 fatias de pão"],
            "steps": ["Tostar."],
            "slug": slug,
            "prep_time": "10 min",
            "yield_text": "1 porção",
        },
    )
    attach_image(db, settings, recipe.id, "test", _marked_jpeg(800, 600, (210, 170, 130), (160, 40, 40)), "Torrada isolada")
    publish_recipe(db, recipe.id, "test")
    feature_recipe(db, recipe.id, "test")
    ensure_schedule_settings(db)
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{PORT}"
    report: dict = {"destinations": [], "viewports": []}

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(25000)
            _wait_health(page)

            page.add_init_script(
                f"localStorage.setItem({json.dumps('lojadepaes_selection_v1')}, {json.dumps(json.dumps([{
                    'key': 'line-65',
                    'slug': product_slug,
                    'variantId': str(variant.id),
                    'quantity': 2,
                    'adaptation': None,
                    'custom': None,
                }]))});"
            )

            page.goto(f"{origin}/")
            page.get_by_role("link", name="Página principal").wait_for()
            assert page.get_by_role("link", name="Página principal").get_attribute("aria-current") == "page"
            assert page.locator(".home-return").count() == 0
            page.get_by_role("link", name="Ver receita").first.click()
            page.get_by_role("heading", name="Torrada isolada 65").wait_for()
            assert _home_return_href(page) == "/"
            assert page.get_by_role("link", name="Voltar à vitrine").get_attribute("href") == "/#paes"
            report["destinations"].append("home-to-recipe")

            for label, section in (
                ("Nossos pães", "paes"),
                ("Crie seu pão", "criacao"),
                ("À nossa mesa", "mural"),
                ("Biblioteca do padeiro", "biblioteca"),
            ):
                page.goto(f"{origin}/receitas/{slug}")
                page.get_by_role("heading", name="Torrada isolada 65").wait_for()
                nav_link = page.get_by_role("navigation", name="Navegação principal").get_by_role("link", name=label)
                href = nav_link.get_attribute("href")
                assert href == f"/#{section}", f"{label} href={href} url={page.url}"
                nav_link.click()
                page.wait_for_url(lambda url: url.rstrip("/").endswith(f"/#{section}") and "/receitas/" not in url)
                page.wait_for_function("id => !!document.getElementById(id)", arg=section)
                page.wait_for_function(
                    """id => {
                      const el = document.getElementById(id);
                      if (!el) return false;
                      const r = el.getBoundingClientRect();
                      return r.bottom > 0 && r.top < window.innerHeight;
                    }""",
                    arg=section,
                )
                assert page.url.endswith(f"/#{section}") or f"/#{section}" in page.url
                assert _section_visible(page, section)
                report["destinations"].append(f"recipe-menu-{section}")

            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            direct = context.new_page()
            direct.set_default_timeout(25000)
            direct.goto(f"{origin}/receitas/{slug}")
            direct.get_by_role("heading", name="Torrada isolada 65").wait_for()
            assert _home_return_href(direct) == "/"
            direct.locator(".home-return a").click()
            direct.wait_for_function("() => location.pathname === '/'")
            direct.get_by_role("heading", name="Todo pão tem uma história.").wait_for()
            report["destinations"].append("direct-return-home")
            direct.goto(f"{origin}/receitas/{slug}")
            direct.get_by_role("img", name="Loja de Pães — Boulangerie").first.click()
            direct.wait_for_function("() => location.pathname === '/'")
            report["destinations"].append("direct-logo-home")
            context.close()

            page.goto(f"{origin}/receitas/{slug}")
            assert page.locator(".header-cart-count").inner_text() == "2"
            page.locator(".home-return a").click()
            page.wait_for_function("() => location.pathname === '/'")
            assert page.locator(".header-cart-count").inner_text() == "2"
            report["destinations"].append("cart-preserved")

            page.goto(f"{origin}/paes/{product_slug}")
            page.get_by_role("heading", name="Pão isolado 65").wait_for()
            assert _home_return_href(page) == "/"
            page.goto(f"{origin}/receitas")
            page.get_by_role("heading", name="Receitas").wait_for()
            assert _home_return_href(page) == "/"
            page.goto(f"{origin}/pedido/novo")
            page.get_by_role("heading", name="Revisar e pedir").wait_for()
            assert _home_return_href(page) == "/"
            page.goto(f"{origin}/receitas/nao-existe-65")
            page.get_by_role("alert").wait_for()
            assert _home_return_href(page) == "/"
            page.goto(f"{origin}/ativar/token-inexistente")
            page.get_by_role("heading", name="Defina sua senha").wait_for()
            assert _home_return_href(page) == "/"
            report["destinations"].extend(["product", "archive", "checkout", "recipe-404", "activate"])

            for width, height, tag in ((1440, 1100, "1440"), (768, 1024, "768"), (390, 844, "390"), (320, 720, "320")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(f"{origin}/receitas/{slug}")
                page.get_by_role("heading", name="Torrada isolada 65").wait_for()
                assert page.locator(".home-return a").is_visible()
                assert _gigio_covers(page, ".home-return a") is False
                if width <= 768:
                    page.get_by_role("button", name="Menu").click()
                    page.get_by_role("link", name="Nossos pães").click()
                    page.wait_for_function("() => document.getElementById('paes')")
                    assert _section_visible(page, "paes")
                    assert page.get_by_role("button", name="Menu").is_visible()
                page.screenshot(path=EVIDENCE / f"recipe-{tag}.png")
                report["viewports"].append(tag)

            page.set_viewport_size({"width": 1440, "height": 1100})
            page.goto(f"{origin}/receitas/{slug}")
            page.get_by_role("navigation", name="Navegação principal").get_by_role("link", name="Crie seu pão").focus()
            page.keyboard.press("Enter")
            page.wait_for_url(lambda url: url.rstrip("/").endswith("/#criacao") and "/receitas/" not in url)
            page.wait_for_function(
                """() => {
                  const el = document.getElementById('criacao');
                  if (!el) return false;
                  const r = el.getBoundingClientRect();
                  return r.bottom > 0 && r.top < window.innerHeight;
                }"""
            )
            assert _section_visible(page, "criacao")
            page.go_back()
            page.get_by_role("heading", name="Torrada isolada 65").wait_for()
            page.go_forward()
            page.wait_for_function("() => document.getElementById('criacao')")
            report["destinations"].append("keyboard-and-history")

            _login(page)
            page.goto(f"{origin}/admin/produtos")
            page.get_by_role("heading", name="Produtos").wait_for()
            assert _home_return_href(page) == "/"
            page.goto(f"{origin}/admin/produtos/receitas/nova")
            page.get_by_label("Título da receita").wait_for()
            page.get_by_label("Título da receita").fill("Rascunho isolado 65")
            dismissed = {"ok": False}

            def on_dialog(dialog) -> None:
                dismissed["ok"] = True
                dialog.dismiss()

            page.on("dialog", on_dialog)
            page.get_by_role("button", name="Voltar à lista").click()
            assert dismissed["ok"] is True
            assert page.get_by_label("Título da receita").input_value() == "Rascunho isolado 65"
            page.locator(".home-return a").click()
            page.wait_for_timeout(300)
            if "/admin/produtos/receitas/nova" not in page.url:
                pytest.fail("Página principal saiu do editor sem o aviso de alterações")
            assert page.get_by_label("Título da receita").input_value() == "Rascunho isolado 65"
            report["destinations"].append("admin-unsaved-kept")

            (EVIDENCE / "isolated.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
