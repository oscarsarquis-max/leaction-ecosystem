"""Leitura em produção, esperando a foto carregar. Sem cadastro."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
PAGES = (
    ("sopa", "/receitas/sopa-de-cebolas-a-la-tartine"),
    ("sardinhas", "/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread"),
    ("tomate", "/receitas/pan-con-tomate-tartine-bread"),
)


def main() -> None:
    report = []
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(45000)
        for key, path in PAGES:
            page.goto("https://lojadepaes.com.br" + path, wait_until="domcontentloaded")
            page.wait_for_selector(".week-recipe-hero img")
            page.wait_for_function(
                """() => {
                  const img = document.querySelector('.week-recipe-hero img');
                  return Boolean(img && img.complete && img.naturalWidth > 0);
                }"""
            )
            page.wait_for_timeout(200)
            data = page.evaluate(
                """() => {
                  const img = document.querySelector('.week-recipe-hero img');
                  const hero = document.querySelector('.week-recipe-hero');
                  const r = img.getBoundingClientRect();
                  const h = hero.getBoundingClientRect();
                  return {
                    title: document.querySelector('h1') && document.querySelector('h1').textContent,
                    hero: { w: Math.round(h.width), h: Math.round(h.height) },
                    img: { w: Math.round(r.width), h: Math.round(r.height) },
                    fit: getComputedStyle(img).objectFit,
                    natural: { w: img.naturalWidth, h: img.naturalHeight },
                  };
                }"""
            )
            report.append({"variant": key, **data})
            page.locator(".week-recipe-page").screenshot(path=CAP / f"prod-after-read-{key}-1440.png")
        context.close()
        browser.close()
    (OUT / "prod-after-read.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
