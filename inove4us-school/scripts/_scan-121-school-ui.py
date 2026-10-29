#!/usr/bin/env python3
"""121 — Playwright School Radar Central de Ações. Senha só de arquivo local, nunca impressa."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-121-shots")
PW = Path(r"C:\Projetos\inove4us-school\scripts\_scan-113-pw.txt")
EMAIL = "operacional@escolateste.edu.br"
BASE = "https://school.inove4us.com.br"
MARKER = "[TESTE VARREDURA 121]"


def main():
    password = PW.read_text(encoding="utf-8").strip() if PW.exists() else ""
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"password_file": PW.exists(), "email": EMAIL}
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
            page.screenshot(path=str(OUT / "school-blocked.png"), full_page=True)
            info["pageerrors"] = logs
            print(json.dumps(info, ensure_ascii=False, indent=2))
            browser.close()
            return 0
        page.locator('input[type="email"]').fill(EMAIL)
        if password:
            page.locator('input[type="password"]').fill(password)
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(4000)
        info["after_login_url"] = page.url
        body = page.inner_text("body") or ""
        info["login_ok"] = "/acesso" not in page.url
        info["has_central"] = "Central de ações" in body
        info["has_curadoria"] = "Curadoria pendente" in body or "sugestões de metodologia" in body
        info["has_marker"] = MARKER in body
        info["has_indice_copy"] = "sem identificação" in body.lower() or "agregado da escola" in body.lower()
        page.screenshot(path=str(OUT / "radar.png"), full_page=True)

        if info["login_ok"]:
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            body2 = page.inner_text("body") or ""
            info["reabrir"] = {
                "url": page.url,
                "has_central": "Central de ações" in body2,
                "has_marker": MARKER in body2,
            }
            page.screenshot(path=str(OUT / "radar-reabrir.png"), full_page=True)

            page.goto(f"{BASE}/editor-pedagogico?pilar=metodologias", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            ed = page.inner_text("body") or ""
            info["editor"] = {
                "url": page.url,
                "has_contribuicao": "Contribuição metodológica" in ed,
                "agregado_copy": "sem identificação" in ed.lower() or "agregado da escola" in ed,
                "has_marker": MARKER in ed,
                "retorno_label": "Retorno ao docente" in ed,
                "aprovar": page.get_by_role("button", name="Aprovar").count(),
            }
            page.screenshot(path=str(OUT / "editor.png"), full_page=True)
        info["pageerrors"] = logs
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
