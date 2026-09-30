from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.actionhub_client import HubCheckoutResult
from app.domain.custom_loaf import public_builder_catalog
from app.domain.schedule import ensure_schedule_settings
from app.main import create_app
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)
from tests.test_custom_loaf import _wednesday

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-53"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5084


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _shots(page, stem: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.screenshot(path=EVIDENCE / f"{stem}-1440.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=EVIDENCE / f"{stem}-390.png", full_page=True)
    page.set_viewport_size({"width": 320, "height": 720})
    page.screenshot(path=EVIDENCE / f"{stem}-320.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1100})


def test_identify_submit_admin_accept_and_pay(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    catalog = public_builder_catalog(db)
    ensure_schedule_settings(db)
    date = _wednesday()
    db.commit()
    dough = catalog["doughs"][0]
    shape = catalog["shapes"][0]
    flour = catalog["flours"][0]
    inclusion = next((item for item in catalog["ingredients"] if item.get("assistant_role") != "flour"), None)
    ingredient_ids = [flour["id"]] + ([inclusion["id"]] if inclusion else [])
    ingredient_names = [flour["name"]] + ([inclusion["name"]] if inclusion else [])

    paid = {"on": False}

    def fake_checkout(*_args, **kwargs):
        return HubCheckoutResult(
            order_id="hub-prompt53",
            status="PENDING",
            checkout_url=None,
            amount_cents=catalog["price_cents"],
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126pix-isolado-prompt53",
            pix_date_of_expiration="2026-10-08T18:00:00-03:00",
            mp_payment_id="53",
        )

    def fake_lookup(*_args, **_kwargs):
        return HubCheckoutResult(
            order_id="hub-prompt53",
            status="PAID" if paid["on"] else "PENDING",
            checkout_url=None,
            amount_cents=catalog["price_cents"],
            reused=True,
            method="pix",
            pix_qr_code="00020126pix-isolado-prompt53",
            pix_date_of_expiration="2026-10-08T18:00:00-03:00",
            mp_payment_id="53",
        )

    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", fake_checkout)
    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", fake_lookup)
    monkeypatch.setattr("app.domain.storefront_orders.cancel_amount_checkout", lambda *_a, **_k: None)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_MAIL_BACKEND", "ses")
    monkeypatch.setenv("LOJADEPAES_MAIL_FROM", "loja@lojadepaes.com.br")
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "true")
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    selection = [
        {
            "key": "custom-1",
            "slug": "pao-personalizado",
            "variantId": "",
            "quantity": 1,
            "adaptation": None,
            "custom": {
                "doughTypeId": dough["id"],
                "breadShapeId": shape["id"],
                "ingredientIds": ingredient_ids,
                "doughName": dough["name"],
                "shapeName": shape["name"],
                "ingredientNames": ingredient_names,
                "flourId": flour["id"],
                "flourName": flour["name"],
                "weightGrams": catalog["weight_grams"],
                "unitCents": catalog["price_cents"],
            },
        }
    ]
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            page = context.new_page()
            page.set_default_timeout(25000)
            _wait_health(page)
            page.add_init_script(
                f"localStorage.setItem('lojadepaes_selection_v1', {json.dumps(json.dumps(selection))});"
                f"sessionStorage.setItem('lojadepaes_preferred_date', {json.dumps(date)});"
            )
            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.get_by_role("heading", name="Revisar e pedir").wait_for()
            page.get_by_text("Usaremos este e-mail para avisar sobre a avaliação").wait_for()
            send = page.get_by_role("button", name="Enviar pedido para avaliação")
            page.wait_for_function(
                "() => { const b = document.querySelector('button.primary'); return b && !b.disabled; }"
            )
            send.click()
            page.get_by_text("Informe o nome de quem pede.").wait_for()
            _shots(page, "identify")
            page.get_by_label("Nome de quem pede").fill("Ana Isolada")
            page.get_by_label("E-mail para acompanhar o pedido").fill("ana-isolada@example.test")
            send.click()
            page.get_by_text("Aguardando avaliação da padaria").first.wait_for()
            page.get_by_role("link", name="Ver meu pedido").wait_for()
            page.get_by_role("button", name="Voltar à loja").wait_for()
            _shots(page, "confirm")
            first_url = page.url
            page.reload()
            page.get_by_text("Aguardando avaliação da padaria").first.wait_for()
            assert page.url == first_url

            login = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/login",
                headers={"Content-Type": "application/json"},
                data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
            )
            assert login.ok, login.text()
            csrf = login.json()["csrf_token"]
            listing = page.request.get(
                f"http://127.0.0.1:{PORT}/api/v1/admin/orders",
                headers={"X-CSRF-Token": csrf},
            )
            assert listing.ok, listing.text()
            items = listing.json()["items"]
            assert items
            assert items[0]["custom_awaiting"] is True
            detail = page.request.get(
                f"http://127.0.0.1:{PORT}/api/v1/admin/orders/{items[0]['id']}",
                headers={"X-CSRF-Token": csrf},
            ).json()
            kinds = {row["kind"]: row for row in detail["notifications"]}
            assert kinds["order_submitted"]["status"] in {"pending", "skipped", "failed"}
            assert kinds["order_submitted_admin"]["status"] == "skipped"
            page.evaluate(
                "(token) => localStorage.setItem('lojadepaes_admin_csrf', token)",
                csrf,
            )
            page.goto(f"http://127.0.0.1:{PORT}/admin/pedidos/{items[0]['id']}")
            page.get_by_text("Nova solicitação de pão personalizado").wait_for()
            _shots(page, "admin")
            accepted = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/orders/{items[0]['id']}/confirm",
                headers={"X-CSRF-Token": csrf},
            )
            assert accepted.ok, accepted.text()
            again = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/admin/orders/{items[0]['id']}/confirm",
                headers={"X-CSRF-Token": csrf},
            )
            assert again.ok, again.text()
            page.goto(f"http://127.0.0.1:{PORT}/pedido/{items[0]['public_reference']}")
            page.get_by_text("A Loja aceitou o pedido").wait_for()
            page.get_by_role("button", name="Pagar com Pix").wait_for()
            page.get_by_role("button", name="Pagar com cartão").wait_for()
            _shots(page, "accepted")
            page.get_by_role("button", name="Pagar com Pix").click()
            page.get_by_text("Código Pix").wait_for()
            _shots(page, "payment")
            paid["on"] = True
            page.get_by_role("button", name="Verificar pagamento").click()
            page.get_by_text("Pagamento: Pago").wait_for()
            _shots(page, "paid")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
