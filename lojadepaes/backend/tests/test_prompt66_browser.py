from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.bakery_time import bakery_today
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.main import create_app
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

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-66"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5096


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _wednesday() -> str:
    today = bakery_today(get_settings())
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta or 7)
    return day.isoformat()


def _login(page) -> str:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD}),
    )
    assert login.ok, login.text()
    csrf = login.json()["csrf_token"]
    page.evaluate(
        "(token) => localStorage.setItem('lojadepaes_admin_csrf', token)",
        csrf,
    )
    return csrf


def test_admin_list_shows_submitted_and_date_request_banner(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    ensure_schedule_settings(db)
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 66b")
    product = Product(
        name="Pão isolado 66",
        slug=f"pao-66b-{uuid4().hex[:8]}",
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
    old = Order(
        public_reference="LP66OLD24H",
        status="submitted",
        fulfillment_modality="pickup",
        customer_name="Pedido antigo",
        customer_email="antigo-66@example.test",
        currency="BRL",
        total_cents=100,
        created_at=datetime.now(UTC) - timedelta(hours=30),
    )
    db.add(old)
    db.commit()

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
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
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            page = context.new_page()
            page.set_default_timeout(25000)
            _wait_health(page)
            page.goto(f"http://127.0.0.1:{PORT}/")

            created = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": _wednesday(),
                        "items": [{"variant_id": str(variant.id), "quantity": 1}],
                        "quoted_cents": 2490,
                        "customer_name": "Ana Isolada",
                        "customer_email": "ana-66-iso@example.test",
                        **NEW_ORDER_ADDRESS,
                        "idempotency_key": "p66-browser-order",
                    }
                ),
            )
            assert created.ok, created.text()
            ref = created.json()["public_reference"]
            date_req = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/schedule/date-requests",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "desired_date": (bakery_today(get_settings()) + timedelta(days=10)).isoformat(),
                        "customer_name": "Bia Isolada",
                        "customer_email": "bia-66-iso@example.test",
                        "intended_quantity": 1,
                        "idempotency_key": "p66-browser-date",
                    }
                ),
            )
            assert date_req.ok, date_req.text()

            csrf = _login(page)
            health = page.request.get(
                f"http://127.0.0.1:{PORT}/api/v1/admin/ops/attendance-health",
                headers={"X-CSRF-Token": csrf},
            )
            assert health.ok, health.text()
            assert health.json()["hidden_submitted"] == 0
            assert health.json()["open_date_requests"] >= 1

            page.goto(f"http://127.0.0.1:{PORT}/admin/pedidos")
            page.get_by_role("heading", name="Pedidos").wait_for()
            page.get_by_text(ref).wait_for()
            page.get_by_text("LP66OLD24H").wait_for()
            page.get_by_text("Solicitação de data").first.wait_for()
            page.get_by_role("button", name="Avaliar e responder").wait_for()
            page.screenshot(path=EVIDENCE / "admin-list-1440.png", full_page=True)
            page.get_by_role("button", name="Avaliar e responder").click()
            page.get_by_text("Bia Isolada").wait_for()
            page.get_by_text("Avaliar e responder").wait_for()
            page.screenshot(path=EVIDENCE / "admin-agenda-1440.png", full_page=True)
            page.get_by_role("button", name="Voltar à fila").click()
            page.get_by_text(ref).click()
            page.get_by_text(ref).wait_for()
            page.get_by_text("Ana Isolada").wait_for()
            page.screenshot(path=EVIDENCE / "admin-detail-1440.png", full_page=True)
            evidence = {
                "reference": ref,
                "old_reference": "LP66OLD24H",
                "date_request_id": date_req.json()["id"],
                "hidden_submitted": health.json()["hidden_submitted"],
            }
            browser.close()
            (EVIDENCE / "isolated.json").write_text(
                json.dumps(evidence, indent=2),
                encoding="utf-8",
            )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
