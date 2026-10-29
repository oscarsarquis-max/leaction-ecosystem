"""Calendário público outubro/2026. Sem pedido."""

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
            page.wait_for_timeout(2500)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.35)")
            page.wait_for_timeout(1000)
            shot = CAP / f"prod-home-calendar-{name}.png"
            page.screenshot(path=shot, full_page=True)
            body = page.inner_text("body")
            report["pages"].append(
                {
                    "step": f"home-{name}",
                    "has_21": "21 de outubro" in body.lower() or "21 de outubro" in body,
                    "has_viagem": "viagem" in body.lower(),
                    "snippet": " ".join(body.split())[:400],
                }
            )
            context.close()
        browser.close()
    (OUT / "public-calendar.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote public-calendar.json")


if __name__ == "__main__":
    main()
