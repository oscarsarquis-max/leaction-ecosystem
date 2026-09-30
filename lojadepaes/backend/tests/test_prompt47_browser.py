from __future__ import annotations

import threading
import time
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.week_recipes import attach_image, create_recipe, feature_recipe, publish_recipe
from app.main import create_app
from PIL import Image
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-47"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5079


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 480), (198, 176, 140)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health")
            if response.ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def test_isolated_recipe_composition(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.skip("SPA não construída; rode npm run build no frontend para a jornada isolada.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "false")
    get_settings.cache_clear()
    reset_engine()

    settings = get_settings()
    recipe = create_recipe(
        db,
        "test",
        {
            "title": "Torrada de teste",
            "summary": "Sugestão isolada só para comprovar o cartão e a leitura.",
            "featured_image_alt": "Torrada de teste",
            "ingredients": ["2 fatias de pão"],
            "steps": ["Tostar e servir."],
        },
    )
    attach_image(db, settings, recipe.id, "test", _jpeg(), "Torrada de teste")
    publish_recipe(db, recipe.id, "test")
    feature_recipe(db, recipe.id, "test")
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
            _wait_health(page)
            login = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/login",
                headers={"Content-Type": "application/json"},
                data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
            )
            assert login.ok
            page.goto(f"http://127.0.0.1:{PORT}/admin/produtos/receitas")
            page.get_by_role("heading", name="Receitas da semana").wait_for()
            page.screenshot(path=EVIDENCE / "admin-lista-1440.png")
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Torrada de teste").wait_for()
            page.locator(".shelf-band").screenshot(path=EVIDENCE / "home-1440.png")
            page.set_viewport_size({"width": 768, "height": 900})
            page.locator(".week-recipe").screenshot(path=EVIDENCE / "home-768.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".week-recipe").screenshot(path=EVIDENCE / "home-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator(".week-recipe").screenshot(path=EVIDENCE / "home-320.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{PORT}/receitas/torrada-de-teste")
            page.get_by_role("heading", name="Torrada de teste").wait_for()
            assert page.get_by_role("link", name="Voltar à vitrine").count() > 0
            assert page.get_by_text("Escolher meu pão").count() == 0
            page.screenshot(path=EVIDENCE / "leitura-1440.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "leitura-390.png", full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
