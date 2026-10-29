from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        for width, height, name in (
            (1440, 900, "prod-home-1440"),
            (390, 844, "prod-home-390"),
        ):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(BASE + "/", wait_until="networkidle")
            page.get_by_role("button", name="Conversar com Gigio").wait_for()
            page.screenshot(path=OUT / f"{name}-fechado.png", full_page=False)
            page.get_by_role("button", name="Conversar com Gigio").click()
            page.get_by_role("heading", name="Gigio").wait_for()
            page.screenshot(path=OUT / f"{name}-aberto.png", full_page=False)
            page.keyboard.press("Escape")
            page.close()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(BASE + "/paes/pao-de-cafe-marroquinus", wait_until="networkidle")
        page.get_by_role("button", name="Adicionar à seleção").click()
        page.goto(BASE + "/pedido/novo", wait_until="networkidle")
        page.get_by_role("button", name="Conversar com Gigio").wait_for()
        send = page.get_by_role("button", name="Enviar pedido")
        assert send.is_visible()
        box = send.bounding_box()
        launch = page.get_by_role("button", name="Conversar com Gigio").bounding_box()
        assert box and launch
        overlap = not (
            box["y"] + box["height"] <= launch["y"]
            or launch["y"] + launch["height"] <= box["y"]
            or box["x"] + box["width"] <= launch["x"]
            or launch["x"] + launch["width"] <= box["x"]
        )
        assert not overlap
        page.screenshot(path=OUT / "prod-checkout-390.png", full_page=False)
        page.close()
        browser.close()
    print("prod-visual-ok")


if __name__ == "__main__":
    main()
