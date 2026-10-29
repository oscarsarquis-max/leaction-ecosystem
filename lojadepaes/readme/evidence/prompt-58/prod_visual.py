from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(BASE + "/?v=58#paes", wait_until="networkidle")
        page.get_by_role("heading", name="Precisa de outra data?").wait_for()
        page.get_by_label("Data desejada").wait_for()
        assert page.get_by_role("button", name="Sugerir uma data").count() == 0
        assert page.get_by_role("button", name="Enviar solicitação").is_visible()
        page.locator("#paes").screenshot(path=OUT / "prod-1440.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_label("Data desejada").wait_for()
        assert page.get_by_role("button", name="Enviar solicitação").is_visible()
        page.locator("#paes").screenshot(path=OUT / "prod-390.png")
        html = page.request.get(BASE + "/").text()
        assert "index-DJDU60Wy.js" in html
        assert page.get_by_role("button", name="Sugerir uma data").count() == 0
        browser.close()
    print("prod-visual-ok")


if __name__ == "__main__":
    main()
