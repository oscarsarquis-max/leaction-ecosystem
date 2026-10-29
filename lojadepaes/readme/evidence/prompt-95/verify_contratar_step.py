"""Próximo passo oficial: cartão → /loja/contratar. Sem iniciar pagamento."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
PARAMS = (
    "https://actionhub.com.br/loja"
    "?return_origin=https%3A%2F%2Flojadepaes.com.br"
    "&return_to=%2F%23biblioteca"
)


def main() -> None:
    report: dict = {"steps": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(45000)
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)[:240]))

        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="Quero este plano").first.click()
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        report["steps"].append(
            {
                "step": "contratar-assinatura",
                "url": page.url,
                "crash_ui": "couldn" in body.lower() and "load" in body.lower(),
                "has_email": "e-mail" in body.lower() or "email" in body.lower(),
                "has_19": "19" in body,
                "has_pagar": "pagar" in body.lower() or "continuar" in body.lower() or "iniciar" in body.lower(),
                "errors": errors[:6],
                "snippet": " ".join(body.split())[:700],
            }
        )
        page.screenshot(path=CAP / "prod-hub-contratar-assinatura-1440.png", full_page=True)

        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Comprar agora").first.click()
        page.wait_for_timeout(2500)
        body2 = page.inner_text("body")
        report["steps"].append(
            {
                "step": "contratar-avulso",
                "url": page.url,
                "crash_ui": "couldn" in body2.lower() and "load" in body2.lower(),
                "has_10": "10" in body2,
                "has_email": "e-mail" in body2.lower() or "email" in body2.lower(),
                "errors": errors[:6],
                "snippet": " ".join(body2.split())[:500],
            }
        )
        page.screenshot(path=CAP / "prod-hub-contratar-avulso-1440.png", full_page=True)
        browser.close()

    (OUT / "verify-contratar.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote verify-contratar.json")


if __name__ == "__main__":
    main()
