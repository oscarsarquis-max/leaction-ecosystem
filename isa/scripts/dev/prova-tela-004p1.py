"""Prova pela tela do ensaio local. Não é uma prova do Cognito nem uma publicação."""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

from test_pg import prepare
import rehearsal_idp


def wait_health(port):
    deadline = time.time() + 15
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%s/api/health" % port, timeout=2) as response:
                body = response.read().decode("utf-8")
            if '"ok": true' in body and '"rehearsal": true' in body and '"database": "postgres"' in body:
                return body
            last = body
        except Exception as exc:
            last = str(exc)
        time.sleep(0.2)
    raise RuntimeError(last)


def start_prod(url):
    env = os.environ.copy()
    env.update({
        "ISA_ENV": "production",
        "ISA_DATABASE_URL": url,
        "ISA_PORT": "8099",
        "ISA_ORIGIN": "http://127.0.0.1:8099",
        "ISA_OIDC_REHEARSAL": "1",
        "ISA_OIDC_ISSUER": "http://127.0.0.1:8096",
        "ISA_OIDC_DISCOVERY": "http://127.0.0.1:8096/.well-known/openid-configuration",
        "ISA_OIDC_CLIENT_ID": "isa-ensaio",
        "ISA_OIDC_REDIRECT": "http://127.0.0.1:8099/callback",
        "ISA_OIDC_ALLOWED_SUBS": "teste-uma,teste-duas",
        "ISA_ERASURE_LEDGER": str(ROOT / "data" / "prova-tela-ledger.jsonl"),
    })
    proc = subprocess.Popen([sys.executable, str(SERVER / "prod_serve.py")], cwd=str(SERVER), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    line = proc.stdout.readline().decode("utf-8", "replace")
    if "ISA produ" not in line:
        raise RuntimeError(line)
    wait_health(8099)
    return proc


def login(page, sub):
    page.goto("http://127.0.0.1:8096/choose?sub=%s" % sub)
    page.goto("http://127.0.0.1:8099/#entrar")
    page.wait_for_selector("#enter-public")
    page.click("#enter-public")
    page.wait_for_selector("text=Sua conta")


def main():
    from playwright.sync_api import sync_playwright
    url = prepare("isa_screen")
    idp = rehearsal_idp.serve(8096)
    import threading
    threading.Thread(target=idp.serve_forever, daemon=True).start()
    proc = start_prod(url)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.goto("http://127.0.0.1:8099/#entrar")
            page.wait_for_selector("#enter-public")
            text = page.inner_text("body")
            if "Marina" in text or "Paulo" in text or "Eveline" in text:
                raise SystemExit("a página pública listou participante")
            if "provedor de ensaio" not in text:
                raise SystemExit("o ensaio não está distinguido do diretório real")
            login(page, "teste-uma")
            page.locator("#open-import").first.click()
            page.click("#load-synthetic")
            page.wait_for_selector("#import-go")
            page.click("#import-go")
            page.wait_for_selector("text=Entraram")
            page.locator("#open-import").first.click()
            page.click("#load-synthetic")
            page.click("#load-overlap")
            page.wait_for_selector("#import-go")
            page.click("#import-go")
            page.wait_for_selector("text=Entraram")
            page.click("#open-pending")
            page.wait_for_selector("text=É a mesma operação")
            pending_before = page.locator("text=É a mesma operação").count()
            if pending_before < 1:
                raise SystemExit("não ficou pendência")
            page.click("#nav-perfil")
            page.click("#leave")
            page.wait_for_selector("#enter-public")
            context.close()
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            login(page, "teste-uma")
            page.click("#nav-lista")
            page.wait_for_selector("text=Pix recebido")
            page.click("#open-pending")
            page.wait_for_selector("text=É a mesma operação")
            page.locator("text=É a mesma operação").first.click()
            page.wait_for_selector("text=Registrado como a mesma operação")
            context.close()
            proc.kill()
            proc.wait(timeout=5)
            proc = start_prod(url)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            login(page, "teste-uma")
            page.click("#nav-lista")
            page.wait_for_selector("h1", state="visible")
            page.wait_for_function("() => document.querySelector('h1') && document.querySelector('h1').textContent.indexOf('Lançamentos') >= 0")
            before = page.locator("#app .list .item").count()
            page.click("#open-pending")
            page.wait_for_selector("text=Decisão já registrada")
            page.click("#nav-lista")
            page.wait_for_function("() => document.querySelector('h1') && document.querySelector('h1').textContent.indexOf('Lançamentos') >= 0")
            page.locator("#open-import").first.click()
            page.click("#load-synthetic")
            page.wait_for_selector("text=Nenhuma ocorrência nova foi criada")
            page.click("#nav-lista")
            page.wait_for_function("() => document.querySelector('h1') && document.querySelector('h1').textContent.indexOf('Lançamentos') >= 0")
            after = page.locator("#app .list .item").count()
            if before != after or before < 1:
                raise SystemExit("a releitura mudou a lista: %s -> %s" % (before, after))
            context.close()
            context = browser.new_context()
            page = context.new_page()
            login(page, "teste-duas")
            body = page.inner_text("body")
            if "Pix recebido" in body or "Compra com cartão" in body or "É a mesma operação" in body:
                raise SystemExit("a outra pessoa viu o registro")
            page.click("#nav-lista")
            if "Pix recebido" in page.inner_text("body"):
                raise SystemExit("a outra pessoa leu o lançamento")
            print("prova tela ok", before)
            context.close()
            browser.close()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        idp.shutdown()


if __name__ == "__main__":
    main()
