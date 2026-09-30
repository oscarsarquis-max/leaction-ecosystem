from __future__ import annotations

import json
import threading
import time
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
)

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-52"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5083


def _wait_health(page) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if page.request.get(f"http://127.0.0.1:{PORT}/api/v1/health").ok:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor isolado :{PORT} não respondeu health")


def _marked_jpeg(width: int, height: int, fill: tuple[int, int, int], mark: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (width, height), fill)
    draw = ImageDraw.Draw(image)
    draw.rectangle([2, 2, width - 3, height - 3], outline=mark, width=6)
    draw.rectangle([8, 8, 36, 36], fill=mark)
    draw.rectangle([width - 36, height - 36, width - 8, height - 8], fill=mark)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _login(page) -> str:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
    )
    assert login.ok, login.text()
    token = login.json()["csrf_token"]
    page.add_init_script(
        f"localStorage.setItem('lojadepaes_admin_csrf', {json.dumps(token)});"
        f"localStorage.setItem('lojadepaes_bakery_tz', 'America/Sao_Paulo');"
    )
    return token


def _publish(page, csrf: str, payload: dict, image: Path, feature: bool) -> dict:
    created = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/week-recipes",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        data=json.dumps(payload),
    )
    assert created.ok, created.text()
    body = created.json()
    upload = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/week-recipes/{body['id']}/image",
        headers={"X-CSRF-Token": csrf},
        multipart={"file": {"name": image.name, "mimeType": "image/jpeg", "buffer": image.read_bytes()}, "alt": payload["featured_image_alt"]},
    )
    assert upload.ok, upload.text()
    path = "publish-featured" if feature else "publish"
    published = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/week-recipes/{body['id']}/{path}",
        headers={"X-CSRF-Token": csrf},
    )
    assert published.ok, published.text()
    return published.json()


def _photo_box(page, selector: str) -> dict:
    return page.locator(selector).first.evaluate(
        "el => ({fit: getComputedStyle(el).objectFit, style: el.getAttribute('style'), "
        "ratio: el.naturalHeight ? el.getBoundingClientRect().width / el.getBoundingClientRect().height : 0, "
        "natural: el.naturalHeight ? el.naturalWidth / el.naturalHeight : 0})"
    )


def test_home_card_full_photo_and_search(db: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    del db
    playwright = pytest.importorskip("playwright.sync_api")
    if not (SPA / "index.html").is_file():
        pytest.skip("SPA não construída; rode npm run build no frontend para a jornada isolada.")

    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_SPA_DIR", str(SPA))
    monkeypatch.setenv("LOJADEPAES_CORS_ORIGINS", f"http://127.0.0.1:{PORT},http://127.0.0.1:5175")
    monkeypatch.setenv("LOJADEPAES_PREVIEW_PROTECTION", "false")
    monkeypatch.setenv("LOJADEPAES_HOUSE_FIDELITY_ACTIVE", "false")
    get_settings.cache_clear()
    reset_engine()

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    landscape = tmp_path / "paisagem.jpg"
    portrait = tmp_path / "retrato.jpg"
    square = tmp_path / "quadrado.jpg"
    landscape.write_bytes(_marked_jpeg(640, 360, (230, 200, 160), (180, 40, 40)))
    portrait.write_bytes(_marked_jpeg(360, 640, (200, 220, 180), (40, 80, 160)))
    square.write_bytes(_marked_jpeg(420, 420, (220, 210, 190), (20, 20, 20)))

    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(20000)
            _wait_health(page)
            csrf = _login(page)
            featured = _publish(
                page,
                csrf,
                {
                    "title": "Torrada isolada 52",
                    "summary": "Fatias com azeite e tomate da casa, sem reescrever o texto para caber no cartão.",
                    "featured_image_alt": "Torrada com cantos marcados",
                    "featured_image_caption": "Foto cadastrada da torrada.",
                    "ingredients": ["2 fatias de pão", "azeite"],
                    "method_text": "Tostar o pão e regar com azeite.",
                },
                portrait,
                True,
            )
            _publish(
                page,
                csrf,
                {
                    "title": "Pudim de pão isolado 52",
                    "summary": "Sobremesa com leite.",
                    "featured_image_alt": "Pudim",
                    "ingredients": ["pão amanhecido", "leite"],
                    "method_text": "Leve ao forno até dourar.",
                },
                landscape,
                False,
            )
            assert featured["slug"]

            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_role("heading", name="Torrada isolada 52").wait_for()
            page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
            page.get_by_text("Receita em destaque").wait_for()
            page.get_by_text("Mais ideias para sua mesa").wait_for()
            page.get_by_label("Buscar receitas").wait_for()
            box = _photo_box(page, ".week-recipe-media img")
            assert box["fit"] == "contain"
            assert box["style"] in (None, "")
            assert abs(box["ratio"] - box["natural"]) < 0.12
            columns = page.locator(".week-recipe-body").evaluate("el => getComputedStyle(el).gridTemplateColumns")
            assert " " in columns
            calendar = page.locator(".bake-calendar--shelf").bounding_box()
            assert calendar
            assert calendar["height"] < 640
            page.screenshot(path=EVIDENCE / "home-1440.png", full_page=True)

            page.set_viewport_size({"width": 768, "height": 1024})
            page.screenshot(path=EVIDENCE / "home-768.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            stacked = page.locator(".week-recipe-body").evaluate("el => getComputedStyle(el).gridTemplateColumns")
            assert " " not in stacked.strip()
            page.screenshot(path=EVIDENCE / "home-390.png", full_page=True)
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "home-320.png", full_page=True)

            page.set_viewport_size({"width": 1440, "height": 1100})
            page.get_by_placeholder("Receita ou ingrediente…").fill("wasabi")
            page.get_by_role("button", name="Buscar").click()
            page.get_by_text("Nenhuma receita encontrada.").wait_for()
            page.get_by_placeholder("Receita ou ingrediente…").fill("azeite")
            page.get_by_role("button", name="Buscar").click()
            page.get_by_role("link", name="Torrada isolada 52").wait_for()
            page.screenshot(path=EVIDENCE / "search-1440.png", full_page=True)
            page.get_by_role("link", name="Ver receita").click()
            page.get_by_role("heading", name="Torrada isolada 52").wait_for()
            hero = _photo_box(page, ".week-recipe-hero img")
            assert hero["fit"] == "contain"
            page.get_by_role("link", name="Voltar aos resultados").click()
            page.get_by_placeholder("Receita ou ingrediente…").wait_for()
            page.get_by_role("link", name="Torrada isolada 52").wait_for()
            page.goto(f"http://127.0.0.1:{PORT}/receitas")
            page.get_by_role("heading", name="Receitas").wait_for()
            page.get_by_role("link", name="Pudim de pão isolado 52").wait_for()
            page.screenshot(path=EVIDENCE / "archive-1440.png", full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
