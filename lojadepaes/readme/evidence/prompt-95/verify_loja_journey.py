"""Jornada pública Loja → Biblioteca → Ver planos. Sem contratação real."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
CAP = OUT / "captures"
CAP.mkdir(exist_ok=True)

LOJA = "https://lojadepaes.com.br"
PARAMS = "https://actionhub.com.br/loja?return_origin=https%3A%2F%2Flojadepaes.com.br&return_to=%2F%23biblioteca"
BARE = "https://actionhub.com.br/loja"


def shot(page, name: str) -> None:
    page.screenshot(path=CAP / name, full_page=True)


def main() -> None:
    report: dict = {"pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(45000)
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)[:240]))

        page.goto(f"{LOJA}/", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        shot(page, "prod-home-1440.png")
        report["pages"].append({"step": "home", "url": page.url, "identifique": page.get_by_role("button", name="Identifique-se").count() > 0})

        page.goto(f"{LOJA}/biblioteca/o-comeco", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        ver = page.get_by_role("link", name="Ver planos")
        report["pages"].append(
            {
                "step": "article",
                "url": page.url,
                "ver_planos": ver.count() > 0,
                "href": ver.first.get_attribute("href") if ver.count() else None,
            }
        )
        shot(page, "prod-article-1440.png")
        if ver.count() == 0:
            raise SystemExit("Ver planos ausente")
        href = ver.first.get_attribute("href") or ""
        if href.startswith("http"):
            page.goto(href, wait_until="domcontentloaded")
        else:
            ver.first.click()
        page.wait_for_timeout(4000)
        target = page
        body = target.inner_text("body")
        report["pages"].append(
            {
                "step": "ver-planos",
                "url": target.url,
                "crash_ui": "couldn" in body.lower() and "load" in body.lower(),
                "has_19": "19" in body,
                "has_10": "10" in body,
                "has_avulso": "avulso" in body.lower(),
                "has_mes": "/mês" in body or "por mês" in body,
                "errors": errors[:6],
                "snippet": " ".join(body.split())[:700],
            }
        )
        target.screenshot(path=CAP / "prod-hub-loja-from-ver-planos-1440.png", full_page=True)

        for name, url in (("params", PARAMS), ("bare", BARE)):
            page2 = context.new_page()
            page2_errors: list[str] = []
            page2.on("pageerror", lambda exc, bucket=page2_errors: bucket.append(str(exc)[:240]))
            page2.goto(url, wait_until="domcontentloaded")
            page2.wait_for_timeout(4000)
            text = page2.inner_text("body")
            report["pages"].append(
                {
                    "step": name,
                    "url": page2.url,
                    "crash_ui": "couldn" in text.lower() and "load" in text.lower(),
                    "has_19": "19" in text,
                    "has_avulso": "avulso" in text.lower(),
                    "errors": page2_errors[:6],
                    "snippet": " ".join(text.split())[:500],
                }
            )
            page2.screenshot(path=CAP / f"prod-hub-loja-{name}-1440.png", full_page=True)
            page2.close()

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            is_mobile=True,
        )
        mpage = mobile.new_page()
        mpage.goto(PARAMS, wait_until="domcontentloaded")
        mpage.wait_for_timeout(4000)
        mtext = mpage.inner_text("body")
        report["pages"].append(
            {
                "step": "mobile-params",
                "crash_ui": "couldn" in mtext.lower() and "load" in mtext.lower(),
                "has_19": "19" in mtext,
                "has_avulso": "avulso" in mtext.lower(),
                "snippet": " ".join(mtext.split())[:400],
            }
        )
        mpage.screenshot(path=CAP / "prod-hub-loja-params-390.png", full_page=True)
        mobile.close()
        browser.close()

    (OUT / "verify-journey.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
