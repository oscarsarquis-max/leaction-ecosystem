"""Recaptura da página oficial de planos no Hub (Chrome instalado)."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "captures"
HUB = "https://actionhub.com.br/loja"


def main() -> None:
    report: dict = {"url": HUB, "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        for width, tag in ((1440, "1440"), (390, "390")):
            context = browser.new_context(
                viewport={"width": width, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_timeout(20000)
            errors: list[str] = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            responses: list[dict] = []

            def on_response(resp):
                url = resp.url
                if "catalog" in url or "/loja" in url:
                    responses.append({"url": url, "status": resp.status})

            page.on("response", on_response)
            page.goto(HUB, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            body = page.inner_text("body")
            report["pages"].append(
                {
                    "viewport": tag,
                    "title": page.title(),
                    "has_19": "19" in body,
                    "has_10": "10" in body,
                    "has_avulso": "avulso" in body.lower(),
                    "has_mes": "/mês" in body or "por mês" in body,
                    "snippet": " ".join(body.split())[:1200],
                    "errors": errors[:5],
                    "responses": responses[:12],
                }
            )
            page.screenshot(path=OUT / f"prod-hub-loja-{tag}.png", full_page=True)
            context.close()
        browser.close()
    (OUT / "hub-capture-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
