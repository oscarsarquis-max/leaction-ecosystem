#!/usr/bin/env python3
"""114 — Playwright B2C Mesa (homologador via check-email). Sem senhas."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-114-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 114]"
CANCELLED = "[TESTE VARREDURA 114] publicado agora fuso"
EXPIRED = "[TESTE VARREDURA 114] vigencia expirada"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2500)


def snapshot(label: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(f"pageerror:{e}"))
        login(page)
        mural = page.get_by_label("Mural da escola")
        heading = page.get_by_text("Comunicados da instituição")
        chip = page.get_by_text("Comunicado da Escola")
        marker = page.get_by_text(MARKER)
        err = page.locator("text=Não foi possível carregar o mural")
        info = {
            "label": label,
            "url": page.url,
            "mural_visible": mural.count() > 0,
            "heading_visible": heading.count() > 0,
            "chip_count": chip.count(),
            "marker_count": marker.count(),
            "mural_error": err.count() > 0,
            "body_has_marker": MARKER in (page.inner_text("body") or ""),
            "mural_has_agora_cancelado": CANCELLED in (page.inner_text("body") or ""),
            "mural_has_expirado": EXPIRED in (page.inner_text("body") or ""),
            "pageerrors": logs,
        }
        day8 = page.locator("button").filter(has_text=re.compile(r"^8$"))
        if day8.count() > 0:
            day8.last.click()
            page.wait_for_timeout(1000)
        agenda_chip = page.get_by_text("Escola", exact=True)
        info["agenda_escola_chip"] = agenda_chip.count()
        info["day8_has_marker"] = MARKER in (page.inner_text("body") or "")
        info["day8_has_agora"] = CANCELLED in (page.inner_text("body") or "")
        info["compromissos_date"] = page.get_by_text("08/09/2026").count() > 0
        if agenda_chip.count() > 0:
            agenda_chip.first.click()
            page.wait_for_timeout(800)
            info["modal_has_marker"] = MARKER in (page.inner_text("body") or "")
            info["modal_readonly"] = page.get_by_text("somente leitura").count() > 0 or page.get_by_text("Somente leitura").count() > 0
        page.screenshot(path=str(OUT / f"{label}.png"), full_page=True)
        page.goto(f"{BASE}/mesa-do-inovador", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        info["reload_marker_count"] = page.get_by_text(MARKER).count()
        info["reload_has_agora"] = CANCELLED in (page.inner_text("body") or "")
        page.screenshot(path=str(OUT / f"{label}-reload.png"), full_page=True)
        browser.close()
        return info


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "mesa"
    print(json.dumps(snapshot(label), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
