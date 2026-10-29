"""Captura isolada do formulário 96B. Sem envio."""

from __future__ import annotations

import threading
import time
from datetime import date
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.schedule import ensure_schedule_settings
from app.domain.schedule_closures import upsert_closure
from app.main import create_app
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-96b" / "captures"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5096
EXPLANATION = (
    "Sugira uma data. A Loja avalia a possibilidade e responde por e-mail. "
    "Esta solicitação ainda não confirma a fornada."
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


def test_form_empty_quantity_and_derived_notice(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()
    settings = get_settings()
    ensure_schedule_settings(db)
    upsert_closure(
        db,
        settings,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 18),
        first_eligible_date=date(2026, 10, 21),
        pause_intake=False,
        internal_reason="Viagem",
        public_notice=None,
        actor_ref="admin:teste96b",
    )
    db.commit()

    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/#paes")
            page.get_by_role("heading", name="Precisa de outra data?").wait_for()
            page.get_by_text("a partir de 21 de outubro", exact=False).wait_for()
            qty = page.get_by_label("Quantidade pretendida")
            assert qty.input_value() == ""
            assert qty.get_attribute("placeholder") == "Informe quantos pães"
            assert page.get_by_text(EXPLANATION).count() == 1
            assert page.get_by_text("inclusive para hoje", exact=False).count() == 0
            assert page.get_by_text("a partir de 21 de outubro", exact=False).count() == 1
            page.screenshot(path=EVIDENCE / "isolated-form-1440.png", full_page=True)
            for width, name in ((390, "isolated-form-390.png"), (320, "isolated-form-320.png")):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(200)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
                )
                page.screenshot(path=EVIDENCE / name, full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
