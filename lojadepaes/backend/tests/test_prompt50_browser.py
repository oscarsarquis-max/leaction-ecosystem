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

EVIDENCE = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-50"
SPA = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PORT = 5082


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


def _login_and_store_csrf(page) -> None:
    login = page.request.post(
        f"http://127.0.0.1:{PORT}/api/v1/admin/login",
        headers={"Content-Type": "application/json"},
        data=f'{{"username":"{TEST_ADMIN_USER}","password":"{TEST_ADMIN_PASSWORD}"}}',
    )
    assert login.ok, login.text()
    body = login.json()
    page.add_init_script(
        f"localStorage.setItem('lojadepaes_admin_csrf', {json.dumps(body['csrf_token'])});"
        f"localStorage.setItem('lojadepaes_bakery_tz', {json.dumps(body.get('bakery_timezone') or 'America/Sao_Paulo')});"
    )


def _assert_card_photo(page, selector: str, max_height: float = 340, *, fit: str = "cover") -> None:
    box = page.locator(selector).first.evaluate(
        "el => ({fit: getComputedStyle(el).objectFit, height: el.getBoundingClientRect().height, "
        "parent: el.parentElement.getBoundingClientRect().height, "
        "filled: Math.abs(el.getBoundingClientRect().width - el.parentElement.getBoundingClientRect().width) < 2})"
    )
    assert box["fit"] == fit
    if fit == "cover":
        assert box["filled"] is True
    assert box["height"] <= max_height
    if fit == "cover":
        assert box["parent"] <= max_height


def _wait_text(page, text: str) -> None:
    page.get_by_text(text, exact=False).first.wait_for()


def test_isolated_save_and_full_photo(db: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
            _login_and_store_csrf(page)
            page.goto(f"http://127.0.0.1:{PORT}/admin/produtos/receitas/nova")
            page.get_by_role("heading", name="Nova receita").wait_for()
            page.get_by_text("Nova receita · rascunho ainda não salvo").wait_for()
            page.locator("#wre-title").fill("Rascunho isolado 50")
            page.get_by_role("button", name="Salvar rascunho").first.click()
            try:
                page.get_by_role("heading", name="Editar receita").wait_for()
            except Exception:
                page.screenshot(path=EVIDENCE / "editor-save-failed.png", full_page=True)
                raise
            assert "/admin/produtos/receitas/" in page.url
            assert "nova" not in page.url
            first_url = page.url
            page.reload()
            page.locator("#wre-title").wait_for()
            page.wait_for_function("document.getElementById('wre-title')?.value === 'Rascunho isolado 50'")
            page.get_by_role("button", name="Publicar e destacar na home").first.click()
            _wait_text(page, "Ainda não dá para publicar")
            assert page.locator("#wre-title").input_value() == "Rascunho isolado 50"
            page.screenshot(path=EVIDENCE / "editor-validation-1440.png", full_page=True)

            page.locator("#wre-summary").fill("Resumo do teste isolado do Prompt 50.")
            page.locator("#wre-ingredients").fill("200 g farinha\n1 ovo")
            page.locator("#wre-method").fill("Misture e asse.\n\nNão cortar a foto.")
            page.locator("#wre-title").fill("Receita isolada 50")
            page.get_by_label("Texto alternativo da foto").fill("Foto de teste com cantos marcados")
            page.locator('input[type="file"]').set_input_files(str(landscape))
            page.get_by_role("button", name="Salvar rascunho").first.click()
            _wait_text(page, "Rascunho e foto salvos.")
            page.wait_for_function("document.querySelector('.wre-preview-frame img')?.naturalWidth > 0")
            _assert_card_photo(page, ".wre-preview-frame img")
            page.get_by_text("Ajustar enquadramento").wait_for()
            page.get_by_text("Horizontal", exact=True).wait_for()
            page.get_by_text("Vertical", exact=True).wait_for()
            page.screenshot(path=EVIDENCE / "editor-1440.png", full_page=True)
            page.get_by_role("tab", name="Prévia").click()
            page.get_by_role("heading", name="Prévia do cartão").wait_for()
            _assert_card_photo(page, ".week-recipe-media img", fit="contain")
            page.screenshot(path=EVIDENCE / "preview-1440.png", full_page=True)
            page.get_by_role("tab", name="Edição").click()
            page.locator('input[type="file"]').set_input_files(str(portrait))
            page.screenshot(path=EVIDENCE / "editor-portrait-1440.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "editor-390.png", full_page=True)
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "editor-320.png", full_page=True)
            page.locator('input[type="file"]').set_input_files(str(square))
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.get_by_role("button", name="Publicar e destacar na home").first.click()
            _wait_text(page, "Receita publicada e destacada na home.")
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_text("Receita isolada 50").wait_for()
            page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
            _assert_card_photo(page, ".week-recipe-media img", fit="contain")
            page.screenshot(path=EVIDENCE / "home-1440.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=EVIDENCE / "home-390.png", full_page=True)
            page.set_viewport_size({"width": 320, "height": 720})
            page.screenshot(path=EVIDENCE / "home-320.png", full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1100})
            public_href = page.locator(".week-recipe-link").get_attribute("href")
            assert public_href
            page.goto(f"http://127.0.0.1:{PORT}{public_href}")
            page.get_by_role("heading", name="Receita isolada 50").wait_for()
            _assert_card_photo(page, ".week-recipe-hero img", max_height=420, fit="contain")
            page.screenshot(path=EVIDENCE / "read-1440.png", full_page=True)

            page.goto(f"http://127.0.0.1:{PORT}/admin/produtos/receitas/nova")
            page.get_by_role("heading", name="Nova receita").wait_for()
            page.locator("#wre-title").fill("Segunda isolada 50")
            page.locator("#wre-summary").fill("Segunda receita para trocar o destaque.")
            page.locator("#wre-ingredients").fill("100 g manteiga")
            page.locator("#wre-method").fill("Misture a manteiga.")
            page.get_by_label("Texto alternativo da foto").fill("Foto quadrada de teste")
            page.locator('input[type="file"]').set_input_files(str(landscape))
            page.get_by_role("button", name="Publicar sem destacar").first.click()
            _wait_text(page, "Receita publicada, sem alterar o destaque da home.")
            second_url = page.url
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_text("Receita isolada 50").wait_for()
            assert page.get_by_text("Segunda isolada 50").count() == 0
            page.goto(second_url)
            page.get_by_role("heading", name="Editar receita").wait_for()
            page.once("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Publicar e destacar na home").first.click()
            _wait_text(page, "Receita publicada e destacada na home.")
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.get_by_text("Segunda isolada 50").wait_for()
            page.goto(f"http://127.0.0.1:{PORT}{public_href}")
            page.get_by_role("heading", name="Receita isolada 50").wait_for()

            page.goto(first_url)
            page.locator("#wre-title").wait_for()
            page.wait_for_function("document.getElementById('wre-title')?.value")
            kept = page.locator("#wre-title").input_value()
            page.locator("#wre-title").fill(kept + " sessão")
            page.context.clear_cookies()
            page.get_by_role("button", name="Salvar rascunho").first.click()
            _wait_text(page, "Sessão encerrada")
            assert page.locator("#wre-title").input_value() == kept + " sessão"
            page.screenshot(path=EVIDENCE / "editor-session-1440.png", full_page=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
