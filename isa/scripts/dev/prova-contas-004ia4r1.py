"""Prova visual do cadastro de contas. Dados sintéticos no laboratório, sem a conta publicada."""
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
SHOTS = ROOT / "documents" / "reviews" / "contas-004ia4r1"
PORT = 8138


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


def overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-contas-r1-"))
    proc = start_server(tmp)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-paulo")
            page.wait_for_selector("#account-switch")
            page.wait_for_selector("#brand-leave")
            text = page.locator("body").inner_text()
            if "Gerenciar contas" in text or "Você" == page.locator("#brand-person").inner_text():
                raise RuntimeError("cabeçalho ainda mistura gestão ou nome genérico")
            if page.locator("#brand-person").inner_text() != "Paulo Nunes":
                raise RuntimeError("nome do laboratório não apareceu")
            if page.locator("#account-switch option").first.inner_text() != "Todas as contas":
                raise RuntimeError("a primeira visão não abre em todas as contas")
            page.click("#desk-perfil")
            page.fill("#profile-name", "Pessoa da prova")
            page.click("#save-profile")
            page.wait_for_function("() => { const node = document.querySelector('#brand-person'); return !!node && node.textContent === 'Pessoa da prova'; }")
            shot(page, "perfil-1280.png")
            page.click("#brand-leave")
            page.wait_for_selector("#enter-paulo")
            page.go_back()
            page.wait_for_timeout(400)
            if page.locator("#brand-person").count() and page.locator("#brand-person").inner_text() == "Pessoa da prova":
                raise RuntimeError("voltar depois de sair reabriu a sessão")
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-paulo")
            page.wait_for_function("() => { const node = document.querySelector('#brand-person'); return !!node && node.textContent === 'Pessoa da prova'; }")
            page.click("#desk-perfil")
            page.click("#other")
            page.wait_for_function("() => document.querySelector('#brand-person') && document.querySelector('#brand-person').textContent.includes('Marina')")
            if "Pessoa da prova" in page.locator("#brand-person").inner_text():
                raise RuntimeError("o nome vazou para a outra pessoa")
            page.click("#desk-perfil")
            page.click("#other")
            page.wait_for_function("() => { const node = document.querySelector('#brand-person'); return !!node && node.textContent === 'Pessoa da prova'; }")
            page.click("#desk-contas")
            page.wait_for_function("() => document.body.innerText.includes('Adicione sua primeira conta')")
            shot(page, "contas-vazia-1280.png")
            page.set_viewport_size({"width": 1280, "height": 900})
            page.click("#add-account")
            page.wait_for_selector("#acc-institution")
            shot(page, "cadastro-1280.png")
            page.click("#account-save")
            page.wait_for_selector("#acc-institution-error")
            if page.locator("#saveerror").is_visible():
                raise RuntimeError("faixa de erro sem falha de servidor")
            page.fill("#acc-institution", "Banco do Brasil")
            page.fill("#acc-number", "0012345-6")
            page.select_option("#acc-kind", "corrente")
            page.click("#contact-section")
            page.fill("#acc-bank-email", "sem-arroba")
            page.click("#account-save")
            page.wait_for_selector("#acc-bank-email-error")
            page.fill("#acc-bank-email", "")
            page.click("#account-save")
            page.wait_for_function("() => document.body.innerText.includes('Conta salva')")
            if "0012345-6" in page.locator("body").inner_text():
                raise RuntimeError("a lista mostrou o número completo")
            shot(page, "contas-lista-1280.png")
            page.click("text=Abrir conta")
            page.wait_for_selector("#tab-acesso")
            if page.locator("text=Conectar banco").count():
                raise RuntimeError("botão de conexão sem serviço")
            shot(page, "acesso-1280.png")
            page.click("#tab-dados")
            page.wait_for_function("() => document.body.innerText.includes('0012345-6')")
            shot(page, "dados-1280.png")
            for width, height, name in ((1440, 900, "lista-1440.png"), (768, 1024, "lista-768.png"), (390, 844, "lista-390.png"), (360, 740, "lista-360.png")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto("http://127.0.0.1:%s/#contas" % PORT)
                page.wait_for_selector("#brand-leave")
                if overflow(page):
                    raise RuntimeError("estouro horizontal em %s" % width)
                shot(page, name)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto("http://127.0.0.1:%s/#contas/nova" % PORT)
            page.wait_for_selector("#account-save")
            shot(page, "cadastro-390.png")
            browser.close()
        print("prova de contas r1 ok")
    finally:
        proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
