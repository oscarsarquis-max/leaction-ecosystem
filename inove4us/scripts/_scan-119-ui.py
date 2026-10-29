#!/usr/bin/env python3
"""119 — Playwright Mesa do desafio (homologador, check-email). Sem senhas."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us\scripts\_scan-119-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 119]"
DID = "f062ff9f-b961-4224-b39b-e6df04efd59b"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2000)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"desafio_id": DID, "marker": MARKER}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(str(e)))
        login(page)
        page.goto(f"{BASE}/desafios/{DID}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        body = page.inner_text("body") or ""
        info["url"] = page.url
        info["has_marker"] = MARKER in body
        info["has_custom"] = "card custom mesa" in body
        info["has_catalogo_editado"] = "card catalogo" in body
        info["has_pei"] = "Adaptação PEI" in body or "PEI ·" in body
        info["has_puzzle"] = page.get_by_text("🧩").count() > 0
        info["puzzle_count"] = page.get_by_text("🧩").count()
        info["has_para_fazer"] = "Para Fazer" in body
        info["has_fazendo"] = "Fazendo" in body
        info["error_load"] = "Não foi possível abrir a mesa" in body
        info["pageerrors"] = logs
        page.screenshot(path=str(OUT / "mesa-1.png"), full_page=True)

        page.goto(f"{BASE}/mesa-do-inovador", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        home = page.inner_text("body") or ""
        info["home_has_marker"] = MARKER in home
        page.screenshot(path=str(OUT / "home.png"), full_page=True)

        page.goto(f"{BASE}/desafios/{DID}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        body2 = page.inner_text("body") or ""
        info["reabrir_has_marker"] = MARKER in body2
        info["reabrir_has_custom"] = "card custom mesa" in body2
        info["reabrir_has_pei"] = "Adaptação PEI" in body2 or "PEI ·" in body2
        info["reabrir_puzzle"] = page.get_by_text("🧩").count()
        page.screenshot(path=str(OUT / "mesa-reabrir.png"), full_page=True)
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
