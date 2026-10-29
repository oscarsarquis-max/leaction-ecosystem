"""Cartão de destaque com as outras fotos publicadas e um quadrado local. Sem cadastro."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:5175/"
PROD = "https://lojadepaes.com.br"
SQUARE = OUT / "fixture-square.jpg"

VARIANTS = (
    ("sardinhas", OUT / "sardinhas.jpg", "49% 53%", 960, 1280),
    ("tomate", OUT / "tomate.jpg", "57% 62%", 900, 1600),
    ("square-fixture", SQUARE, "50% 50%", 400, 400),
)


def make_square() -> None:
    image = Image.new("RGB", (400, 400), (236, 231, 216))
    draw = ImageDraw.Draw(image)
    draw.ellipse((80, 80, 320, 320), fill=(152, 83, 60))
    draw.rectangle((160, 250, 240, 340), fill=(250, 248, 242))
    image.save(SQUARE, quality=90)


def data_url(path: Path) -> str:
    raw = path.read_bytes()
    return "data:image/jpeg;base64," + __import__("base64").b64encode(raw).decode("ascii")


def attach(page) -> None:
    def handle(route) -> None:
        path = route.request.url[route.request.url.find("/api") :]
        try:
            with urllib.request.urlopen(PROD + path, timeout=30) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type") or "application/octet-stream"
                status = 200
        except urllib.error.HTTPError as error:
            body = error.read()
            content_type = error.headers.get("Content-Type") or "application/json"
            status = error.code
        route.fulfill(status=status, body=body, headers={"Content-Type": content_type})

    page.route("**/api/v1/catalog/**", handle)


def main() -> None:
    make_square()
    report = {"kind": "card-formats-local", "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        attach(page)
        page.set_default_timeout(45000)
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_selector(".week-recipe-media img")
        page.locator(".week-recipe").scroll_into_view_if_needed()
        for name, path, focus, natural_w, natural_h in VARIANTS:
            page.evaluate(
                """([src, nextFocus]) => {
                  const img = document.querySelector('.week-recipe-media img');
                  img.src = src;
                  img.style.objectPosition = nextFocus;
                }""",
                [data_url(path), focus],
            )
            page.wait_for_function(
                """([w, h]) => {
                  const img = document.querySelector('.week-recipe-media img');
                  return img && img.complete && img.naturalWidth === w && img.naturalHeight === h;
                }""",
                arg=[natural_w, natural_h],
            )
            page.wait_for_timeout(250)
            data = page.evaluate(
                """() => {
                  const media = document.querySelector('.week-recipe-media');
                  const img = document.querySelector('.week-recipe-media img');
                  const r = media.getBoundingClientRect();
                  return {
                    media_w: Math.round(r.width),
                    media_h: Math.round(r.height),
                    ratio: +(r.width / r.height).toFixed(3),
                    fills: Math.abs(r.width - img.getBoundingClientRect().width) <= 1,
                    fit: getComputedStyle(img).objectFit,
                    position: img.style.objectPosition || getComputedStyle(img).objectPosition,
                    natural: { w: img.naturalWidth, h: img.naturalHeight },
                  };
                }"""
            )
            report["pages"].append({"variant": name, **data})
            page.locator(".week-recipe-media").screenshot(path=CAP / f"local-card-{name}-1440.png")
        page.goto(BASE.rstrip("/") + "/receitas", wait_until="domcontentloaded")
        page.wait_for_selector(".recipe-archive-page, .recipe-search-results")
        page.wait_for_timeout(400)
        report["archive"] = page.evaluate(
            """() => ({
              photos: document.querySelectorAll('.recipe-archive-page img, .recipe-search-results img').length,
              titles: [...document.querySelectorAll('.recipe-search-results a')].map((el) => el.textContent.trim()),
            })"""
        )
        page.locator(".recipe-archive-page").screenshot(path=CAP / "local-archive-1440.png")
        page.unroute_all(behavior="ignoreErrors")
        context.close()
        browser.close()
    (OUT / "local-card-formats.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote local-card-formats")


if __name__ == "__main__":
    main()
