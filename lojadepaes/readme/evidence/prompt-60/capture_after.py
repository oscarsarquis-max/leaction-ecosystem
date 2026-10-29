import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"
SLUG = "pan-con-tomate-tartine-bread"


def metrics(page):
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const first = main && (main.querySelector('h1, h2, .eyebrow, p') || main);
          const cs = getComputedStyle(main);
          const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
          const gigio = document.querySelector('.gigio-launch');
          const search = document.querySelector('#home-recipe-q');
          const action = document.querySelector('.recipe-search-row .primary, main.week-recipe-page a.text-button, main.checkout-page button.primary');
          const g = gigio && gigio.getBoundingClientRect();
          const overlap = (a, b) => {
            if (!a || !b) return false;
            return !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
          };
          const s = search && search.getBoundingClientRect();
          const b = action && action.getBoundingClientRect();
          return {
            paddingLeft: cs.paddingLeft,
            paddingRight: cs.paddingRight,
            firstLeft: first ? Math.round(first.getBoundingClientRect().left) : null,
            overflowX: overflow,
            gigioSearch: overlap(g, s),
            bundle: [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0] || null,
          };
        }"""
    )


def main() -> None:
    report = {}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (768, 1024, "768"), (1440, 900, "1440")):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{BASE}/receitas/{SLUG}", wait_until="networkidle")
            page.get_by_role("heading", level=1).wait_for()
            if width <= 390:
                page.locator("main.week-recipe-page a.text-button").evaluate("el => el.scrollIntoView({block:'end'})")
            report[f"recipe-{tag}"] = metrics(page)
            page.screenshot(path=OUT / f"after-recipe-{tag}.png", full_page=True)
            page.goto(f"{BASE}/pedido/novo", wait_until="networkidle")
            page.get_by_text("Pedido").first.wait_for()
            report[f"review-{tag}"] = metrics(page)
            page.screenshot(path=OUT / f"after-review-{tag}.png", full_page=True)
            if width in (390, 1440):
                page.goto(f"{BASE}/#paes", wait_until="networkidle")
                page.get_by_label("Buscar receitas").wait_for()
                page.get_by_label("Buscar receitas").evaluate("el => el.scrollIntoView({block:'end'})")
                report[f"home-{tag}"] = metrics(page)
                page.locator(".week-recipe").screenshot(path=OUT / f"after-home-card-{tag}.png")
                page.screenshot(path=OUT / f"after-home-{tag}.png", full_page=True)
            page.close()
        browser.close()
    (OUT / "after-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
