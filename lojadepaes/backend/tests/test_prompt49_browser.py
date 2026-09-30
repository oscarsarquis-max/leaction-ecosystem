from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.week_recipes import create_recipe
from app.main import create_app
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-49"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5081


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def test_isolated_wide_editor(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
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

    recipe = create_recipe(
        db,
        "test",
        {
            "title": "Receita longa isolada",
            "summary": "Fixture só do Prompt 49, nunca publicada em produção.",
            "ingredients": ["200 g farinha", "1 ovo", "água"],
            "steps": ["1. Misture tudo em uma tigela funda.", "2. Sove até a massa ficar lisa.", "Asse em forno médio até dourar."],
        },
    )
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    long_method = (
        "1. Misture a farinha com a água até formar uma massa homogênea.\n\n"
        "2. Sove por dez minutos, descansando se a massa endurecer.\n\n"
        "3. Modele, deixe crescer e asse até o fundo soar oco.\n\n"
        "Não é necessário separar estes parágrafos em botões de passo."
    )

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            _wait_health(page)
            login = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/login",
                headers={"Content-Type": "application/json"},
                data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
            )
            assert login.ok
            page.goto(f"http://127.0.0.1:{PORT}/admin/produtos/receitas/{recipe.id}")
            page.get_by_role("heading", name="Editar receita").wait_for()
            page.locator("#wre-title").wait_for()
            page.wait_for_function("document.getElementById('wre-title')?.value === 'Receita longa isolada'")
            method = page.locator("#wre-method")
            method.wait_for()
            assert page.get_by_role("button", name="Adicionar passo").count() == 0
            assert page.get_by_role("button", name="Remover passo").count() == 0
            method.fill(long_method)
            page.get_by_label("Ingredientes").fill("200 g farinha\n1 ovo\nágua filtrada")
            box = method.bounding_box()
            assert box and box["height"] >= 280
            page.screenshot(path=EVIDENCE / "editor-1440.png", full_page=True)
            for width, height, name in ((768, 1024, "editor-768.png"), (390, 844, "editor-390.png"), (320, 720, "editor-320.png")):
                page.set_viewport_size({"width": width, "height": height})
                page.screenshot(path=EVIDENCE / name, full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.get_by_role("tab", name="Prévia").click()
            page.get_by_role("heading", name="Prévia do cartão").wait_for()
            page.screenshot(path=EVIDENCE / "preview-1440.png", full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
