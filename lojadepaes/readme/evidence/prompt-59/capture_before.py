from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(BASE + "/#paes", wait_until="networkidle")
        page.get_by_text("Receita em destaque").wait_for()
        page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
        metrics = page.evaluate(
            """() => {
              const media = document.querySelector('.week-recipe-media');
              const img = document.querySelector('.week-recipe-media img');
              const ms = getComputedStyle(media);
              const is = getComputedStyle(img);
              const mr = media.getBoundingClientRect();
              const ir = img.getBoundingClientRect();
              return {
                justify: ms.justifyContent,
                align: ms.alignItems,
                fit: is.objectFit,
                maxH: is.maxHeight,
                mediaW: Math.round(mr.width),
                imgW: Math.round(ir.width),
                imgH: Math.round(ir.height),
                leftGap: Math.round(ir.left - mr.left),
                rightGap: Math.round(mr.right - ir.right),
              };
            }"""
        )
        (OUT / "prod-before-metrics.json").write_text(
            __import__("json").dumps(metrics, indent=2), encoding="utf-8"
        )
        page.locator(".week-recipe").screenshot(path=OUT / "prod-before-card-1440.png")
        page.locator("#paes").screenshot(path=OUT / "prod-before-1440.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator(".week-recipe").screenshot(path=OUT / "prod-before-card-390.png")
        browser.close()
    print(metrics)


if __name__ == "__main__":
    main()
