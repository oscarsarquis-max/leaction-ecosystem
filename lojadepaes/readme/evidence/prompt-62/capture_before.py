import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def flush(page) -> dict:
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const vw = window.innerWidth;
          const cs = getComputedStyle(main);
          const nodes = [...main.querySelectorAll('h1,h2,p,li,img,a,label,button,input,textarea,fieldset,.eyebrow,.product-summary')];
          const bad = [];
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) continue;
            if (r.left < 15.5) bad.push({tag: el.tagName, left: Math.round(r.left), text: (el.innerText || el.alt || '').slice(0, 60)});
            if (r.right > vw - 15.5) bad.push({tag: el.tagName, right: Math.round(r.right), vw, text: (el.innerText || el.alt || '').slice(0, 60)});
          }
          return {
            path: location.pathname,
            title: document.querySelector('h1')?.textContent || null,
            paddingLeft: cs.paddingLeft,
            paddingRight: cs.paddingRight,
            overflowX: document.documentElement.scrollWidth > vw + 1,
            flush: bad.slice(0, 10),
            bundle: [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0] || null,
          };
        }"""
    )


def main() -> None:
    report = {}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        catalog = page.request.get(f"{BASE}/api/v1/catalog/products").json()
        items = catalog.get("items") or catalog.get("products") or catalog
        if isinstance(items, dict):
            items = items.get("items") or []
        canela = next((p for p in items if "canela" in (p.get("name") or "").lower() or "canela" in (p.get("slug") or "")), None)
        other = next((p for p in items if p is not canela and p.get("slug")), None)
        report["catalog"] = {
            "canela": {"name": canela.get("name"), "slug": canela.get("slug"), "href": canela.get("href")} if canela else None,
            "other": {"name": other.get("name"), "slug": other.get("slug")} if other else None,
            "count": len(items) if isinstance(items, list) else None,
        }
        slug = (canela or {}).get("slug")
        if not slug:
            raise SystemExit(json.dumps(report, indent=2))
        href = f"{BASE}/paes/{slug}"
        page.goto(href, wait_until="networkidle")
        page.get_by_role("heading", level=1).wait_for()
        report["route"] = page.evaluate("location.pathname")
        for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (375, 812, "375"), (430, 932, "430")):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(80)
            report[f"canela-{tag}"] = flush(page)
            page.screenshot(path=OUT / f"before-canela-{tag}.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        if other:
            page.goto(f"{BASE}/paes/{other['slug']}", wait_until="networkidle")
            page.get_by_role("heading", level=1).wait_for()
            report["other-390"] = flush(page)
            page.screenshot(path=OUT / "before-other-390.png", full_page=True)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(href, wait_until="networkidle")
        page.get_by_role("heading", level=1).wait_for()
        report["canela-1440"] = flush(page)
        page.screenshot(path=OUT / "before-canela-1440.png", full_page=True)
        html = page.request.get(BASE).text()
        report["home-bundle"] = __import__("re").search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
        report["home-bundle"] = report["home-bundle"].group(0) if report["home-bundle"] else None
        browser.close()
    (OUT / "before-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
