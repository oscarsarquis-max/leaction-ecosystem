#!/usr/bin/env python3
"""120 — UI Mesa somente leitura após encerramento + reload."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us\scripts\_scan-120-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
DID = "b1349162-22d9-4d24-8d6d-dbca6200e1e7"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1200)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2500)


def snap(page):
    body = page.inner_text("body") or ""
    return {
        "url": page.url,
        "somente_leitura": "somente leitura" in body.lower() or "Somente leitura" in body,
        "banner_encerrado": "Desafio encerrado" in body,
        "puzzle": page.get_by_text("🧩").count(),
        "acrescentar": page.get_by_role("button", name="Acrescentar / ratificar aulas").count(),
        "has_marker": "[TESTE VARREDURA 120]" in body,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"did": DID}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 1100}).new_page()
        login(page)
        page.goto(f"{BASE}/desafios/{DID}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        info["aberto"] = snap(page)
        page.screenshot(path=str(OUT / "mesa-encerrado.png"), full_page=True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        info["reabrir"] = snap(page)
        page.screenshot(path=str(OUT / "mesa-reabrir.png"), full_page=True)
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
