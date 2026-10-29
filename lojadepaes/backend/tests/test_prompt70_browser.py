from __future__ import annotations

import json
import threading
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.customer_mail import CTA_PAY, DELIVERY_NEED, render_order_accepted_parts
from app.domain.date_request_accept import date_request_access_token
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import email_access_token
from app.main import create_app
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus
from app.models.orders import Order
from app.models.products import Product, ProductVariant
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)
from tests.db_fixtures import NEW_ORDER_ADDRESS

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-70"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5099


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _login(page) -> str:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD}),
    )
    assert login.ok, login.text()
    csrf = login.json()["csrf_token"]
    page.goto(f"http://127.0.0.1:{PORT}/")
    page.evaluate(
        "(token) => localStorage.setItem('lojadepaes_admin_csrf', token)",
        csrf,
    )
    return csrf


def _fill_address(page, *, postal: str = "60150-160") -> None:
    page.get_by_label("Rua").fill(NEW_ORDER_ADDRESS["delivery_street"])
    page.get_by_label("Número").fill(NEW_ORDER_ADDRESS["delivery_number"])
    page.get_by_label("Bairro").fill(NEW_ORDER_ADDRESS["delivery_district"])
    page.get_by_label("Cidade").fill(NEW_ORDER_ADDRESS["delivery_city"])
    page.get_by_label("Estado").select_option("CE")
    page.get_by_label("CEP").fill(postal)


def test_accept_email_link_and_address_save_viewports(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 70b")
    product = Product(
        name="Focaccia Alta isolada 70",
        slug=f"pao-70b-{uuid4().hex[:8]}",
        short_description="teste",
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
    db.commit()

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    get_settings.cache_clear()
    reset_engine()

    monkeypatch.setattr(
        "app.domain.storefront_orders.request_amount_checkout",
        lambda *_args, **kwargs: HubCheckoutResult(
            order_id="hub-70-browser",
            status="PENDING",
            checkout_url=None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix70b",
            pix_qr_code_base64="abc",
        ),
    )

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
            _wait_health(page)

            date_req = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/schedule/date-requests",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "desired_date": (bakery_today(get_settings()) + timedelta(days=10)).isoformat(),
                        "customer_name": "Bia Isolada 70",
                        "customer_email": "bia-70-iso@example.test",
                        "intended_quantity": 1,
                        "message": "focaccia sem endereço",
                        "idempotency_key": "p70-browser-date",
                        "lines": [{"variant_id": str(variant.id), "quantity": 1}],
                    }
                ),
            )
            assert date_req.ok, date_req.text()
            date_id = date_req.json()["id"]

            desktop_csrf = _login(page)
            page.goto(f"http://127.0.0.1:{PORT}/admin/pedidos")
            page.get_by_role("button", name="Avaliar e responder").click()
            page.get_by_role("button", name="Aceitar data solicitada e enviar para pagamento").click()
            page.get_by_text("Pedido formalizado e data reservada").wait_for()
            page.screenshot(path=EVIDENCE / "admin-accept-1440.png", full_page=True)

            detail = page.request.get(
                f"http://127.0.0.1:{PORT}/api/v1/admin/date-requests/{date_id}",
                headers={"X-CSRF-Token": desktop_csrf},
            )
            assert detail.ok, detail.text()
            order_id = detail.json()["converted_order_id"]
            db.expire_all()
            order = db.get(Order, UUID(str(order_id)))
            assert order is not None
            mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
            assert CTA_PAY in mail.body
            assert DELIVERY_NEED in mail.body
            assert f"/pedido/{order.public_reference}" in mail.body
            _subject, _text, html = render_order_accepted_parts(db, get_settings(), order)
            (EVIDENCE / "order-accepted.html").write_text(html, encoding="utf-8")
            (EVIDENCE / "order-accepted.txt").write_text(mail.body, encoding="utf-8")

            request_row = db.get(DateRequest, UUID(str(date_id)))
            old_token = date_request_access_token(get_settings(), request_row)
            order_token = email_access_token(get_settings(), order)

            tablet = browser.new_context(viewport={"width": 768, "height": 1024})
            tablet_page = tablet.new_page()
            tablet_page.set_default_timeout(25000)
            tablet_page.goto(f"http://127.0.0.1:{PORT}/solicitacao/{date_id}?token={old_token}")
            tablet_page.get_by_role("button", name="Salvar endereço de entrega").wait_for()
            tablet_page.get_by_role("link", name="Pagar com Pix").wait_for()
            _fill_address(tablet_page)
            tablet_page.get_by_role("button", name="Salvar endereço de entrega").click()
            tablet_page.get_by_text("Endereço de entrega salvo.").wait_for()
            tablet_page.reload()
            tablet_page.get_by_role("link", name="Pagar com Pix").wait_for()
            tablet_page.screenshot(path=EVIDENCE / "old-link-768.png", full_page=True)
            tablet.close()
            db.expire_all()
            db.refresh(order)
            assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]

            phone = browser.new_context(
                viewport={"width": 320, "height": 568},
                is_mobile=True,
                has_touch=True,
            )
            phone_page = phone.new_page()
            phone_page.set_default_timeout(25000)
            phone_page.goto(
                f"http://127.0.0.1:{PORT}/pedido/{order.public_reference}?token={order_token}"
            )
            phone_page.get_by_text("Rua das Fornadas").wait_for()
            assert "ainda dependem do aceite" not in phone_page.content()
            phone_page.get_by_role("button", name="Pagar com Pix").click()
            phone_page.get_by_text("00020126pix70b").wait_for()
            phone_page.screenshot(path=EVIDENCE / "pay-before-address-320.png", full_page=True)
            phone.close()

            mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
            )
            mobile_page = mobile.new_page()
            mobile_page.set_default_timeout(25000)
            mobile_page.goto(
                f"http://127.0.0.1:{PORT}/pedido/{order.public_reference}?token={order_token}"
            )
            mobile_page.get_by_text("Rua das Fornadas").wait_for()
            mobile_page.reload()
            mobile_page.get_by_text("Rua das Fornadas").wait_for()
            mobile_page.screenshot(path=EVIDENCE / "address-saved-390.png", full_page=True)
            mobile.close()

            desktop_cust = browser.new_context(viewport={"width": 1440, "height": 1100})
            cust = desktop_cust.new_page()
            cust.set_default_timeout(25000)
            cust.goto(f"http://127.0.0.1:{PORT}/pedido/{order.public_reference}?token={order_token}")
            cust.get_by_text("Rua das Fornadas").wait_for()
            cust.screenshot(path=EVIDENCE / "order-1440.png", full_page=True)

            bad = desktop_cust.new_page()
            bad.goto(f"http://127.0.0.1:{PORT}/solicitacao/{date_id}?token=invalido123456")
            bad.get_by_text("acesso à solicitação recusado").wait_for()
            desktop_cust.close()
            desktop.close()
            browser.close()
            (EVIDENCE / "isolated.json").write_text(
                json.dumps(
                    {
                        "date_request_id": date_id,
                        "order_id": str(order.id),
                        "public_reference": order.public_reference,
                        "viewports": [320, 390, 768, 1440],
                        "device": "emulated Chromium, not a physical phone",
                        "email_inbox": False,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
