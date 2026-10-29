"""Capturas isoladas do login. API fictícia; sem e-mail nem senha reais."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:5175/"

UNIDENTIFIED = {"identified": False}
NONE = {
    "identified": True,
    "assinatura": {"status": "none", "status_label": "Sem assinatura", "authorized": False, "cancelable": False},
    "consultas_ia": {"monthly_credits": 0, "pack_credits": 0},
    "fidelidade": {"enrolled": False, "bread_credits": 0},
}


def mock_api(page, situacao: dict) -> None:
    page.unroute("**/api/**")

    def handle(route):
        url = route.request.url
        if "/conta/situacao" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(situacao))
            return
        if "/biblioteca/verificar" in url:
            route.fulfill(status=400, content_type="application/json", body=json.dumps({"detail": "código inválido ou expirado"}))
            return
        if "/admin/" in url:
            route.fulfill(status=401, content_type="application/json", body=json.dumps({"detail": "não autenticado"}))
            return
        route.fulfill(status=404, content_type="application/json", body="{}")

    page.route("**/api/**", handle)


def main() -> None:
    report: dict = {"kind": "isolated-fictional", "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(45000)
        mock_api(page, UNIDENTIFIED)
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="Identifique-se").click()
        page.wait_for_timeout(400)
        panel = page.get_by_role("dialog", name="Situação da conta")
        report["pages"].append(
            {
                "step": "isolated-initial-1440",
                "enter": page.get_by_role("button", name="Entrar").count(),
                "receive": page.get_by_role("button", name="Receber código").count(),
                "admin": page.get_by_role("link", name="Acesso administrativo").count(),
                "email": page.get_by_label("E-mail cadastrado").count(),
                "code": page.get_by_label("Código de acesso").count(),
            }
        )
        panel.screenshot(path=CAP / "isolated-initial-1440.png")

        page.get_by_label("E-mail cadastrado").fill("ana.ficticia@example.com")
        page.get_by_label("Código de acesso").fill("000000")
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(600)
        report["pages"].append(
            {
                "step": "isolated-error-1440",
                "status": page.get_by_role("status").inner_text() if page.get_by_role("status").count() else "",
                "email_kept": page.get_by_label("E-mail cadastrado").input_value(),
            }
        )
        panel.screenshot(path=CAP / "isolated-error-1440.png")

        mock_api(page, NONE)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.get_by_role("button", name=re.compile(r"Assinatura\s+Sem assinatura", re.I)).click()
        page.wait_for_timeout(400)
        report["pages"].append(
            {
                "step": "isolated-auth-none-1440",
                "dialog": page.get_by_role("dialog").inner_text()[:400],
                "has_active_claim": "Assinatura ativa" in page.inner_text("body"),
            }
        )
        page.get_by_role("dialog", name="Situação da conta").screenshot(path=CAP / "isolated-auth-none-1440.png")

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mpage = mobile.new_page()
        mock_api(mpage, UNIDENTIFIED)
        mpage.goto(BASE, wait_until="domcontentloaded")
        mpage.wait_for_timeout(1500)
        mpage.get_by_role("button", name="Identifique-se").click()
        mpage.wait_for_timeout(400)
        mpage.get_by_role("dialog", name="Situação da conta").screenshot(path=CAP / "isolated-initial-390.png")
        narrow = browser.new_context(viewport={"width": 320, "height": 568})
        npage = narrow.new_page()
        mock_api(npage, UNIDENTIFIED)
        npage.goto(BASE, wait_until="domcontentloaded")
        npage.wait_for_timeout(1500)
        npage.get_by_role("button", name="Identifique-se").click()
        npage.wait_for_timeout(400)
        npage.screenshot(path=CAP / "isolated-initial-320.png")
        mobile.close()
        narrow.close()
        context.close()
        browser.close()

    (OUT / "isolated-verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote isolated-verify.json")


if __name__ == "__main__":
    main()
