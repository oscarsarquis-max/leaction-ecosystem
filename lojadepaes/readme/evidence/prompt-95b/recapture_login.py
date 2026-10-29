"""Recorte do painel Identifique-se. Sem clicar em Receber código nem Entrar."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "captures"
OUT.mkdir(exist_ok=True)


def capture(page, name: str) -> None:
    page.goto("https://lojadepaes.com.br/", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.get_by_role("button", name="Identifique-se").click()
    page.wait_for_timeout(600)
    panel = page.locator("#header-customer-panel, [role='dialog'][aria-label='Situação da conta']").first
    if panel.count():
        panel.screenshot(path=OUT / name)
    else:
        page.locator(".header-customer-panel").first.screenshot(path=OUT / name)


def main() -> None:
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        page = desktop.new_page()
        page.set_default_timeout(45000)
        capture(page, "prod-loja-identifique-panel-1440.png")
        desktop.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mpage = mobile.new_page()
        mpage.set_default_timeout(45000)
        capture(mpage, "prod-loja-identifique-panel-390.png")
        mobile.close()
        browser.close()
    print("wrote login panels")


if __name__ == "__main__":
    main()
