#!/usr/bin/env python3
"""123 — Playwright Mesa B2C. Sem senhas. Homologador e inovador."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-123-shots")
BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 123]"


def login(page, email: str):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("#email", email)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2500)


def snapshot(email: str, label: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 700})
        page = context.new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(f"pageerror:{e}"))
        login(page, email)
        mural = page.get_by_label("Mural da escola")
        heading = page.get_by_text("Comunicados da instituição")
        chip = page.get_by_text("Comunicado da Escola")
        marker = page.get_by_text(MARKER)
        err = page.locator("text=Não foi possível carregar o mural")
        body = page.inner_text("body") or ""
        info = {
            "label": label,
            "email": email,
            "url": page.url,
            "mural_visible": mural.count() > 0,
            "heading_visible": heading.count() > 0,
            "chip_count": chip.count(),
            "marker_count": marker.count(),
            "mural_error": err.count() > 0,
            "body_has_marker": MARKER in body,
            "pageerrors": logs,
            "viewport": {"w": 1440, "h": 700},
            "scroll_y_max": page.evaluate("() => document.documentElement.scrollHeight - window.innerHeight"),
            "mural_overflow": None,
        }
        if mural.count() > 0:
            info["mural_overflow"] = mural.evaluate(
                """el => ({
                    tag: el.tagName,
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    overflowY: getComputedStyle(el).overflowY,
                    maxHeight: getComputedStyle(el).maxHeight,
                })"""
            )
            titles = mural.locator("p.font-semibold").all_inner_texts()
            info["mural_title_texts"] = [t for t in titles if t.strip()]
        page.screenshot(path=str(OUT / f"{label}.png"), full_page=True, timeout=60000)
        if info["scroll_y_max"] and info["scroll_y_max"] > 0:
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"{label}-scrolled.png"), full_page=False)
            info["scrolled"] = True
        page.goto(f"{BASE}/mesa-do-inovador", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        info["reload_marker_count"] = page.get_by_text(MARKER).count()
        info["reload_mural_error"] = page.locator("text=Não foi possível carregar o mural").count() > 0
        page.screenshot(path=str(OUT / f"{label}-reload.png"), full_page=True)
        browser.close()
        return info


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "homologador@leaction.com.br"
    label = sys.argv[2] if len(sys.argv) > 2 else "homolog"
    print(json.dumps(snapshot(email, label), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
