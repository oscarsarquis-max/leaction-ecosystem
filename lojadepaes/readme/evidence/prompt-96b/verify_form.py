"""Leitura em produção do formulário 96B. Sem envio, e-mail ou pagamento."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
BASE = "https://lojadepaes.com.br/#paes"
EXPLANATION = (
    "Sugira uma data. A Loja avalia a possibilidade e responde por e-mail. "
    "Esta solicitação ainda não confirma a fornada."
)
OLD = "inclusive para hoje"


def inspect(page) -> dict:
    qty = page.get_by_label("Quantidade pretendida")
    body = page.inner_text("body")
    overflow = page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )
    return {
        "url": page.url,
        "heading": page.get_by_role("heading", name="Precisa de outra data?").count(),
        "quantity_value": qty.input_value() if qty.count() else None,
        "placeholder": qty.get_attribute("placeholder") if qty.count() else None,
        "explanation": EXPLANATION in body,
        "old_inclusive_hoje": OLD in body.lower(),
        "closure_notice": "a partir de" in body.lower(),
        "no_horizontal_overflow": overflow,
        "submit_visible": page.get_by_role("button", name="Enviar solicitação").count(),
    }


def main() -> None:
    report: dict = {"kind": "production_read", "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        ops = page.request.get("https://lojadepaes.com.br/api/v1/operations")
        report["operations"] = {
            "status": ops.status,
            "closure_notice": ops.json().get("closure_notice") if ops.ok else None,
        }
        page.goto(BASE, wait_until="domcontentloaded")
        page.get_by_role("heading", name="Precisa de outra data?").wait_for()
        page.wait_for_timeout(800)
        report["pages"].append({"step": "desktop-1440", **inspect(page)})
        page.screenshot(path=CAP / "prod-form-1440.png", full_page=True)
        for width, name, key in (
            (390, "prod-form-390.png", "mobile-390"),
            (320, "prod-form-320.png", "mobile-320"),
        ):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(300)
            report["pages"].append({"step": key, **inspect(page)})
            page.screenshot(path=CAP / name, full_page=True)
        browser.close()
    (OUT / "verify-form.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    desktop = report["pages"][0]
    assert desktop["heading"] == 1
    assert desktop["quantity_value"] == ""
    assert desktop["placeholder"] == "Informe quantos pães"
    assert desktop["explanation"]
    assert not desktop["old_inclusive_hoje"]
    print("PROD_FORM_OK")


if __name__ == "__main__":
    main()
