"""Antes/depois visual da abertura. Sem pedido, e-mail ou pagamento."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:5175/"
SIZES = (
    ("1440", 1440, 900, False),
    ("1920", 1920, 1080, False),
    ("768", 768, 1024, False),
    ("390", 390, 844, True),
    ("320", 320, 568, False),
)


def measure(page) -> dict:
    return page.evaluate(
        """() => {
          const intro = document.querySelector('.intro');
          const photo = document.querySelector('.intro-photo');
          const copy = document.querySelector('.intro-copy');
          const shelf = document.querySelector('#paes, .shelf, .product-shelf, [id="paes"]')
            || document.querySelector('h2');
          const box = (el) => el ? el.getBoundingClientRect() : null;
          const ib = box(intro);
          const pb = box(photo);
          const overflow = document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1;
          return {
            intro_w: ib && Math.round(ib.width),
            photo_w: pb && Math.round(pb.width),
            photo_h: pb && Math.round(pb.height),
            copy_w: copy && Math.round(copy.getBoundingClientRect().width),
            ratio: pb && pb.width && (pb.width / pb.height),
            src: photo && photo.getAttribute('src'),
            natural: photo && { w: photo.naturalWidth, h: photo.naturalHeight, complete: photo.complete },
            alt: photo && photo.getAttribute('alt'),
            has_seal: Boolean(document.querySelector('.intro-aside .seal')),
            has_levain: (document.body.innerText || '').includes('O DESPERTAR DO LEVAIN'),
            has_title: (document.body.innerText || '').includes('Todo pão tem uma história'),
            overflow_ok: overflow,
          };
        }"""
    )


def main() -> None:
    report: dict = {"pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        for name, width, height, mobile in SIZES:
            context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=mobile)
            page = context.new_page()
            page.set_default_timeout(45000)
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 0)")
            data = measure(page)
            report["pages"].append({"step": name, **data})
            intro = page.locator(".intro")
            intro.screenshot(path=CAP / f"local-intro-{name}.png")
            page.screenshot(path=CAP / f"local-fold-{name}.png", full_page=False)
            context.close()
        browser.close()
    (OUT / "local-intro.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote local-intro.json")


if __name__ == "__main__":
    main()
