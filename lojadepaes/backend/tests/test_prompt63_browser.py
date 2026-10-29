from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.custom_loaf import ensure_assistant_choices
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import ensure_schedule_settings
from app.domain.showcase import ensure_slots
from app.main import create_app
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant, ShowcaseSlot
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_custom_loaf import _wednesday

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-63"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5093


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _production_labels(page, root: str) -> list[str]:
    return page.evaluate(
        """(sel) => {
          const scope = document.querySelector(sel) || document;
          return [...scope.querySelectorAll('.bake-day')]
            .filter((el) => el.querySelector('svg'))
            .map((el) => el.getAttribute('aria-label') || '')
            .filter(Boolean);
        }""",
        root,
    )


def _day_keys(labels: list[str]) -> list[str]:
    return [label.split(":")[0].strip() for label in labels]


def _gigio_covers(page, selector: str) -> bool:
    return page.evaluate(
        """(sel) => {
          const gigio = document.querySelector('.gigio-launch');
          const target = document.querySelector(sel);
          if (!gigio || !target) return false;
          const g = gigio.getBoundingClientRect();
          const t = target.getBoundingClientRect();
          return !(g.right <= t.left || t.right <= g.left || g.bottom <= t.top || t.bottom <= g.top);
        }""",
        selector,
    )


def test_delivery_only_and_creator_calendar(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.fail(f"SPA não construída em {SPA}. Rode npm run build no frontend.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ORDERS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT}")
    get_settings.cache_clear()
    reset_engine()

    token = uuid4().hex[:8]
    base = create_recipe_base(db, code=f"rb-{token}", name="Massa 63")
    product = Product(
        name="Pão isolado 63",
        slug=f"pao-63-{token}",
        short_description="crosta",
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
    ensure_assistant_choices(db)
    ensure_schedule_settings(db)
    ensure_slots(db)
    slot = db.query(ShowcaseSlot).filter_by(position=1).one()
    slot.product_id = product.id
    db.commit()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    report: dict = {"isolated": True}

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(30000)
            _wait_health(page)

            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_role("heading", name="Escolha sua fornada").wait_for()
            page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
            home_days = _production_labels(page, ".bake-calendar--shelf")
            assert home_days, "home sem marcadores de produção"
            page.screenshot(path=EVIDENCE / "isolated-home-1440.png", full_page=True)

            page.goto(f"http://127.0.0.1:{PORT}/#criacao")
            page.get_by_role("heading", name="Criador de Pães").wait_for()
            page.get_by_role("button", name=re.compile("branca", re.I)).click()
            page.get_by_role("button", name=re.compile("maturada", re.I)).click()
            page.get_by_role("button", name=re.compile("escolher os sabores", re.I)).click()
            page.get_by_role("button", name=re.compile("escolher a forma", re.I)).click()
            page.get_by_role("button", name=re.compile("pão de forma", re.I)).click()
            page.get_by_role("button", name=re.compile("combinar o encontro", re.I)).click()
            page.get_by_text(re.compile("A Loja faz somente entregas")).wait_for()
            assert page.get_by_text(re.compile("retirada é a modalidade", re.I)).count() == 0
            qty = page.get_by_role("spinbutton", name="Quantidade", exact=True)
            box = qty.bounding_box()
            assert box is not None
            assert box["height"] >= 44, box
            page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
            creator_days = _production_labels(page, ".builder-meet .bake-calendar")
            assert _day_keys(creator_days) == _day_keys(home_days), {
                "home": home_days,
                "creator": creator_days,
            }
            page.screenshot(path=EVIDENCE / "isolated-creator-1440.png", full_page=True)

            pickup = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": _wednesday(),
                        "items": [{"variant_id": str(variant.id), "quantity": 1}],
                        "quoted_cents": 2490,
                        "customer_name": "Tentativa Retirada",
                        "customer_email": "retirada63@example.test",
                        "fulfillment_modality": "pickup",
                        **NEW_ORDER_ADDRESS,
                        "idempotency_key": f"prompt-63-pickup-{token}",
                    }
                ),
            )
            assert pickup.status == 422, pickup.text()
            assert "somente entregas" in pickup.text().casefold() or "retirada" in pickup.text().casefold()

            created = page.request.post(
                f"http://127.0.0.1:{PORT}/api/v1/storefront/orders",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "requested_date": _wednesday(),
                        "items": [{"variant_id": str(variant.id), "quantity": 1}],
                        "quoted_cents": 2490,
                        "customer_name": "Pedido Isolado 63",
                        "customer_email": "pedido63@example.test",
                        **NEW_ORDER_ADDRESS,
                        "idempotency_key": f"prompt-63-{token}",
                    }
                ),
            )
            assert created.ok, created.text()
            body = created.json()
            assert body["fulfillment_modality"] == "delivery"
            assert body["total_cents"] == 2490
            report["reference"] = body["public_reference"]

            page.goto(f"http://127.0.0.1:{PORT}/paes/{product.slug}")
            page.get_by_role("button", name="Adicionar à seleção").click()
            page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
            page.get_by_text(re.compile("será entregue no endereço indicado")).wait_for()
            assert page.get_by_text(re.compile("retirada", re.I)).count() == 0
            page.get_by_label("Horário preferido para entrega").wait_for()
            page.get_by_role("group", name="Endereço de entrega").wait_for()
            page.screenshot(path=EVIDENCE / "isolated-checkout-1440.png", full_page=True)

            page.get_by_role("button", name="Conversar com Gigio").click()
            page.get_by_label("Mensagem para o Gigio").fill("Vocês fazem retirada?")
            page.get_by_role("button", name="Enviar", exact=True).click()
            page.get_by_text(re.compile("somente entregas")).wait_for()
            assert page.get_by_text(re.compile("oscar@", re.I)).count() == 0

            for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (768, 900, "768")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{PORT}/#criacao")
                page.get_by_role("button", name=re.compile("branca", re.I)).click()
                page.get_by_role("button", name=re.compile("maturada", re.I)).click()
                page.get_by_role("button", name=re.compile("escolher os sabores", re.I)).click()
                page.get_by_role("button", name=re.compile("escolher a forma", re.I)).click()
                page.get_by_role("button", name=re.compile("pão de forma", re.I)).click()
                page.get_by_role("button", name=re.compile("combinar o encontro", re.I)).click()
                page.get_by_text(re.compile("A Loja faz somente entregas")).wait_for()
                page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                note = page.locator(".builder-meet .fornada-note, .builder-meet .bake-calendar-note").last
                note.wait_for()
                assert _gigio_covers(page, ".builder-meet .fornada-note") is False
                page.screenshot(path=EVIDENCE / f"isolated-creator-{tag}.png", full_page=True)
                page.goto(f"http://127.0.0.1:{PORT}/pedido/novo")
                page.get_by_text(re.compile("será entregue no endereço indicado")).wait_for()
                page.screenshot(path=EVIDENCE / f"isolated-checkout-{tag}.png", full_page=True)

            (EVIDENCE / "isolated.txt").write_text(
                json.dumps({**report, "homeDays": home_days, "creatorDays": creator_days}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        get_settings.cache_clear()
        reset_engine()
