"""Captura do cartão de receita e da página de leitura. Sem pedido ou pagamento."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
BASE = sys.argv[1] if len(sys.argv) > 1 else "https://lojadepaes.com.br/"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "prod-before"
SIZES = (
    ("1440", 1440, 900, False),
    ("1920", 1920, 1080, False),
    ("768", 768, 1024, False),
    ("390", 390, 844, True),
    ("320", 320, 568, False),
)
SLUGS = (
    ("sopa", "/receitas/sopa-de-cebolas-a-la-tartine"),
    ("sardinhas", "/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread"),
    ("tomate", "/receitas/pan-con-tomate-tartine-bread"),
)


def measure(page) -> dict:
    return page.evaluate(
        """() => {
          const media = document.querySelector('.week-recipe-media');
          const img = document.querySelector('.week-recipe-media img');
          const hero = document.querySelector('.week-recipe-hero');
          const heroImg = document.querySelector('.week-recipe-hero img');
          const copy = document.querySelector('.week-recipe-copy');
          const title = document.querySelector('.week-recipe h3, .week-recipe-page h1');
          const box = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { w: Math.round(r.width), h: Math.round(r.height) };
          };
          const overflow = document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1;
          const mb = box(media);
          const ib = box(img);
          return {
            title: title && title.textContent,
            media: mb,
            img: ib,
            media_ratio: mb && mb.h ? +(mb.w / mb.h).toFixed(3) : null,
            img_fills: Boolean(mb && ib && Math.abs(mb.w - ib.w) <= 1 && Math.abs(mb.h - ib.h) <= 1),
            object_fit: img && getComputedStyle(img).objectFit,
            object_position: img && (img.style.objectPosition || getComputedStyle(img).objectPosition),
            natural: img && { w: img.naturalWidth, h: img.naturalHeight },
            copy: box(copy),
            hero: box(hero),
            hero_img: box(heroImg),
            hero_fit: heroImg && getComputedStyle(heroImg).objectFit,
            has_link: Boolean(document.querySelector('.week-recipe-link, .week-recipe-page')),
            overflow_ok: overflow,
          };
        }"""
    )


def main() -> None:
    report = {"base": BASE, "prefix": PREFIX, "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        for name, width, height, mobile in SIZES:
            context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=mobile)
            page = context.new_page()
            page.set_default_timeout(45000)
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_selector(".week-recipe-media img")
            page.wait_for_function(
                """() => {
                  const img = document.querySelector('.week-recipe-media img');
                  return Boolean(img && img.complete && img.naturalWidth > 0);
                }"""
            )
            page.locator(".week-recipe").scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            data = measure(page)
            report["pages"].append({"step": f"{PREFIX}-home-{name}", **data})
            page.locator(".week-recipe").screenshot(path=CAP / f"{PREFIX}-home-card-{name}.png")
            if name in {"1440", "390"}:
                page.screenshot(path=CAP / f"{PREFIX}-home-fold-{name}.png", full_page=False)
            context.close()

        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(45000)
        for key, path in SLUGS:
            page.goto(BASE.rstrip("/") + path, wait_until="domcontentloaded")
            page.wait_for_selector(".week-recipe-hero img, h1")
            page.wait_for_timeout(400)
            data = measure(page)
            report["pages"].append({"step": f"{PREFIX}-read-{key}", **data})
            page.locator(".week-recipe-page").screenshot(path=CAP / f"{PREFIX}-read-{key}-1440.png")
        context.close()
        browser.close()
    (OUT / f"{PREFIX}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", PREFIX)


if __name__ == "__main__":
    main()
