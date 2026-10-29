"""Diagnóstico /loja: console, pageerror, rede, crash. Sem cobrança."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
CAPTURES = OUT / "captures"
CAPTURES.mkdir(exist_ok=True)

URLS = [
    ("loja-bare", "https://actionhub.com.br/loja"),
    (
        "loja-params",
        "https://actionhub.com.br/loja?return_origin=https%3A%2F%2Flojadepaes.com.br&return_to=%2F%23biblioteca",
    ),
    ("hub-home", "https://actionhub.com.br/"),
    ("hub-ecossistema", "https://actionhub.com.br/ecossistema"),
    ("brand-png", "https://actionhub.com.br/brands/lojadepaes.png"),
]


def probe(page, name: str, url: str) -> dict:
    console: list[dict] = []
    page_errors: list[str] = []
    failed: list[dict] = []
    responses: list[dict] = []

    page.on("console", lambda msg: console.append({"type": msg.type, "text": msg.text[:400]}))
    page.on("pageerror", lambda exc: page_errors.append(str(exc)[:500]))
    page.on(
        "requestfailed",
        lambda req: failed.append(
            {"url": req.url[:180], "error": (req.failure or "")[:160]}
        ),
    )
    page.on(
        "response",
        lambda resp: responses.append({"url": resp.url[:180], "status": resp.status})
        if any(key in resp.url for key in ("/loja", "catalog", "brands", "hub-api", "/_next/"))
        else None,
    )

    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    body = ""
    try:
        body = page.inner_text("body")
    except Exception as exc:
        body = f"<inner_text failed: {exc}>"
    title = ""
    try:
        title = page.title()
    except Exception as exc:
        title = f"<title failed: {exc}>"
    page.screenshot(path=CAPTURES / f"diag-{name}.png", full_page=True)
    return {
        "name": name,
        "url": url,
        "final_url": page.url,
        "title": title,
        "crash_ui": "couldn" in body.lower() and "load" in body.lower(),
        "has_planos": "Planos da Loja" in body or "Assinatura da Biblioteca" in body,
        "has_19": "19" in body,
        "has_avulso": "avulso" in body.lower(),
        "snippet": " ".join(body.split())[:500],
        "page_errors": page_errors[:8],
        "console": [item for item in console if item["type"] in {"error", "warning"}][:12],
        "failed": failed[:12],
        "responses": [item for item in responses if item["status"] >= 400][:12],
    }


def main() -> None:
    report = {"pages": []}
    with sync_playwright() as api:
        browser = api.chromium.launch(channel="chrome")
        for name, url in URLS:
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_timeout(25000)
            try:
                report["pages"].append(probe(page, name, url))
            except Exception as exc:
                report["pages"].append({"name": name, "url": url, "fatal": str(exc)[:400]})
            context.close()
        browser.close()
    (OUT / "diagnose-loja.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
