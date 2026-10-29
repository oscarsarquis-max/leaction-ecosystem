import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def main() -> None:
    report = {}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        page.get_by_role("heading", name="Fale com A Loja").wait_for()
        whatsapp = page.get_by_role("link", name="Converse pelo WhatsApp")
        instagram = page.get_by_role("link", name="Acompanhe no Instagram")
        report["whatsapp"] = whatsapp.get_attribute("href")
        report["instagram"] = instagram.get_attribute("href")
        report["formOpen"] = page.locator(".bake-calendar-request form").count() > 0
        report["bundle"] = page.evaluate(
            """() => [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0]"""
        )
        for width, height, tag in ((1440, 900, "1440"), (768, 1024, "768"), (390, 844, "390"), (320, 720, "320")):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(80)
            page.locator(".home-contact").scroll_into_view_if_needed()
            page.screenshot(path=OUT / f"prod-home-{tag}.png", full_page=True)
            page.locator(".home-contact").screenshot(path=OUT / f"prod-contact-{tag}.png")
        browser.close()
    (OUT / "prod-after.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
