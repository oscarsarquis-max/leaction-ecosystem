from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.bakery_time import bakery_today
from app.domain.customer_identity import CUSTOMER_COOKIE, _create_session
from app.domain.house_fidelity import activate_campaign
from app.domain.schedule import ensure_schedule_settings
from app.main import create_app
from app.models.products import ProductVariant
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)
from tests.test_house_fidelity_catalog import _published
from tests.test_house_fidelity_ledger import _account, _campaign, _settings
from tests.test_house_fidelity_prompt45 import _available_credit

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-45"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5078


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


def test_browser_admin_and_checkout_offer(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    get_settings.cache_clear()
    reset_engine()

    product = _published(db, units=None)
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    campaign = _campaign(db, status="draft")
    campaign.starts_at = None
    db.flush()
    activated = activate_campaign(db, _settings())
    zero = _account(db)
    zero.name = "Bia Sem Compra"
    zero.email = "bia-zero@example.com"
    credited = _account(db)
    credited.name = "Ana Com Credito"
    credited.email = "ana-credito@example.com"
    _available_credit(db, activated, credited)
    customer_token = _create_session(db, get_settings(), credited)
    ensure_schedule_settings(db)
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            _wait_health(page)
            login = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/login",
                headers={"Content-Type": "application/json"},
                data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
            )
            assert login.ok, login.text()
            csrf = login.json().get("csrf_token")
            page.goto(f"http://127.0.0.1:{PORT}/admin/fidelidade")
            page.evaluate(
                "(token) => sessionStorage.setItem('lojadepaes_admin_csrf', token)",
                csrf,
            )
            page.get_by_role("heading", name="Fidelidade da casa").wait_for()
            assert page.get_by_text("O crédito vale um pão de 500 g da vitrine").count() > 0
            assert page.get_by_text("Motivo do ajuste").count() == 0
            page.screenshot(path=EVIDENCE / "admin-lista-1440.png", full_page=True)
            page.set_viewport_size({"width": 768, "height": 900})
            page.screenshot(path=EVIDENCE / "admin-lista-768.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "admin-lista-390.png", full_page=True)
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "admin-lista-320.png", full_page=True)
            page.set_viewport_size({"width": 1440, "height": 900})
            page.get_by_role("button", name="Ver detalhes").first.click()
            page.get_by_role("button", name="Conceder crédito manualmente").wait_for()
            page.screenshot(path=EVIDENCE / "admin-detalhe-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "admin-detalhe-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "admin-detalhe-320.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.get_by_role("button", name="Conceder crédito manualmente").click()
            page.get_by_label("Por que está concedendo este crédito?").wait_for()
            page.screenshot(path=EVIDENCE / "admin-ajuste-1440.png")
            page.set_viewport_size({"width": 768, "height": 900})
            page.screenshot(path=EVIDENCE / "admin-ajuste-768.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "admin-ajuste-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "admin-ajuste-320.png")
            page.keyboard.press("Escape")
            shop = browser.new_context(viewport={"width": 1440, "height": 900})
            shop.add_cookies(
                [
                    {
                        "name": CUSTOMER_COOKIE,
                        "value": customer_token,
                        "url": f"http://127.0.0.1:{PORT}/",
                    }
                ]
            )
            offer = shop.new_page()
            today = bakery_today(get_settings())
            delta = (3 - today.isoweekday()) % 7
            bake_day = today + timedelta(days=delta)
            if bake_day <= today:
                bake_day += timedelta(days=7)
            offer.goto(f"http://127.0.0.1:{PORT}/")
            offer.evaluate(
                """([slug, variantId, day]) => {
                  localStorage.setItem(
                    "lojadepaes_selection_v1",
                    JSON.stringify([{ key: "k1", slug, variantId, quantity: 1 }]),
                  );
                  sessionStorage.setItem("lojadepaes_preferred_date", day);
                }""",
                [product.slug, str(variant.id), bake_day.isoformat()],
            )
            offer.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            offer.get_by_text("Você tem 1 crédito disponível").wait_for()
            offer.get_by_role("button", name="Usar meu crédito").wait_for()
            offer.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-oferta-1440.png")
            offer.set_viewport_size({"width": 768, "height": 900})
            offer.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-oferta-768.png")
            offer.set_viewport_size({"width": 390, "height": 844})
            offer.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-oferta-390.png")
            offer.set_viewport_size({"width": 320, "height": 720})
            offer.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-oferta-320.png")
            offer.get_by_role("button", name="Usar meu crédito").click()
            offer.get_by_text("Crédito fidelidade").wait_for()
            shop.close()
            guest = browser.new_context(viewport={"width": 1440, "height": 900})
            shop = guest.new_page()
            shop.goto(f"http://127.0.0.1:{PORT}/")
            shop.evaluate(
                """([slug, variantId]) => {
                  localStorage.setItem(
                    "lojadepaes_selection_v1",
                    JSON.stringify([{ key: "k1", slug, variantId, quantity: 1 }]),
                  );
                }""",
                [product.slug, str(variant.id)],
            )
            shop.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            shop.get_by_text("Identifique-se na peça").wait_for()
            shop.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-guest-1440.png")
            shop.set_viewport_size({"width": 390, "height": 844})
            shop.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-guest-390.png")
            shop.set_viewport_size({"width": 320, "height": 720})
            shop.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-guest-320.png")
            guest.close()
            browser.close()
            (EVIDENCE / "journey.txt").write_text(
                f"admin redesenho e oferta guest ok\nstarts_at={activated.starts_at.isoformat()}\n",
                encoding="utf-8",
            )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
