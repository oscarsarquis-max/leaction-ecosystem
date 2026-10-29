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

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-56"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5086


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("servidor isolado do Gigio não respondeu")


def test_gigio_launcher_and_panel_viewports(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")
    del db
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page()
            _wait_health(page)
            for width, height, suffix in ((1440, 900, "1440"), (768, 900, "768"), (390, 844, "390"), (320, 720, "320")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{PORT}/")
                launch = page.get_by_role("button", name="Conversar com Gigio")
                launch.wait_for()
                box = launch.bounding_box()
                assert box is not None
                assert box["x"] + box["width"] <= width - 8
                assert box["y"] + box["height"] <= height - 8
                page.screenshot(path=EVIDENCE / f"fechado-{suffix}.png")
                launch.click()
                page.get_by_role("heading", name="Gigio").wait_for()
                page.get_by_text("Ideias para sua mesa. Ajuda com seu pedido.").wait_for()
                page.screenshot(path=EVIDENCE / f"aberto-{suffix}.png")
                page.get_by_role("button", name="Fechar conversa").click()
                page.get_by_role("button", name="Conversar com Gigio").wait_for()
            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.set_viewport_size({"width": 390, "height": 844})
            launch = page.get_by_role("button", name="Conversar com Gigio")
            launch.wait_for()
            page.screenshot(path=EVIDENCE / "checkout-390.png")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
