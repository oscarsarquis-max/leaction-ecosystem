"""Calendário público depois do fechamento. Sem pedido."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)


def main() -> None:
    report: dict = {"pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        for name, width, height in (("1440", 1440, 1000), ("390", 390, 844)):
            context = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=width < 800,
            )
            page = context.new_page()
            page.goto("https://lojadepaes.com.br/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            cal = page.locator(".bake-calendar, [aria-label='Calendário de fornadas']").first
            if cal.count():
                cal.scroll_into_view_if_needed()
            page.wait_for_timeout(800)
            page.screenshot(path=CAP / f"prod-home-after-{name}.png", full_page=True)
            body = page.inner_text("body")
            report["pages"].append(
                {
                    "step": f"home-after-{name}",
                    "has_notice": "fornadas disponíveis a partir de 21" in body.lower(),
                    "has_viagem": "viagem" in body.lower(),
                    "snippet": " ".join(body.split())[body.lower().find("escolha") : body.lower().find("escolha") + 500]
                    if "escolha" in body.lower()
                    else " ".join(body.split())[:500],
                }
            )
            page.goto("https://lojadepaes.com.br/#criacao", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.screenshot(path=CAP / f"prod-fazedor-after-{name}.png", full_page=True)
            fbody = page.inner_text("body")
            report["pages"].append(
                {
                    "step": f"fazedor-after-{name}",
                    "has_notice": "fornadas disponíveis a partir de 21" in fbody.lower(),
                    "has_viagem": "viagem" in fbody.lower(),
                }
            )
            context.close()
        browser.close()
    (OUT / "public-after.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote public-after.json")


if __name__ == "__main__":
    main()
