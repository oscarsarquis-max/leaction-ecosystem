from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"
QUESTION = "Quero comprar um pão rústico de fermentação natural. Com o que combina na hora de servir?"


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE + "/", wait_until="networkidle")
        page.evaluate("sessionStorage.removeItem('lojadepaes_gigio_messages')")
        page.get_by_role("button", name="Conversar com Gigio").click()
        page.get_by_role("heading", name="Gigio").wait_for()
        page.get_by_label("Mensagem para o Gigio").fill(QUESTION)
        send = page.get_by_role("button", name="Enviar")
        assert send.is_visible()
        with page.expect_response(
            lambda resp: "/api/v1/gigio/chat" in resp.url and resp.request.method == "POST",
            timeout=90000,
        ) as pending:
            send.click()
            page.get_by_text("Gigio está consultando").wait_for()
        payload = pending.value.json()
        reply = payload.get("reply") or ""
        if "longa demais" in reply or payload.get("unavailable"):
            page.screenshot(path=OUT / "prod-fail.png", full_page=False)
            raise AssertionError(f"resposta inválida: {payload}")
        page.get_by_text("Gigio está consultando").wait_for(state="hidden", timeout=15000)
        body = page.locator(".gigio-thread").inner_text()
        if "longa demais" in body:
            raise AssertionError("mensagem falsa de comprimento no painel")
        if "Pão Fermentação Natural" not in body and not payload.get("links"):
            page.screenshot(path=OUT / "prod-fail.png", full_page=False)
            raise AssertionError(f"painel sem resposta culinária: {body[:400]}")
        cafe_links = page.get_by_role("link", name="Pão de Café")
        assert cafe_links.count() == 0
        send_box = send.bounding_box()
        assert send_box and send_box["width"] >= 48 and send_box["height"] >= 32
        page.screenshot(path=OUT / "prod-1440.png", full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        mobile_send = page.get_by_role("button", name="Enviar").bounding_box()
        assert mobile_send and mobile_send["width"] >= 44 and mobile_send["height"] >= 32
        page.screenshot(path=OUT / "prod-390.png", full_page=False)
        browser.close()
    print("prod-visual-ok")


if __name__ == "__main__":
    main()
