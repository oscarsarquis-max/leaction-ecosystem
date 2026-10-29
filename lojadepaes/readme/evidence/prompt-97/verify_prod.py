"""Produção: inspeciona o popover. Sem Entrar, Receber código, senha ou e-mail."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
LOJA = "https://lojadepaes.com.br/"


def inspect(page) -> dict:
    identify_hits: list[str] = []
    page.on(
        "request",
        lambda req: identify_hits.append(req.url)
        if "identificar" in req.url or "verificar" in req.url
        else None,
    )
    page.goto(LOJA, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.get_by_role("button", name="Identifique-se").click()
    page.wait_for_timeout(600)
    panel = page.get_by_role("dialog", name="Situação da conta")
    admin = page.get_by_role("form", name="Acesso administrativo")
    return {
        "url": page.url,
        "email": page.get_by_label("E-mail cadastrado").count(),
        "cpf_visible": page.get_by_label("CPF do cadastro").count(),
        "code": page.get_by_label("Código de acesso").count(),
        "enter": page.get_by_role("button", name="Entrar", exact=True).count(),
        "receive": page.get_by_role("button", name="Receber código").count(),
        "admin_link": page.get_by_role("link", name="Acesso administrativo").count(),
        "admin_form": admin.count(),
        "admin_user": page.get_by_label("Usuário").count(),
        "panel_text": " ".join(panel.inner_text().split())[:500] if panel.count() else "",
        "identify_or_verify": identify_hits,
    }


def main() -> None:
    report: dict = {"kind": "production-inspection-only", "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        page = desktop.new_page()
        page.set_default_timeout(45000)
        data = inspect(page)
        report["pages"].append({"step": "prod-1440", **data})
        page.get_by_role("dialog", name="Situação da conta").screenshot(path=CAP / "prod-identifique-1440.png")
        desktop.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mpage = mobile.new_page()
        mpage.set_default_timeout(45000)
        report["pages"].append({"step": "prod-390", **inspect(mpage)})
        mpage.get_by_role("dialog", name="Situação da conta").screenshot(path=CAP / "prod-identifique-390.png")
        mobile.close()
        browser.close()

    (OUT / "verify-prod.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote verify-prod.json")


if __name__ == "__main__":
    main()
