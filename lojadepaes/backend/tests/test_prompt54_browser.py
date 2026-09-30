from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.schedule import ensure_schedule_settings
from app.main import create_app
from app.models.products import ProductIngredient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.test_custom_loaf import _wednesday
from tests.test_house_fidelity_catalog import _published

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-54"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5085


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
    for width, height, suffix in ((1440, 1100, "1440"), (768, 900, "768"), (390, 844, "390"), (320, 720, "320")):
        page.set_viewport_size({"width": width, "height": height})
        page.screenshot(path=EVIDENCE / f"{stem}-{suffix}.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1100})


def _quoted_total(root, amount: str):
    return root.locator(".selection-total p").filter(has_text=re.compile(rf"^Total {re.escape(amount)}"))


def _assert_comfortable_gutters(page) -> None:
    viewport = page.viewport_size
    assert viewport is not None
    for locator in (
        page.locator("main.checkout-page h1"),
        page.locator("main.checkout-page .checkout-form input").first,
        page.locator("main.checkout-page .bake-calendar--checkout"),
    ):
        box = locator.bounding_box()
        assert box is not None
        assert box["x"] >= 16
        assert box["x"] + box["width"] <= viewport["width"] - 16


def test_ingredients_once_and_review_quantity(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    product = _published(db, units=None)
    product.short_description = "Crosta firme e miolo aberto."
    for index, name in enumerate(["Farinha de trigo", "Água", "Levain", "Sal", "Azeite", "Mel"]):
        db.add(ProductIngredient(product_id=product.id, name=name, sort_order=index))
    ensure_schedule_settings(db)
    date = _wednesday()
    db.commit()

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORIGIN", f"http://127.0.0.1:{PORT}")
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
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(25000)
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_text("Ver ingredientes").first.click()
            full = page.get_by_text("Farinha de trigo, Água, Levain, Sal, Azeite, Mel.")
            full.wait_for()
            assert full.count() == 1
            assert page.get_by_text("Crosta firme e miolo aberto.").count() == 1
            assert page.get_by_text("Farinha de trigo, Água, Levain…").count() == 0
            _shots(page, "shelf")

            page.goto(f"http://127.0.0.1:{PORT}/paes/{product.slug}")
            page.get_by_role("heading", name="Pão da vitrine").wait_for()
            detail_list = page.get_by_text("Farinha de trigo, Água, Levain, Sal, Azeite, Mel.")
            detail_list.wait_for()
            assert detail_list.count() == 1
            _shots(page, "detail")

            detail = page.request.get(f"http://127.0.0.1:{PORT}/api/v1/catalog/products/{product.slug}").json()
            variant_id = detail["variants"][0]["id"]
            selection = [
                {
                    "key": "line-1",
                    "slug": product.slug,
                    "variantId": variant_id,
                    "quantity": 1,
                    "adaptation": {"text": "sem gergelim", "reason": "preference"},
                    "custom": None,
                }
            ]
            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.evaluate(
                """([lines, requested, contact]) => {
                  localStorage.setItem("lojadepaes_selection_v1", JSON.stringify(lines));
                  sessionStorage.setItem("lojadepaes_preferred_date", requested);
                  sessionStorage.setItem("lojadepaes_contact", JSON.stringify(contact));
                }""",
                [
                    selection,
                    date,
                    {"name": "Ana Isolada", "email": "ana-isolada@example.test"},
                ],
            )
            page.reload()
            review = page.locator("main.checkout-page")
            review.get_by_role("heading", name="Revisar e pedir").wait_for()
            qty = review.get_by_role("spinbutton", name="Quantidade")
            qty.wait_for()
            page.wait_for_function(
                "() => { const b = [...document.querySelectorAll('main.checkout-page button.primary')].find(el => el.textContent.includes('Enviar')); return b && !b.disabled; }"
            )
            review.get_by_label("Nome de quem pede").fill("Ana Isolada")
            review.get_by_label("E-mail para acompanhar o pedido").fill("ana-isolada@example.test")
            review.get_by_label("Observação (opcional)").fill("chegar depois das 16h")
            assert review.get_by_text("sem gergelim").count() >= 1
            _assert_comfortable_gutters(page)

            def delay_quote(route):
                if route.request.method == "POST" and "/storefront/quote" in route.request.url:
                    time.sleep(0.6)
                route.continue_()

            page.route("**/api/v1/storefront/quote", delay_quote)
            review.get_by_role("button", name="Aumentar quantidade").click()
            review.get_by_text("Recalculando o total…").wait_for()
            assert review.get_by_role("button", name="Enviar pedido").is_disabled()
            _quoted_total(review, "R$ 49,80").wait_for()
            page.unroute("**/api/v1/storefront/quote")

            review.get_by_role("button", name="Diminuir quantidade").click()
            _quoted_total(review, "R$ 24,90").wait_for()
            qty.fill("2")
            _quoted_total(review, "R$ 49,80").wait_for()
            assert review.get_by_label("Nome de quem pede").input_value() == "Ana Isolada"

            failed = {"done": False}

            def fail_once(route):
                if (
                    not failed["done"]
                    and route.request.method == "POST"
                    and "/storefront/quote" in route.request.url
                ):
                    failed["done"] = True
                    route.fulfill(
                        status=503,
                        content_type="application/json",
                        body='{"detail":"Nao foi possivel cotar agora"}',
                    )
                    return
                route.continue_()

            page.route("**/api/v1/storefront/quote", fail_once)
            review.get_by_role("button", name="Diminuir quantidade").click()
            review.locator(".tip").filter(has_text="Nao foi possivel cotar agora").first.wait_for()
            assert qty.input_value() == "1"
            assert review.get_by_label("Nome de quem pede").input_value() == "Ana Isolada"
            page.unroute("**/api/v1/storefront/quote")

            def credit_on_two(route):
                if route.request.method != "POST" or "/storefront/quote" not in route.request.url:
                    route.continue_()
                    return
                response = route.fetch()
                payload = json.loads(route.request.post_data or "{}")
                body = response.json()
                quantity = (payload.get("items") or [{}])[0].get("quantity", 1)
                if quantity >= 2:
                    body["discount_cents"] = 2490
                    body["total_cents"] = body["subtotal_cents"] - 2490
                    body["credit_applied"] = True
                route.fulfill(
                    status=response.status,
                    headers={"content-type": "application/json"},
                    body=json.dumps(body),
                )

            page.route("**/api/v1/storefront/quote", credit_on_two)
            review.get_by_role("button", name="Aumentar quantidade").click()
            review.get_by_text("Crédito fidelidade −R$ 24,90").wait_for()
            assert _quoted_total(review, "R$ 24,90").count() == 1
            page.unroute("**/api/v1/storefront/quote")
            page.reload()
            review = page.locator("main.checkout-page")
            review.get_by_role("spinbutton", name="Quantidade").wait_for()
            assert review.get_by_role("spinbutton", name="Quantidade").input_value() == "2"
            review.get_by_label("Nome de quem pede").wait_for()
            assert review.get_by_text("sem gergelim").count() >= 1
            _shots(page, "review")
            _assert_comfortable_gutters(page)

            created = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": date,
                        "items": [{"variant_id": variant_id, "quantity": 1}],
                        "quoted_cents": 2490,
                        "customer_name": "Pedido Persistido",
                        "customer_email": "persistido@example.test",
                        "idempotency_key": "prompt-54-order",
                    }
                ),
            )
            assert created.ok, created.text()
            order = created.json()
            page.goto(f"http://127.0.0.1:{PORT}/pedido/{order['public_reference']}?token={order['access_token']}")
            persisted = page.locator("main.checkout-page")
            persisted.get_by_role("heading", name="Acompanhar pedido").wait_for()
            assert persisted.get_by_role("spinbutton", name="Quantidade").count() == 0
            assert persisted.get_by_role("button", name="Aumentar quantidade").count() == 0
            assert persisted.get_by_text("1 un.").count() >= 1
            page.evaluate(
                "(raw) => localStorage.setItem('lojadepaes_selection_v1', raw)",
                json.dumps([{**selection[0], "quantity": 9}]),
            )
            page.reload()
            persisted = page.locator("main.checkout-page")
            persisted.get_by_text("1 un.").wait_for()
            assert persisted.locator(".selection-total").filter(has_text=re.compile(r"Total R\$ 24,90")).count() >= 1
            assert persisted.get_by_role("spinbutton", name="Quantidade").count() == 0
            _shots(page, "order")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
