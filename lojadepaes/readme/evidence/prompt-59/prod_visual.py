import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(BASE + "/?v=59#paes", wait_until="networkidle")
        page.get_by_text("Receita em destaque").wait_for()
        page.get_by_label("Data desejada").wait_for()
        page.wait_for_function("document.querySelector('.week-recipe-media img')?.naturalWidth > 0")
        assert page.get_by_role("button", name="Sugerir uma data").count() == 0
        assert page.get_by_role("button", name="Enviar solicitação").is_visible()
        metrics = page.evaluate(
            """() => {
              const media = document.querySelector('.week-recipe-media');
              const img = document.querySelector('.week-recipe-media img');
              const search = document.querySelector('.week-recipe-search');
              const body = document.querySelector('.week-recipe-body');
              const ms = getComputedStyle(media);
              const is = getComputedStyle(img);
              const mr = media.getBoundingClientRect();
              const ir = img.getBoundingClientRect();
              const sr = search.getBoundingClientRect();
              const br = body.getBoundingClientRect();
              return {
                justify: ms.justifyContent,
                align: ms.alignItems,
                fit: is.objectFit,
                maxH: is.maxHeight,
                imgH: Math.round(ir.height),
                imgW: Math.round(ir.width),
                mediaW: Math.round(mr.width),
                leftGap: Math.round(ir.left - mr.left),
                rightGap: Math.round(mr.right - ir.right),
                searchGap: Math.round(sr.top - br.bottom),
              };
            }"""
        )
        (OUT / "prod-after-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        if metrics["fit"] != "contain" or metrics["imgH"] > 321:
            raise AssertionError(metrics)
        if abs(metrics["leftGap"] - metrics["rightGap"]) > 4:
            raise AssertionError(metrics)
        page.locator(".week-recipe").screenshot(path=OUT / "prod-after-card-1440.png")
        page.locator("#paes").screenshot(path=OUT / "prod-after-1440.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_label("Data desejada").wait_for()
        page.locator(".week-recipe").screenshot(path=OUT / "prod-after-card-390.png")
        page.locator("#paes").screenshot(path=OUT / "prod-after-390.png")
        html = page.request.get(BASE + "/?v=59").text()
        assert "Sugerir uma data" not in page.content()
        match = __import__("re").search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
        print(json.dumps({"bundle": match.group(0) if match else None, **metrics}, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
