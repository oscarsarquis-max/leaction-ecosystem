#!/usr/bin/env python3
"""113 — Playwright School Secretaria mural. Senha lida de arquivo local, nunca impressa."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-113-shots")
PW = Path(r"C:\Projetos\inove4us-school\scripts\_scan-113-pw.txt")
EMAIL = "operacional@escolateste.edu.br"
BASE = "https://school.inove4us.com.br"
MARKER = "[TESTE VARREDURA 113]"


def main():
    password = PW.read_text(encoding="utf-8").strip()
    OUT.mkdir(parents=True, exist_ok=True)
    label = sys.argv[1] if len(sys.argv) > 1 else "school"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(str(e)))
        page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        info = {"url_after_acesso": page.url, "title": page.title()}
        # gatekeeper?
        if "gatekeeper" in page.url or "bloqueado" in (page.inner_text("body") or "").lower():
            info["blocked"] = True
            page.screenshot(path=str(OUT / f"{label}-blocked.png"), full_page=True)
            print(json.dumps(info, ensure_ascii=False, indent=2))
            browser.close()
            return 0
        page.locator('input[type="email"]').fill(EMAIL)
        page.locator('input[type="password"]').fill(password)
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(4000)
        info["url_after_login"] = page.url
        page.goto(f"{BASE}/secretaria", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        tab = page.get_by_role("button", name="Mural / Comunicações")
        if tab.count() == 0:
            tab = page.get_by_text("Mural / Comunicações")
        if tab.count() > 0:
            tab.first.click()
            page.wait_for_timeout(2000)
        info["url"] = page.url
        info["marker_count"] = page.get_by_text(MARKER).count()
        info["has_edit_button"] = page.get_by_role("button", name="Editar").count()
        info["has_cancel_button"] = page.get_by_role("button", name="Cancelar").count()
        info["empty_copy"] = page.get_by_text("Nenhum comunicado no mural.").count() > 0
        info["pageerrors"] = logs
        page.screenshot(path=str(OUT / f"{label}.png"), full_page=True)
        # fechar/reabrir
        page.goto(f"{BASE}/secretaria", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        tab2 = page.get_by_text("Mural / Comunicações")
        if tab2.count() > 0:
            tab2.first.click()
            page.wait_for_timeout(1500)
        info["reload_marker_count"] = page.get_by_text(MARKER).count()
        page.screenshot(path=str(OUT / f"{label}-reload.png"), full_page=True)
        browser.close()
        print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
