#!/usr/bin/env python3
"""113 — Playwright B2C Mesa (homologador via check-email). Sem senhas."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-113-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 113]"


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
        empty_agenda = page.get_by_text("Nenhum compromisso neste dia.")
        err = page.locator("text=Não foi possível carregar o mural")
        info = {
            "label": label,
            "url": page.url,
            "mural_visible": mural.count() > 0,
            "heading_visible": heading.count() > 0,
            "chip_count": chip.count(),
            "marker_count": marker.count(),
            "empty_agenda_copy": empty_agenda.count() > 0,
            "mural_error": err.count() > 0,
            "body_has_marker": MARKER in (page.inner_text("body") or ""),
            "legend_has_comunicado": page.get_by_text("Comunicado da Escola").count() > 0,
            "pageerrors": logs,
        }
        day9 = page.locator("button").filter(has_text=re.compile(r"^9$"))
        if day9.count() > 0:
            day9.last.click()
            page.wait_for_timeout(1000)
        agenda_chip = page.get_by_text("Escola", exact=True)
        info["agenda_escola_chip"] = agenda_chip.count()
        info["day9_has_marker"] = MARKER in (page.inner_text("body") or "")
        info["compromissos_date"] = page.get_by_text("09/09/2026").count() > 0
        if agenda_chip.count() > 0:
            agenda_chip.first.click()
            page.wait_for_timeout(800)
            info["modal_has_marker"] = MARKER in (page.inner_text("body") or "")
        page.screenshot(path=str(OUT / f"{label}.png"), full_page=True)
        browser.close()
        return info


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "empty"
    print(json.dumps(snapshot(label), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
