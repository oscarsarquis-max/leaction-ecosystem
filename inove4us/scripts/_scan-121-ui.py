#!/usr/bin/env python3
"""121 — Playwright B2C: Relato Área 2, trava 120, card lilás na Mesa. Sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\inove4us\scripts\_scan-121-shots")
STATE = Path(r"C:\Projetos\inove4us\scripts\_scan-121-state.json")
EMAIL = "homologador@leaction.com.br"
BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 121]"


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("#email", EMAIL)
    page.get_by_role("button", name="Continuar").click()
    page.wait_for_url("**/mesa-do-inovador**", timeout=45000)
    page.wait_for_timeout(2000)


def snap_mesa(page):
    body = page.inner_text("body") or ""
    return {
        "url": page.url,
        "has_marker": MARKER in body,
        "somente_leitura": "somente leitura" in body.lower() or "Somente leitura" in body,
        "banner_encerrado": "Desafio encerrado" in body,
        "registrar_concluir": page.get_by_role("button", name="Registrar e concluir aula").count(),
        "resposta_tag": "[Resposta à Proposta Metodológica]" in body,
        "aviso_geral_misturado": False,
        "lilac_hint": "Resposta à Proposta Metodológica" in body,
        "has_proposta": "proposta" in body.lower() and MARKER in body,
    }


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    did0 = st.get("d0")
    did = st.get("d1")
    did2 = st.get("d2")
    if not did:
        print(json.dumps({"error": "sem d1 no state"}, ensure_ascii=False))
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"d0": did0, "d1": did, "d2": did2, "suffix": st.get("suffix")}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 1100}).new_page()
        logs = []
        page.on("pageerror", lambda e: logs.append(str(e)))
        login(page)

        e0 = (st.get("eids0") or [None])[0]
        e1 = (st.get("eids1") or [None])[-1]
        e2 = (st.get("eids2") or [None])[0]

        # Relato Área 2 vive na mesa de execução (/execucao/:idEvento), não no painel gerencial
        if e0:
            page.goto(f"{BASE}/execucao/{e0}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            info["d0_execucao"] = snap_mesa(page)
            page.screenshot(path=str(OUT / "d0-execucao.png"), full_page=True)
            iniciar = page.get_by_role("button", name="Marcar aula em execução")
            if iniciar.count():
                iniciar.first.click()
                page.wait_for_timeout(1500)
            btn = page.get_by_role("button", name="Registrar e concluir aula")
            info["d0_botao_concluir_exec"] = btn.count()
            if btn.count():
                btn.first.click()
                page.wait_for_timeout(1500)
                dlg = page.inner_text("body") or ""
                info["relato"] = {
                    "aberto": "Fechamento da aula" in dlg or "Encerramento da aula" in dlg,
                    "area2": "Sugestão para a coordenação" in dlg,
                    "opcional": "Opcional" in dlg,
                    "copy_curadoria": "A curadoria só recebe" in dlg or "opcional" in dlg.lower(),
                }
                page.screenshot(path=str(OUT / "relato-area2.png"), full_page=True)
                cancel = page.get_by_role("button", name="Cancelar")
                if cancel.count():
                    cancel.first.click()
                    page.wait_for_timeout(800)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            info["d0_execucao_reabrir"] = snap_mesa(page)

        if did0:
            page.goto(f"{BASE}/desafios/{did0}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            info["d0_mesa"] = snap_mesa(page)
            btn = page.get_by_role("button", name="Registrar e concluir aula")
            info["d0_botao_concluir"] = btn.count()
            if btn.count():
                btn.first.click()
                page.wait_for_timeout(1500)
                dlg = page.inner_text("body") or ""
                info["relato"] = {
                    "aberto": "Fechamento da aula" in dlg or "Encerramento da aula" in dlg,
                    "area2": "Sugestão para a coordenação" in dlg,
                    "opcional": "Opcional" in dlg,
                    "nao_trava": "curadoria só recebe sugestão se você escrever" in dlg.lower()
                    or "A curadoria só recebe" in dlg,
                }
                page.screenshot(path=str(OUT / "relato-area2.png"), full_page=True)
                cancel = page.get_by_role("button", name="Cancelar")
                if cancel.count():
                    cancel.first.click()
                    page.wait_for_timeout(800)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            info["d0_reabrir"] = snap_mesa(page)
            page.screenshot(path=str(OUT / "d0-reabrir.png"), full_page=True)

        # D1 já encerrado na API — confirma trava 120 + possível card lilás
        page.goto(f"{BASE}/desafios/{did}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        info["d1_aberto"] = snap_mesa(page)
        page.screenshot(path=str(OUT / "d1-mesa-encerrado.png"), full_page=True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        info["d1_reabrir"] = snap_mesa(page)
        page.screenshot(path=str(OUT / "d1-mesa-reabrir.png"), full_page=True)

        if did2:
            page.goto(f"{BASE}/desafios/{did2}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            info["d2_aberto"] = snap_mesa(page)
            page.screenshot(path=str(OUT / "d2-mesa.png"), full_page=True)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            info["d2_reabrir"] = snap_mesa(page)

        if e1:
            page.goto(f"{BASE}/execucao/{e1}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            info["d1_execucao"] = snap_mesa(page)
            page.screenshot(path=str(OUT / "d1-execucao.png"), full_page=True)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            info["d1_execucao_reabrir"] = snap_mesa(page)

        if e2:
            page.goto(f"{BASE}/execucao/{e2}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            info["d2_execucao"] = snap_mesa(page)
            page.screenshot(path=str(OUT / "d2-execucao.png"), full_page=True)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            info["d2_execucao_reabrir"] = snap_mesa(page)

        # Home / Mesa do inovador — avisos não devem aparecer como gerais sem tag
        page.goto(f"{BASE}/mesa-do-inovador", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        home = page.inner_text("body") or ""
        info["home"] = {
            "has_marker": MARKER in home,
            "resposta_tag": "[Resposta à Proposta Metodológica]" in home,
            "url": page.url,
        }
        page.screenshot(path=str(OUT / "home.png"), full_page=True)

        info["pageerrors"] = logs
        browser.close()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
