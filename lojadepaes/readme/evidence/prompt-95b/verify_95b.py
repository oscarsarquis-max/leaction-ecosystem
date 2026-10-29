"""95B — jornada visual em produção. Sem submit, e-mail, cobrança ou mutação."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)

HUB = "https://actionhub.com.br"
LOJA = "https://lojadepaes.com.br"
PARAMS = (
    f"{HUB}/loja"
    "?return_origin=https%3A%2F%2Flojadepaes.com.br"
    "&return_to=%2F%23biblioteca"
)
CONSENT = (
    "Ao confirmar a contratação, você autoriza a cobrança de R$ 19,00 por mês neste cartão."
)
EMAIL_HINT = "Use o e-mail do seu cadastro na Loja de Pães"
PACK_CONSENT = "Não é assinatura e não renova sozinho"
FORBIDDEN = (
    "Cancele no ActionHub",
    "identifica o contrato no ActionHub",
    "Renovação automática mensal autorizada neste cartão",
    "Pedido da fornada",
)


def body_flags(text: str) -> dict:
    low = text.lower()
    return {
        "has_19": "19" in text,
        "has_10": "10" in text,
        "has_assinatura_biblioteca": "sua assinatura da biblioteca" in low,
        "has_consultas_ia": "suas consultas de ia" in low,
        "has_planos_biblioteca": "planos da biblioteca" in low,
        "has_consent": CONSENT in text,
        "has_email_hint": EMAIL_HINT in text,
        "has_pack_consent": PACK_CONSENT.lower() in low,
        "has_no_email_auth": "não enviamos e-mail para autorizar" in low,
        "has_mercadopago": "mercado pago" in low,
        "has_actionhub_customer": any(item.lower() in low for item in FORBIDDEN),
        "forbidden_hits": [item for item in FORBIDDEN if item.lower() in low],
        "crash_ui": "couldn't load" in low or "this page couldn’t load" in low,
        "snippet": " ".join(text.split())[:900],
    }


def inspect_form(page) -> dict:
    return {
        "email": page.get_by_label("E-mail cadastrado").count(),
        "cpf": page.get_by_label("CPF do cadastro").count(),
        "code": page.get_by_label("Código de acesso").count(),
        "enter": page.get_by_role("button", name="Entrar", exact=True).count(),
        "receive": page.get_by_role("button", name="Receber código").count(),
        "admin": page.get_by_role("button", name="Entrar como administrador").count(),
    }


def main() -> None:
    report: dict = {"pages": [], "assets": {}, "network_identify": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")

        logo = None
        try:
            logo = browser.new_context().request.get(f"{HUB}/brands/lojadepaes.png")
            report["assets"]["logo"] = {
                "status": logo.status,
                "content_type": logo.headers.get("content-type"),
                "bytes": len(logo.body()),
            }
        except Exception as exc:
            report["assets"]["logo"] = {"error": type(exc).__name__}

        health_hub = browser.new_context().request.get(f"{HUB}/api/health")
        report["assets"]["hub_health"] = {
            "status": health_hub.status,
            "body": health_hub.text()[:240],
        }
        health_loja = browser.new_context().request.get(f"{LOJA}/api/v1/health")
        report["assets"]["loja_health"] = {
            "status": health_loja.status,
            "body": health_loja.text()[:240],
        }

        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(45000)
        errors: list[str] = []
        identify_calls: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)[:240]))
        page.on(
            "request",
            lambda req: identify_calls.append(req.url)
            if "identify" in req.url.lower() or "biblioteca/identificar" in req.url.lower()
            else None,
        )

        # Home Loja + Identifique-se (não clicar Receber código)
        page.goto(LOJA + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Identifique-se").click()
        page.wait_for_timeout(800)
        login = inspect_form(page)
        report["pages"].append(
            {
                "step": "loja-identifique-1440",
                "url": page.url,
                "login": login,
                "identify_requests": list(identify_calls),
                "has_gerenciar": page.get_by_role("button", name="Gerenciar assinatura").count(),
                "errors": errors[:6],
                "snippet": " ".join(page.inner_text("body").split())[:500],
            }
        )
        page.screenshot(path=CAP / "prod-loja-identifique-1440.png", full_page=True)

        # Hub planos
        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        html = page.content()
        build = re.search(r'"buildId":"([^"]+)"', html)
        report["assets"]["build_id"] = build.group(1) if build else None
        flags = body_flags(page.inner_text("body"))
        report["pages"].append(
            {
                "step": "hub-loja-params-1440",
                "url": page.url,
                "logo": page.locator('img[alt*="Loja de Pães"]').count(),
                "errors": errors[:6],
                **flags,
            }
        )
        page.screenshot(path=CAP / "prod-hub-loja-params-1440.png", full_page=True)

        page.goto(f"{HUB}/loja", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        flags = body_flags(page.inner_text("body"))
        report["pages"].append(
            {
                "step": "hub-loja-bare-1440",
                "url": page.url,
                "logo": page.locator('img[alt*="Loja de Pães"]').count(),
                **flags,
            }
        )
        page.screenshot(path=CAP / "prod-hub-loja-bare-1440.png", full_page=True)

        # Contratar assinatura — sem submit
        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Quero este plano").first.click()
        page.wait_for_timeout(2500)
        flags = body_flags(page.inner_text("body"))
        report["pages"].append(
            {
                "step": "contratar-assinatura-1440",
                "url": page.url,
                "logo": page.locator('img[alt*="Loja de Pães"]').count(),
                "cta": page.get_by_role("button", name="Ir para autorizar a assinatura").count(),
                "preparando_stuck": page.get_by_text("Preparando", exact=False).count() > 0
                and page.get_by_role("button", name="Ir para autorizar a assinatura").count() == 0,
                "errors": errors[:6],
                **flags,
            }
        )
        page.screenshot(path=CAP / "prod-hub-contratar-assinatura-1440.png", full_page=True)

        # Contratar pacote — sem submit
        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Comprar agora").first.click()
        page.wait_for_timeout(2500)
        flags = body_flags(page.inner_text("body"))
        report["pages"].append(
            {
                "step": "contratar-avulso-1440",
                "url": page.url,
                "logo": page.locator('img[alt*="Loja de Pães"]').count(),
                "cta": page.get_by_role("button", name="Ir para o pagamento do pacote").count(),
                "has_recurrence_auth": "autoriza a cobrança de R$ 19,00" in page.inner_text("body"),
                "errors": errors[:6],
                **flags,
            }
        )
        page.screenshot(path=CAP / "prod-hub-contratar-avulso-1440.png", full_page=True)

        # Mobile
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mpage = mobile.new_page()
        mpage.set_default_timeout(45000)
        mpage.goto(LOJA + "/", wait_until="domcontentloaded")
        mpage.wait_for_timeout(2500)
        mpage.get_by_role("button", name="Identifique-se").click()
        mpage.wait_for_timeout(800)
        report["pages"].append(
            {
                "step": "loja-identifique-390",
                "login": inspect_form(mpage),
            }
        )
        mpage.screenshot(path=CAP / "prod-loja-identifique-390.png", full_page=True)

        mpage.goto(PARAMS, wait_until="domcontentloaded")
        mpage.wait_for_timeout(2500)
        report["pages"].append(
            {
                "step": "hub-loja-params-390",
                "logo": mpage.locator('img[alt*="Loja de Pães"]').count(),
                **body_flags(mpage.inner_text("body")),
            }
        )
        mpage.screenshot(path=CAP / "prod-hub-loja-params-390.png", full_page=True)
        mpage.get_by_role("button", name="Quero este plano").first.click()
        mpage.wait_for_timeout(2500)
        report["pages"].append(
            {
                "step": "contratar-assinatura-390",
                "url": mpage.url,
                "cta": mpage.get_by_role("button", name="Ir para autorizar a assinatura").count(),
                **body_flags(mpage.inner_text("body")),
            }
        )
        mpage.screenshot(path=CAP / "prod-hub-contratar-assinatura-390.png", full_page=True)

        mobile.close()
        context.close()
        browser.close()

    report["network_identify"] = identify_calls
    (OUT / "verify-95b.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote verify-95b.json")


if __name__ == "__main__":
    main()
