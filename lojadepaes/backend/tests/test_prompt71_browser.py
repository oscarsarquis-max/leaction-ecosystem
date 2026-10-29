from __future__ import annotations

import json
import re
import threading
import time
from datetime import timedelta
from html import unescape
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.bakery_time import bakery_today
from app.domain.customer_mail import CTA_PAY, render_order_accepted_parts
from app.domain.date_request_accept import date_request_access_token
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import email_access_token
from app.main import create_app
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus
from app.models.orders import Order
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)
from tests.db_fixtures import NEW_ORDER_ADDRESS

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-71"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5101


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


def _fill_address(page) -> None:
    page.get_by_label("Rua").fill(NEW_ORDER_ADDRESS["delivery_street"])
    page.get_by_label("Número").fill(NEW_ORDER_ADDRESS["delivery_number"])
    page.get_by_label("Bairro").fill(NEW_ORDER_ADDRESS["delivery_district"])
    page.get_by_label("Cidade").fill(NEW_ORDER_ADDRESS["delivery_city"])
    page.get_by_label("Estado").select_option("CE")
    page.get_by_label("CEP").fill("60150-160")


def _cta_href(html: str) -> str:
    match = re.search(
        r'<a href="([^"]+)"[^>]*>\s*Pagar e acompanhar meu pedido\s*</a>',
        html,
    )
    assert match, "e-mail sem botão de pagamento"
    href = unescape(match.group(1))
    assert "/pedido/" in href
    assert "token=" in href
    return href


def test_email_href_shows_pay_actions_without_address(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 71")
    product = Product(
        name="Focaccia Alta isolada 71",
        slug=f"pao-71-{uuid4().hex[:8]}",
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
            order_id="hub-71-browser",
            status="PENDING",
            checkout_url="https://pay.example.test/card-71" if kwargs.get("method") == "card" else None,
            amount_cents=2490,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix71b",
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
            admin = browser.new_context(viewport={"width": 1440, "height": 1100})
            page = admin.new_page()
            page.set_default_timeout(25000)
            _wait_health(page)

            date_req = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/schedule/date-requests",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "desired_date": (bakery_today(get_settings()) + timedelta(days=10)).isoformat(),
                        "customer_name": "Ana Isolada 71",
                        "customer_email": "ana-71-iso@example.test",
                        "intended_quantity": 1,
                        "message": "focaccia sem endereço",
                        "idempotency_key": "p71-browser-date",
                        "lines": [{"variant_id": str(variant.id), "quantity": 1}],
                    }
                ),
            )
            assert date_req.ok, date_req.text()
            date_id = date_req.json()["id"]
            _login(page)
            page.goto(f"http://127.0.0.1:{PORT}/admin/pedidos")
            page.get_by_role("button", name="Avaliar e responder").click()
            page.get_by_role("button", name="Aceitar data solicitada e enviar para pagamento").click()
            page.get_by_text("Pedido formalizado e data reservada").wait_for()
            admin.close()

            db.expire_all()
            request_row = db.get(DateRequest, UUID(str(date_id)))
            order = db.get(Order, request_row.converted_order_id)
            assert order is not None
            mail = db.query(EmailOutbox).filter_by(order_id=order.id, kind="order_accepted").one()
            assert CTA_PAY in mail.body
            _subject, _text, html = render_order_accepted_parts(db, get_settings(), order)
            (EVIDENCE / "order-accepted.html").write_text(
                re.sub(r"token=[A-Za-z0-9_-]+", "token=redacted", html),
                encoding="utf-8",
            )
            href = _cta_href(html)
            assert order.public_reference in href
            old_token = date_request_access_token(get_settings(), request_row)

            phone = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
            )
            phone_page = phone.new_page()
            phone_page.set_default_timeout(25000)
            phone_page.goto(href)
            phone_page.get_by_role("button", name="Pagar com Pix").wait_for()
            phone_page.get_by_role("button", name="Pagar com cartão").wait_for()
            assert phone_page.get_by_role("button", name="Salvar endereço de entrega").is_visible()
            phone_page.screenshot(path=EVIDENCE / "email-link-pay-390.png", full_page=True)
            phone_page.get_by_role("button", name="Pagar com Pix").click()
            phone_page.get_by_text("00020126pix71b").wait_for()
            phone_page.screenshot(path=EVIDENCE / "pix-from-email-390.png", full_page=True)
            _fill_address(phone_page)
            phone_page.get_by_role("button", name="Salvar endereço de entrega").click()
            phone_page.get_by_text("Endereço de entrega salvo.").wait_for()
            phone_page.reload()
            phone_page.get_by_text("Rua das Fornadas").wait_for()
            phone_page.get_by_role("button", name="Pagar com Pix").wait_for()
            phone.close()

            narrow = browser.new_context(
                viewport={"width": 320, "height": 568},
                is_mobile=True,
                has_touch=True,
            )
            narrow_page = narrow.new_page()
            narrow_page.set_default_timeout(25000)
            narrow_page.goto(href)
            pix_btn = narrow_page.get_by_role("button", name="Pagar com Pix")
            pix_btn.wait_for()
            box = pix_btn.bounding_box()
            assert box is not None and box["width"] >= 240
            narrow_page.screenshot(path=EVIDENCE / "email-link-pay-320.png", full_page=True)
            narrow.close()

            desktop = browser.new_context(viewport={"width": 1440, "height": 1100})
            desk = desktop.new_page()
            desk.set_default_timeout(25000)
            desk.goto(href)
            desk.get_by_role("button", name="Pagar com Pix").wait_for()
            desk.screenshot(path=EVIDENCE / "email-link-pay-1440.png", full_page=True)

            old = desktop.new_page()
            old.goto(f"http://127.0.0.1:{PORT}/solicitacao/{date_id}?token={old_token}")
            old.get_by_role("link", name="Pagar com Pix").wait_for()
            old.get_by_role("link", name="Pagar com cartão").wait_for()
            old.screenshot(path=EVIDENCE / "old-link-pay-1440.png", full_page=True)

            bad = desktop.new_page()
            bad.goto(f"http://127.0.0.1:{PORT}/pedido/{order.public_reference}?token=invalido123456")
            bad.get_by_text("acesso ao pedido recusado").wait_for()
            assert bad.get_by_role("button", name="Pagar com Pix").count() == 0

            order.status = OrderStatus.CANCELLED.value
            db.commit()
            cancelled = desktop.new_page()
            cancelled.goto(href)
            cancelled.get_by_text("Este pedido foi cancelado. Não há cobrança a abrir.").wait_for()
            assert cancelled.get_by_role("button", name="Pagar com Pix").count() == 0

            order.status = OrderStatus.IN_PRODUCTION.value
            record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
            record.financial_status = FinancialStatus.PAID.value
            record.amount_paid_cents = order.total_cents
            db.commit()
            paid = desktop.new_page()
            paid.goto(href)
            paid.get_by_text("Pagamento recebido").wait_for()
            assert paid.get_by_role("button", name="Pagar com Pix").count() == 0
            desktop.close()
            browser.close()

            db.refresh(order)
            assert order.delivery_street == NEW_ORDER_ADDRESS["delivery_street"]
            assert order.total_cents == 2490
            (EVIDENCE / "isolated.json").write_text(
                json.dumps(
                    {
                        "public_reference": order.public_reference,
                        "email_cta": "/pedido/",
                        "opened_email_href": True,
                        "pay_actions_before_address": True,
                        "viewports": [320, 390, 1440],
                        "device": "emulated Chromium, not a physical phone",
                        "email_inbox": False,
                        "provider": "simulated",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
