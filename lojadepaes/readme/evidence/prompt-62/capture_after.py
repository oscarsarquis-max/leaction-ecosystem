import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"
SLUG = "pao-de-canela-cenemon-bread"
OTHER = "pao-de-frutas-arabian-bread"


def boxes(page) -> dict:
    return page.evaluate(
        """() => {
          const main = document.querySelector('main');
          const vw = window.innerWidth;
          const nodes = [...main.querySelectorAll('h1,p,img,a,label,button,legend,.eyebrow')];
          const flush = [];
          const samples = {};
          for (const el of nodes) {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) continue;
            const key = el.tagName + ':' + (el.innerText || el.alt || '').slice(0, 24);
            if (!samples[el.tagName]) samples[el.tagName] = {left: Math.round(r.left), right: Math.round(vw - r.right)};
            if (r.left < 15.5 || r.right > vw - 15.5) flush.push({tag: el.tagName, left: Math.round(r.left), right: Math.round(r.right)});
          }
          return {
            path: location.pathname,
            paddingLeft: getComputedStyle(main).paddingLeft,
            paddingRight: getComputedStyle(main).paddingRight,
            overflowX: document.documentElement.scrollWidth > vw + 1,
            flush: flush.slice(0, 6),
            samples,
            bundle: [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0] || null,
          };
        }"""
    )


def main() -> None:
    report = {"browser": "playwright-chromium emulated; not physical iPhone/Safari"}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{BASE}/#paes", wait_until="networkidle")
        page.get_by_role("heading", name="Pão de Canela").click()
        page.get_by_role("heading", name="Pão de Canela (Cinnamon Bread)").wait_for()
        report["from-home"] = page.evaluate("location.pathname")
        for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (375, 812, "375"), (430, 932, "430"), (768, 1024, "768"), (1440, 900, "1440")):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(80)
            report[f"canela-{tag}"] = boxes(page)
            page.screenshot(path=OUT / f"after-canela-{tag}.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE}/paes/{OTHER}", wait_until="networkidle")
        page.get_by_role("heading", level=1).wait_for()
        report["other-390"] = boxes(page)
        page.screenshot(path=OUT / "after-other-390.png", full_page=True)
        browser.close()
    (OUT / "after-metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
