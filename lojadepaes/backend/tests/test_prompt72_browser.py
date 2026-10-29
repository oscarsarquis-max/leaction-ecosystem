from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.orders import new_public_reference
from app.main import create_app
from app.models.enums import OrderStatus
from app.models.orders import Order
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_PASSWORD, TEST_ADMIN_USER, TEST_SESSION_SECRET

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-72"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5102


def _login(page) -> None:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD}),
    )
    assert login.ok, login.text()
    page.goto(f"http://127.0.0.1:{PORT}/")
    page.evaluate(
        "(token) => localStorage.setItem('lojadepaes_admin_csrf', token)",
        login.json()["csrf_token"],
    )


def test_admin_history_search_and_todos(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    done = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.COMPLETED.value,
        fulfillment_modality="delivery",
        customer_name="Osváldo Isolado 72",
        customer_email="osvaldo-72@example.test",
        currency="BRL",
        subtotal_cents=2490,
        delivery_fee_cents=0,
        discount_cents=0,
        total_cents=2490,
        holds_capacity=False,
        access_token_hash=uuid4().hex + uuid4().hex[:32],
        submit_idempotency_key=f"p72-hist-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
    )
    db.add(done)
    db.commit()

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    get_settings.cache_clear()
    reset_engine()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            desktop = browser.new_context(viewport={"width": 1440, "height": 1100})
            page = desktop.new_page()
            page.set_default_timeout(25000)
            deadline = time.time() + 20
            while time.time() < deadline:
                if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                    break
                time.sleep(0.2)
            _login(page)
            page.goto(f"http://127.0.0.1:{PORT}/admin/pedidos")
            page.get_by_text("Fila operacional: só vigentes.").wait_for()
            page.locator("select").first.select_option("all")
            page.get_by_role("button", name="Filtrar").click()
            page.get_by_text(done.public_reference).wait_for()
            page.get_by_text("Todos os estados acessíveis").wait_for()
            page.screenshot(path=EVIDENCE / "admin-todos-1440.png", full_page=True)
            page.get_by_label("Buscar").fill("osvaldo")
            page.get_by_role("button", name="Filtrar").click()
            page.get_by_text("Busca no histórico completo").wait_for()
            page.get_by_text(done.public_reference).wait_for()
            page.screenshot(path=EVIDENCE / "admin-search-osvaldo-1440.png", full_page=True)

            phone = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            mobile = phone.new_page()
            mobile.set_default_timeout(25000)
            _login(mobile)
            mobile.goto(f"http://127.0.0.1:{PORT}/admin/pedidos")
            mobile.get_by_label("Buscar").fill("Osváldo")
            mobile.get_by_role("button", name="Filtrar").click()
            mobile.get_by_text(done.public_reference).wait_for()
            mobile.screenshot(path=EVIDENCE / "admin-search-osvaldo-390.png", full_page=True)
            phone.close()
            desktop.close()
            browser.close()
        (EVIDENCE / "isolated.json").write_text(
            json.dumps(
                {
                    "todos_includes_completed": True,
                    "search_name_finds_history": True,
                    "viewports": [390, 1440],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
