"""Prova de contas no laboratório. Não usa a conta publicada."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "documents" / "reviews" / "contas-004ia4"
PORT = 8137


def start_server(data):
    env = os.environ.copy()
    env.update({"ISA_ENV": "lab", "ISA_DATA": str(data), "ISA_PORT": str(PORT), "ISA_BACKUP_ROOT": str(data / "backups")})
    (data / "backups").mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "serve.py")], cwd=str(ROOT / "server"), env=env)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%s/api/health" % PORT, timeout=1) as response:
                if response.status == 200:
                    return proc
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("servidor local não subiu")


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=False)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-contas-"))
    proc = start_server(tmp)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-paulo")
            page.wait_for_selector("#account-switch")
            page.wait_for_selector("#brand-leave")
            if page.locator("#account-switch option").all_inner_texts() != ["Todas as contas"]:
                raise RuntimeError("a primeira visão não abre em todas as contas")
            page.click("#desk-contas")
            page.wait_for_function("() => document.body.innerText.includes('Cadastre sua primeira conta')")
            shot(page, "contas-vazia-1280.png")
            page.click("a[href='#contas/nova']")
            page.fill("#acc-name", "Corrente")
            page.fill("#acc-institution", "Banco do Brasil")
            page.select_option("#acc-currency", "BRL")
            page.click("#account-save")
            page.wait_for_function("() => document.body.innerText.includes('Conta salva')")
            page.click("a[href='#contas/nova']")
            page.fill("#acc-name", "Viagem")
            page.fill("#acc-institution", "Instituição informada")
            page.select_option("#acc-currency", "USD")
            page.click("#account-save")
            page.wait_for_function("() => document.body.innerText.includes('Viagem') && document.body.innerText.includes('USD')")
            shot(page, "contas-lista-1280.png")
            with page.expect_response(lambda response: "/api/accounts/select" in response.url and response.status == 200):
                page.select_option("#account-switch", label="Viagem · Instituição informada · USD")
            page.goto("http://127.0.0.1:%s/#inicio" % PORT)
            page.wait_for_function("() => document.body.innerText.includes('Ainda não informado') || document.body.innerText.includes('moeda')")
            shot(page, "conta-usd-1280.png")
            page.select_option("#account-switch", "all")
            page.wait_for_function("() => document.body.innerText.includes('não há um total em reais') && !document.body.innerText.includes('R$ 0,00') && !document.body.innerText.includes('US$ 0,00')")
            shot(page, "todas-moedas-1280.png")
            page.click("#desk-perfil")
            page.wait_for_function("() => document.body.innerText.includes('Claude pela AWS') && !document.body.innerText.includes('não uma inteligência')")
            shot(page, "perfil-1280.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(200)
            shot(page, "todas-390.png")
            page.set_viewport_size({"width": 360, "height": 740})
            page.wait_for_timeout(200)
            narrow = page.evaluate("""() => ({
              scroll: document.documentElement.scrollWidth > window.innerWidth + 1,
              bar: document.querySelector('.brand-bar').scrollWidth > document.querySelector('.brand-bar').clientWidth + 1,
              leave: !!document.querySelector('#brand-leave')
            })""")
            if narrow["scroll"] or narrow["bar"] or not narrow["leave"]:
                raise RuntimeError("cabeçalho estreito: %s" % narrow)
            shot(page, "marca-360.png")
            page.click("#brand-leave")
            page.wait_for_selector("#enter-paulo")
            browser.close()
            print("prova de contas ok")
    finally:
        proc.kill()
        proc.wait(timeout=5)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
