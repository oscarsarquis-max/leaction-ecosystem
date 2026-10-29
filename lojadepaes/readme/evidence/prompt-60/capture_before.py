import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"
SLUG = "pan-con-tomate-tartine-bread"


def metrics(page, extra=""):
    return page.evaluate(
        f"""() => {{
          const main = document.querySelector('main');
          const first = main && (main.querySelector('h1, h2, .eyebrow, p') || main);
          const mr = main.getBoundingClientRect();
          const cs = getComputedStyle(main);
          const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
          const gigio = document.querySelector('.gigio-launch');
          const search = document.querySelector('.recipe-search-row input, [aria-label="Buscar receitas"]');
          const send = document.querySelector('.checkout-page button.primary, .recipe-search-row .primary');
          const g = gigio && gigio.getBoundingClientRect();
          const s = search && search.getBoundingClientRect();
          const b = send && send.getBoundingClientRect();
          const overlap = (a, b) => a && b && !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
          return {{
            paddingLeft: cs.paddingLeft,
            paddingRight: cs.paddingRight,
            mainLeft: Math.round(mr.left),
            firstLeft: first ? Math.round(first.getBoundingClientRect().left) : null,
            overflowX: overflow,
            gigioSearch: overlap(g, s),
            gigioAction: overlap(g, b),
            {extra}
          }};
        }}"""
    )


def shot(page, name: str) -> None:
    page.screenshot(path=OUT / name, full_page=True)


def main() -> None:
    report = {}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        for width, height, tag in ((390, 844, "390"), (320, 720, "320")):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{BASE}/receitas/{SLUG}", wait_until="networkidle")
            page.get_by_role("heading", level=1).wait_for()
            report[f"recipe-{tag}"] = metrics(page)
            shot(page, f"before-recipe-{tag}.png")
            page.goto(f"{BASE}/pedido/novo", wait_until="networkidle")
            page.get_by_text("Pedido").first.wait_for()
            report[f"review-{tag}"] = metrics(page)
            shot(page, f"before-review-{tag}.png")
            page.goto(f"{BASE}/#paes", wait_until="networkidle")
            page.get_by_label("Buscar receitas").wait_for()
            page.get_by_label("Buscar receitas").evaluate("el => el.scrollIntoView({block:'end'})")
            report[f"home-{tag}"] = metrics(page)
            page.locator(".week-recipe").screenshot(path=OUT / f"before-home-card-{tag}.png")
            page.close()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE}/#paes", wait_until="networkidle")
        page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalHeight > 0")
        report["card-1440"] = page.evaluate(
            """() => {
              const img = document.querySelector('.week-recipe-media img');
              const is = getComputedStyle(img);
              const r = img.getBoundingClientRect();
              return { maxH: is.maxHeight, imgH: Math.round(r.height), imgW: Math.round(r.width) };
            }"""
        )
        browser.close()
    (OUT / "before-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
