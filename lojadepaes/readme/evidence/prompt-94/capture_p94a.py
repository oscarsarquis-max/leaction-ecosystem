"""Capturas 94A: UI pública publicada + cabeçalho autenticado em sandbox (intercept)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ORIGIN = "https://lojadepaes.com.br"
HUB = "https://actionhub.com.br/loja"
OUT = Path(__file__).resolve().parent / "captures"
OUT.mkdir(parents=True, exist_ok=True)

SANDBOX = {
    "identified": True,
    "name": "Ana 94A",
    "assinatura": {
        "label": "Assinatura",
        "status": "active",
        "status_label": "Assinatura ativa",
        "authorized": True,
        "subscriber_discount": True,
    },
    "consultas_ia": {
        "label": "Consultas de IA",
        "credits": 29,
        "monthly_credits": 19,
        "pack_credits": 10,
        "pack_expires": False,
        "can_use_ai": True,
    },
    "fidelidade": {
        "label": "Fidelidade / créditos de pão",
        "enrolled": True,
        "bread_credits": 2,
        "stamps_label": "2 carimbos",
    },
    "plans_href": "https://actionhub.com.br/loja",
}

CANCELLED = {
    **SANDBOX,
    "assinatura": {
        **SANDBOX["assinatura"],
        "status": "cancelled_with_access",
        "status_label": "Renovação cancelada · acesso vigente",
    },
}


def _bundle(html: str) -> str | None:
    match = re.search(r"/assets/index-[^\"']+\.(?:js|css)", html)
    return match.group(0) if match else None


def main() -> None:
    report: dict = {"env_public": "production", "env_auth": "sandbox-intercept", "pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch()
        for width, tag in ((1440, "1440"), (390, "390")):
            context = browser.new_context(viewport={"width": width, "height": 1100})
            page = context.new_page()
            page.set_default_timeout(45000)

            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            html = page.content()
            report["bundle"] = _bundle(html)
            identify = page.get_by_role("button", name="Identifique-se")
            report["pages"].append(
                {
                    "url": page.url,
                    "viewport": tag,
                    "identifique": identify.count() > 0,
                    "nao_assinante_precoce": "não assinante" in html.lower() or "sem assinatura" in (identify.inner_text() if identify.count() else ""),
                }
            )
            if identify.count():
                identify.first.click()
                page.wait_for_timeout(400)
            page.screenshot(path=OUT / f"prod-home-visitor-{tag}.png")

            page.goto(f"{ORIGIN}/biblioteca/o-comeco", wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            article = page.content()
            report["pages"].append(
                {
                    "url": page.url,
                    "viewport": tag,
                    "ver_planos": page.get_by_role("link", name="Ver planos").count() > 0,
                    "formulario_no_artigo": bool(re.search(r'name="cpf"|Confirmar identidade', article)),
                }
            )
            page.screenshot(path=OUT / f"prod-article-{tag}.png", full_page=True)

            page.goto(f"{ORIGIN}/biblioteca/calculadora", wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            page.screenshot(path=OUT / f"prod-calculator-{tag}.png")

            page.goto(HUB, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            hub_html = page.content()
            report["pages"].append(
                {
                    "url": page.url,
                    "viewport": tag,
                    "has_19": "19" in hub_html,
                    "has_10": "10" in hub_html,
                    "text_sample": re.sub(r"\s+", " ", page.inner_text("body"))[:800],
                }
            )
            page.screenshot(path=OUT / f"prod-hub-loja-{tag}.png", full_page=True)
            context.close()

        sandbox = browser.new_context(viewport={"width": 1440, "height": 900})
        page = sandbox.new_page()
        page.route(
            "**/api/v1/conta/situacao",
            lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(SANDBOX)),
        )
        page.goto(f"{ORIGIN}/", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        toggle = page.locator(".header-customer-toggle")
        if toggle.count():
            toggle.first.click()
            page.wait_for_timeout(400)
        page.screenshot(path=OUT / "sandbox-header-assinante-1440.png")

        page.route(
            "**/api/v1/conta/situacao",
            lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(CANCELLED)),
        )
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        if page.locator(".header-customer-toggle").count():
            page.locator(".header-customer-toggle").first.click()
            page.wait_for_timeout(400)
        page.screenshot(path=OUT / "sandbox-header-cancelada-1440.png")
        sandbox.close()
        browser.close()

    (OUT / "capture-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
