from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.house_fidelity import activate_campaign
from app.domain.house_fidelity_ledger import reconcile_order
from app.domain.schedule import ensure_schedule_settings
from app.main import create_app
from app.models.customers import CustomerAccount
from app.models.email_outbox import EmailOutbox
from app.models.products import ProductVariant
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_house_fidelity_catalog import _published
from tests.test_house_fidelity_ledger import (
    _account,
    _campaign,
    _close,
    _order,
    _pay,
    _settings,
)

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-44"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5077


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


def test_browser_fidelity_journey(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", "test-customer-identity-secret-32c")
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", "test-admin-session-secret-32chars")
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    get_settings.cache_clear()
    reset_engine()

    variant_product = _published(db, units=None)
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == variant_product.id))
    campaign = _campaign(db, status="draft")
    campaign.starts_at = None
    db.flush()
    activated = activate_campaign(db, _settings())
    account = _account(db)
    for _ in range(4):
        order = _order(db, account, activated, variant)
        _pay(db, order)
        _close(db, order)
        reconcile_order(db, _settings(), order)
    ensure_schedule_settings(db)
    db.commit()

    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    log = []

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/#fidelidade")
            page.get_by_role("button", name="Quero participar").click()
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "cadastro-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "cadastro-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "cadastro-320.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.get_by_label("Nome").fill("Ana Isolada")
            page.get_by_label("E-mail").fill("ana-isolada@example.com")
            page.get_by_label("CPF").fill("390.533.447-05")
            page.get_by_role("button", name="Enviar cadastro").click()
            page.get_by_text("Código de verificação").wait_for()
            assert page.get_by_text("Cadastro concluído").count() == 0
            mail = db.query(EmailOutbox).filter_by(to_address="ana-isolada@example.com").first()
            assert mail is not None
            import re

            code = re.search(r"é (\d{6})", mail.body).group(1)
            page.get_by_label("Código de verificação").fill("000000")
            page.get_by_role("button", name="Confirmar código").click()
            page.get_by_role("alert").wait_for()
            page.get_by_label("Código de verificação").fill(code)
            page.get_by_role("button", name="Confirmar código").click()
            page.get_by_text("Ana Isolada").wait_for()
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "saldo-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "saldo-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "saldo-320.png")
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "home-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "home-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "home-320.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.evaluate(
                """([slug, variantId]) => {
                  localStorage.setItem(
                    "lojadepaes_selection_v1",
                    JSON.stringify([{ key: "k1", slug, variantId, quantity: 1 }]),
                  );
                }""",
                [variant_product.slug, str(variant.id)],
            )
            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.get_by_text("Fidelidade da casa").wait_for()
            page.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator(".house-fidelity-checkout").screenshot(path=EVIDENCE / "checkout-320.png")
            db.expire_all()
            ana = db.scalar(
                select(CustomerAccount).where(CustomerAccount.email == "ana-isolada@example.com")
            )
            assert ana is not None
            for _ in range(4):
                paid = _order(db, ana, activated, variant)
                _pay(db, paid)
                _close(db, paid)
                reconcile_order(db, _settings(), paid)
            db.commit()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{PORT}/#fidelidade")
            page.get_by_role("button", name="Resgatar pão de 500 g").click()
            page.locator("legend").filter(has_text="Pão de 500 g").wait_for()
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "resgate-1440.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "resgate-390.png")
            page.set_viewport_size({"width": 320, "height": 720})
            page.locator("#fidelidade").screenshot(path=EVIDENCE / "resgate-320.png")
            guest = browser.new_context(viewport={"width": 1440, "height": 900})
            guest_page = guest.new_page()
            guest_page.goto(f"http://127.0.0.1:{PORT}/")
            guest_page.evaluate(
                """([slug, variantId]) => {
                  localStorage.setItem(
                    "lojadepaes_selection_v1",
                    JSON.stringify([{ key: "k1", slug, variantId, quantity: 1 }]),
                  );
                }""",
                [variant_product.slug, str(variant.id)],
            )
            guest_page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            guest_page.get_by_text("Identifique-se na peça").wait_for()
            guest_page.locator(".house-fidelity-checkout").screenshot(
                path=EVIDENCE / "checkout-guest-1440.png"
            )
            guest.close()
            browser.close()
            log.append("signup-verify-session-checkout-redeem ok")
            log.append(f"campaign starts_at={activated.starts_at.isoformat()}")
            log.append(f"reward variant={variant_product.slug}")
            (EVIDENCE / "journey.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
