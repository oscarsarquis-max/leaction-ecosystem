"""Logo da Loja nas páginas de planos. Sem contratação."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)

PLANS = "https://actionhub.com.br/loja"
PARAMS = (
    "https://actionhub.com.br/loja"
    "?return_origin=https%3A%2F%2Flojadepaes.com.br"
    "&return_to=%2F%23biblioteca"
)
LOGO = "https://actionhub.com.br/brands/lojadepaes.png"


def main() -> None:
    report: dict = {"pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(45000)

        logo_resp = page.request.get(LOGO)
        report["logo"] = {
            "url": LOGO,
            "status": logo_resp.status,
            "content_type": logo_resp.headers.get("content-type"),
            "bytes": len(logo_resp.body()),
        }

        for step, url in (("bare", PLANS), ("params", PARAMS)):
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            img = page.locator('img[alt*="Loja de Pães"]')
            box = img.bounding_box() if img.count() else None
            natural = img.evaluate(
                """el => ({nw: el.naturalWidth, nh: el.naturalHeight, w: el.clientWidth, h: el.clientHeight, complete: el.complete})"""
            ) if img.count() else None
            report["pages"].append(
                {
                    "step": step,
                    "url": page.url,
                    "logo_count": img.count(),
                    "box": box,
                    "natural": natural,
                    "has_19": "19" in page.inner_text("body"),
                    "has_avulso": "avulso" in page.inner_text("body").lower(),
                }
            )
            page.screenshot(path=CAP / f"prod-loja-{step}-1440.png", full_page=False)

        page.get_by_role("button", name="Quero este plano").first.click()
        page.wait_for_timeout(2000)
        img = page.locator('img[alt*="Loja de Pães"]')
        report["pages"].append(
            {
                "step": "contratar-mensal",
                "url": page.url,
                "logo_count": img.count(),
                "natural": img.evaluate(
                    """el => ({nw: el.naturalWidth, nh: el.naturalHeight, complete: el.complete})"""
                ) if img.count() else None,
            }
        )
        page.screenshot(path=CAP / "prod-contratar-mensal-1440.png", full_page=False)

        page.goto(PARAMS, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Comprar agora").first.click()
        page.wait_for_timeout(2000)
        img = page.locator('img[alt*="Loja de Pães"]')
        report["pages"].append(
            {
                "step": "contratar-avulso",
                "url": page.url,
                "logo_count": img.count(),
                "natural": img.evaluate(
                    """el => ({nw: el.naturalWidth, nh: el.naturalHeight, complete: el.complete})"""
                ) if img.count() else None,
            }
        )
        page.screenshot(path=CAP / "prod-contratar-avulso-1440.png", full_page=False)

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mpage = mobile.new_page()
        mpage.goto(PARAMS, wait_until="domcontentloaded")
        mpage.wait_for_timeout(2500)
        mimg = mpage.locator('img[alt*="Loja de Pães"]')
        report["pages"].append(
            {
                "step": "mobile-params",
                "logo_count": mimg.count(),
                "box": mimg.bounding_box() if mimg.count() else None,
                "natural": mimg.evaluate(
                    """el => ({nw: el.naturalWidth, nh: el.naturalHeight, complete: el.complete})"""
                ) if mimg.count() else None,
            }
        )
        mpage.screenshot(path=CAP / "prod-loja-params-390.png", full_page=False)
        mpage.get_by_role("button", name="Quero este plano").first.click()
        mpage.wait_for_timeout(2000)
        mpage.screenshot(path=CAP / "prod-contratar-mensal-390.png", full_page=False)
        mobile.close()
        browser.close()

    (OUT / "verify-logo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote verify-logo.json")


if __name__ == "__main__":
    main()
