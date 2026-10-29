#!/usr/bin/env python3
"""117 — B2C UI: Instituições read-only + Dia a Dia aula solta (homologador)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us-school\scripts\_scan-117-shots")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2000)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.on("pageerror", lambda e: logs.append(str(e)))
        login(page)
        info = {"mesa_url": page.url}

        page.goto(f"{BASE}/instituicoes", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        body = page.inner_text("body") or ""
        info["instituicoes"] = {
            "url": page.url,
            "conta_institucional": "Conta institucional" in body,
            "copy_secretaria": "Secretaria do School" in body or "vêm da Secretaria" in body,
            "btn_nova_instituicao": page.get_by_role("button", name="Nova instituição").count()
            + page.get_by_role("button", name="Adicionar instituição").count()
            + page.get_by_text("Nova instituição").count(),
            "escola_teste": "Escola Teste" in body,
            "alocacao_6ano": "6º Ano" in body or "6º ano" in body,
            "matematica": "Matemática" in body,
            "readonly_inputs": page.locator("input[readonly]").count(),
        }
        page.screenshot(path=str(OUT / "b2c-instituicoes.png"), full_page=True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        body2 = page.inner_text("body") or ""
        info["instituicoes_reload"] = {
            "conta_institucional": "Conta institucional" in body2,
            "escola_teste": "Escola Teste" in body2,
        }
        page.screenshot(path=str(OUT / "b2c-instituicoes-reload.png"), full_page=True)

        page.goto(f"{BASE}/dia-a-dia/nova", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        body3 = page.inner_text("body") or ""
        info["dia_a_dia_nova"] = {
            "url": page.url,
            "tema_visible": page.locator("textarea, input").count(),
            "exige_instituicao": "vincule uma instituição" in body3.lower()
            or "vínculo pedagógico obrigatório" in body3.lower(),
            "bloqueado": "não é possível" in body3.lower() and "aula" in body3.lower(),
        }
        page.screenshot(path=str(OUT / "b2c-dia-a-dia-nova.png"), full_page=True)

        page.goto(f"{BASE}/acesso?email=varredura117@leaction.com.br&school_invite=1", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        body4 = page.inner_text("body") or ""
        info["acesso_convite"] = {
            "url": page.url,
            "hint_escola": "Convite da sua escola" in body4 or "school_invite" in page.url,
            "email_preenchido": (page.locator("#email").input_value() if page.locator("#email").count() else "")[:80],
        }
        page.screenshot(path=str(OUT / "b2c-acesso-convite.png"), full_page=True)
        info["pageerrors"] = logs
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
