from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
import uvicorn
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from sqlalchemy.orm import Session
from tests.test_gigio import PersistentToolsGateway, _published

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-57"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5087
QUESTION = "Quero comprar um pão rústico de fermentação natural. Com o que combina na hora de servir?"


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("servidor isolado do Gigio não respondeu")


def test_exact_culinary_question_in_browser(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")
    _published(db, "Pão de fermentação natural")
    db.commit()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()
    app = create_app()
    app.state.gigio_gateway = PersistentToolsGateway()
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_role("button", name="Conversar com Gigio").click()
            page.get_by_label("Mensagem para o Gigio").fill(QUESTION)
            page.get_by_role("button", name="Enviar").click()
            page.get_by_text("sugestão do Gigio", exact=False).wait_for()
            assert page.get_by_text("longa demais").count() == 0
            page.screenshot(path=EVIDENCE / "isolated-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "isolated-390.png")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
