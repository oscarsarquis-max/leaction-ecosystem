#!/usr/bin/env python3
"""119 — UI: Mesa do desafio, 🧩 TEA no card custom, fechar/reabrir."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us\scripts\_scan-119-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
DID = "f062ff9f-b961-4224-b39b-e6df04efd59b"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1200)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2500)


def snap_body(page):
    body = page.inner_text("body") or ""
    return {
        "url": page.url,
        "has_custom": "card custom mesa" in body,
        "has_pei_catalogo": "Adaptação PEI: [TESTE VARREDURA 119] card catalogo" in body
        or "Adaptação PEI" in body,
        "has_pei_custom": "Adaptação PEI: [TESTE VARREDURA 119] card custom" in body,
        "puzzle": page.get_by_text("🧩").count(),
        "has_modal_aulas": "Acrescentar / ratificar aulas" in body
        or "Acrescentar" in body and "aulas" in body.lower(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"did": DID}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 1100}).new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(str(e)))
        login(page)
        page.get_by_text("[TESTE VARREDURA 119] kanban").first.click()
        page.wait_for_url(f"**/desafios/{DID}**", timeout=30000)
        page.wait_for_timeout(3000)
        info["apos_click_home"] = snap_body(page)
        page.screenshot(path=str(OUT / "ui2-aberto.png"), full_page=True)

        cancel = page.get_by_role("button", name="Cancelar")
        if cancel.count():
            cancel.first.click()
            page.wait_for_timeout(800)
        info["apos_cancelar_modal"] = snap_body(page)

        puzzles = page.get_by_text("🧩")
        info["puzzle_visible"] = puzzles.count()
        if puzzles.count():
            puzzles.first.click()
            page.wait_for_timeout(800)
            tea = page.get_by_role("menuitem", name="TEA")
            if tea.count() == 0:
                tea = page.get_by_text("TEA (Espectro Autista)")
            info["menu_tea"] = tea.count()
            if tea.count():
                tea.first.click()
                page.wait_for_timeout(8000)
        info["apos_pei_ui"] = snap_body(page)
        page.screenshot(path=str(OUT / "ui2-pei.png"), full_page=True)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        cancel2 = page.get_by_role("button", name="Cancelar")
        if cancel2.count():
            cancel2.first.click()
            page.wait_for_timeout(600)
        info["reabrir"] = snap_body(page)
        info["pageerrors"] = logs
        page.screenshot(path=str(OUT / "ui2-reabrir.png"), full_page=True)
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
