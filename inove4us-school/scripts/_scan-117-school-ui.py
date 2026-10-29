#!/usr/bin/env python3
"""117 — Playwright School Minha Equipe. Senha de arquivo local, nunca impressa."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-117-shots")
PW = Path(r"C:\Projetos\inove4us-school\scripts\_scan-113-pw.txt")
EMAIL = "operacional@escolateste.edu.br"
BASE = "https://school.inove4us.com.br"
MARKER = "varredura117"


def main():
    password = PW.read_text(encoding="utf-8").strip() if PW.exists() else ""
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"password_file": PW.exists()}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(str(e)))
        page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        if page.locator('input[type="email"]').count() == 0:
            info["blocked"] = True
            info["url"] = page.url
            page.screenshot(path=str(OUT / "school-equipe-blocked.png"), full_page=True)
            print(json.dumps(info, ensure_ascii=False, indent=2))
            browser.close()
            return 0
        page.locator('input[type="email"]').fill(EMAIL)
        if password:
            page.locator('input[type="password"]').fill(password)
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(4000)
        info["url_after_login"] = page.url
        page.goto(f"{BASE}/equipe", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        body = page.inner_text("body") or ""
        info["equipe"] = {
            "url": page.url,
            "has_pendente": "Pendente" in body,
            "has_ativo": "Ativo" in body,
            "has_homologador": "homologador@leaction.com.br" in body,
            "has_varredura117": MARKER in body.lower() or "varredura117@" in body.lower(),
            "forbidden": "zona" in body.lower() and "acesso" in body.lower() or "não tem permissão" in body.lower(),
        }
        page.screenshot(path=str(OUT / "school-equipe.png"), full_page=True)
        page.goto(f"{BASE}/equipe", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        body2 = page.inner_text("body") or ""
        info["equipe_reload"] = {
            "has_homologador": "homologador@leaction.com.br" in body2,
            "has_varredura117": MARKER in body2.lower() or "varredura117@" in body2.lower(),
            "has_pendente": "Pendente" in body2,
        }
        page.screenshot(path=str(OUT / "school-equipe-reload.png"), full_page=True)
        info["pageerrors"] = logs
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
