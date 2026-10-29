import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"
HREF = "/paes/pao-de-canela-cenemon-bread"


def boxes(page) -> dict:
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const vw = window.innerWidth;
          const pick = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {left: Math.round(r.left), right: Math.round(vw - r.right), w: Math.round(r.width)};
          };
          const nodes = [...main.querySelectorAll('h1,p,img,a,label,button,legend,.eyebrow')];
          const flush = [];
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) continue;
            if (r.left < 15.5 || r.right > vw - 15.5) flush.push({tag: el.tagName, left: Math.round(r.left), right: Math.round(r.right), text: (el.innerText||el.alt||'').slice(0,40)});
          }
          return {
            path: location.pathname,
            paddingLeft: getComputedStyle(main).paddingLeft,
            paddingRight: getComputedStyle(main).paddingRight,
            overflowX: document.documentElement.scrollWidth > vw + 1,
            flush,
            eyebrow: pick('.eyebrow, .eyebrow a'),
            h1: pick('h1'),
            img: pick('main.product-page img'),
            summary: pick('.product-summary'),
            cta: pick('main.product-page button.primary'),
            bundle: [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0] || null,
          };
        }"""
    )


def main() -> None:
    extra = {}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{BASE}/#paes", wait_until="networkidle")
        page.locator(f'a.shelf-link[href="{HREF}"]').first.click()
        page.get_by_role("heading", name="Pão de Canela (Cinnamon Bread)").wait_for()
        extra["from-home"] = page.evaluate("location.pathname")
        extra["home-to-product"] = boxes(page)
        page.screenshot(path=OUT / "after-canela-from-home-390.png", full_page=True)
        page.goto(BASE + HREF, wait_until="networkidle")
        page.get_by_role("heading", name="Pão de Canela (Cinnamon Bread)").wait_for()
        for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (375, 812, "375"), (430, 932, "430"), (768, 1024, "768"), (1440, 900, "1440")):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(100)
            extra[f"canela-{tag}"] = boxes(page)
            page.screenshot(path=OUT / f"after-canela-{tag}.png", full_page=True)
        browser.close()
    prev = json.loads((OUT / "after-metrics.json").read_text(encoding="utf-8"))
    prev.update(extra)
    (OUT / "after-metrics.json").write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print(json.dumps({k: extra[k] for k in extra if k != "canela-768"}, indent=2))


if __name__ == "__main__":
    main()
