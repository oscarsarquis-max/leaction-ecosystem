"""Prova visual do cadastro contínuo. Base sintética de laboratório, sem a conta publicada."""
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "documents" / "reviews" / "contas-004ia4r2"
PORT = 8142


def start_server(data):
    env = os.environ.copy()
    env.update({"ISA_ENV": "lab", "ISA_DATA": str(data), "ISA_PORT": str(PORT), "ISA_BACKUP_ROOT": str(data / "backups")})
    (data / "backups").mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "serve.py")], cwd=str(ROOT / "server"), env=env)
    deadline = time.time() + 20
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


def style_of(page, selector):
    return page.evaluate(
        """(selector) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const style = getComputedStyle(node);
          return { tag: node.tagName, size: style.fontSize, weight: style.fontWeight, text: node.textContent.trim().slice(0, 80) };
        }""",
        selector,
    )


def enter(page):
    page.goto("http://127.0.0.1:%s/#entrar" % PORT)
    page.click("#enter-paulo")
    page.wait_for_selector("text=Seu dinheiro")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-contas-r2-"))
    proc = start_server(tmp)
    notes = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            def fail_json(route):
                route.fulfill(status=500, content_type="application/json", body="{}")
            page.route("**/api/workspace", fail_json)
            page.route("**/api/accounts", fail_json)
            enter(page)
            page.click("#desk-contas")
            page.wait_for_selector("text=Não foi possível carregar as contas")
            if page.locator("text=Adicione sua primeira conta").count():
                raise RuntimeError("falha de rede apareceu como lista vazia")
            shot(page, "lista-erro-1280.png")
            page.unroute_all()
            page.reload()
            enter(page)
            page.click("#desk-contas")
            page.wait_for_selector("text=Adicione sua primeira conta")
            if page.locator("#add-account").count():
                raise RuntimeError("o botão do topo apareceu junto da lista vazia")
            if page.locator("text=Adicionar conta").count() != 1:
                raise RuntimeError("a lista vazia não tem uma única chamada")
            shot(page, "lista-vazia-1280.png")
            page.click("text=Adicionar conta")
            page.wait_for_selector("#acc-institution")
            if page.locator("summary").count():
                raise RuntimeError("o formulário ainda esconde campos")
            if page.locator("#acc-currency").count() != 1 or not page.locator("#acc-currency").is_visible():
                raise RuntimeError("a moeda não está visível")
            if "BRL" not in page.locator("#acc-currency").input_value() and page.locator("#acc-currency").input_value() != "BRL":
                raise RuntimeError("a moeda padrão não é BRL")
            page.locator("#acc-institution").fill("Brasil")
            page.wait_for_selector("#bank-listbox [role=option]")
            if "001 — Banco do Brasil" not in page.locator("#bank-listbox").inner_text():
                raise RuntimeError("Brasil não encontrou 001 — Banco do Brasil")
            page.locator("#acc-institution").fill("")
            page.locator("#acc-institution").fill("1")
            page.wait_for_selector("#bank-listbox [role=option]")
            if "001 — Banco do Brasil" not in page.locator("#bank-listbox").inner_text():
                raise RuntimeError("a consulta 1 não encontrou o código 001")
            page.locator("#acc-institution").fill("001")
            page.wait_for_selector("#bank-listbox [role=option]")
            page.locator("#acc-institution").press("ArrowDown")
            page.locator("#acc-institution").press("Enter")
            if page.locator("#acc-institution").input_value() != "001 — Banco do Brasil":
                raise RuntimeError("Enter não escolheu o banco")
            page.locator("#acc-institution").fill("brasil")
            page.wait_for_timeout(100)
            if page.locator("#acc-institution").get_attribute("data-bank-name"):
                raise RuntimeError("editar a busca manteve a seleção anterior")
            page.locator("#bank-listbox [role=option]").first.click()
            if page.locator("#acc-institution").get_attribute("data-bank-code") != "001":
                raise RuntimeError("o clique não gravou o código")
            page.fill("#acc-number", "0012345-6")
            page.select_option("#acc-kind", "corrente")
            page.fill("#acc-agency", "0123-4")
            page.fill("#acc-agency-name", "Agência Centro")
            shot(page, "formulario-topo-1280.png")
            page.locator("#contact-section").scroll_into_view_if_needed()
            shot(page, "formulario-contatos-1280.png")
            h1 = style_of(page, "h1")
            h2 = style_of(page, "h2")
            h3 = style_of(page, "#contact-list h3")
            notes.append({"h1": h1, "h2": h2, "h3": h3})
            if h1["size"] != "28px" or h1["weight"] not in ("700", "bold"):
                raise RuntimeError("H1 desktop fora da escala: %s" % h1)
            if h2["size"] != "20px":
                raise RuntimeError("H2 desktop fora da escala: %s" % h2)
            if h3["size"] != "16px":
                raise RuntimeError("H3 desktop fora da escala: %s" % h3)
            page.click("#account-save")
            try:
                page.wait_for_selector("#add-account", timeout=8000)
            except Exception:
                banner = page.locator("#saveerror")
                detail = banner.inner_text() if banner.count() else page.locator("body").inner_text()[:500]
                raise RuntimeError("não saiu do formulário: %s" % detail)
            if page.locator("text=Adicione sua primeira conta").count():
                raise RuntimeError("a lista preenchida repetiu o convite vazio")
            shot(page, "lista-preenchida-1280.png")
            page.click("text=Abrir conta")
            page.click("text=Editar dados")
            page.wait_for_selector("#acc-agency-name")
            if page.locator("#acc-agency-name").input_value() != "Agência Centro":
                raise RuntimeError("o nome da agência não voltou")
            if page.locator("#acc-agency").input_value() != "0123-4":
                raise RuntimeError("o código da agência não voltou")
            edit_url = page.url
            db = sqlite3.connect(tmp / "isa.sqlite")
            db.execute("UPDATE account SET nickname = ?, country = ?, account_digit = ?, agency_email = ? WHERE account_number = ?", ("Casa", "Brasil", "7", "agencia@exemplo.com", "0012345-6"))
            db.commit()
            kept_row = db.execute("SELECT nickname, account_digit FROM account").fetchone()
            db.close()
            if not kept_row or kept_row[0] != "Casa":
                raise RuntimeError("a base de laboratório não recebeu o apelido: %s" % (kept_row,))
            page.reload()
            try:
                page.wait_for_selector("text=Já registrados nesta conta", timeout=8000)
            except Exception:
                payload = page.evaluate("""async () => {
                  const response = await fetch('/api/workspace', { headers: { 'X-ISA-Lab-Person': 'paulo' } });
                  const data = await response.json();
                  const account = (data.accounts || [])[0] || {};
                  const saved = JSON.parse(sessionStorage.getItem('isa-demo-v1') || '{}');
                  const stored = (saved.accounts || [])[0] || {};
                  return JSON.stringify({ status: response.status, nickname: account.nickname, stored: stored.nickname, person: saved.personId });
                }""")
                raise RuntimeError(str(payload) + " | " + " / ".join(str(item) for item in notes))
            kept = page.locator("text=Já registrados nesta conta").locator("xpath=..").inner_text()
            if "Casa" not in kept or "7" not in kept or "agencia@exemplo.com" not in kept:
                raise RuntimeError("os dados legados não apareceram: %s" % kept)
            page.click("#account-save")
            page.wait_for_selector("#desk-contas")
            row = sqlite3.connect(tmp / "isa.sqlite").execute("SELECT nickname, country, account_digit, agency_email, agency_name, bank_code FROM account").fetchone()
            if row != ("Casa", "Brasil", "7", "agencia@exemplo.com", "Agência Centro", "001"):
                raise RuntimeError("a edição apagou um dado legado: %s" % (row,))
            refused = page.evaluate("""async () => {
              const response = await fetch('/api/accounts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ institution: 'Santander', bankCode: '001', accountNumber: '1', kind: 'corrente' }) });
              return response.status;
            }""")
            if refused < 400:
                raise RuntimeError("o servidor aceitou banco e código incoerentes")
            for width, height, suffix in ((1440, 900, "1440"), (768, 900, "768"), (390, 844, "390"), (360, 740, "360")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto("http://127.0.0.1:%s/#contas/nova" % PORT)
                page.wait_for_selector("#acc-institution")
                shot(page, "formulario-%s.png" % suffix)
                if width <= 390:
                    mobile = style_of(page, "h1")
                    if mobile["size"] != "25px":
                        raise RuntimeError("H1 no celular fora da escala em %s: %s" % (width, mobile))
            page.set_viewport_size({"width": 1280, "height": 900})
            for route, name in (("#inicio", "inicio"), ("#lancamentos", "lancamentos"), ("#planejar", "planejar"), ("#perfil", "perfil")):
                page.goto("http://127.0.0.1:%s/%s" % (PORT, route))
                page.wait_for_selector("h1")
                found = style_of(page, "h1")
                notes.append({name: found})
                if found["size"] != "28px":
                    raise RuntimeError("H1 de %s fora da escala: %s" % (name, found))
                shot(page, "titulo-%s-1280.png" % name)
            zoom_dir = Path(tempfile.mkdtemp(prefix="isa-zoom-r2-"))
            (zoom_dir / "Default").mkdir()
            level = math.log(2) / math.log(1.2)
            (zoom_dir / "Default" / "Preferences").write_text(json.dumps({"partition": {"default_zoom_level": {"x": level}}}), encoding="utf-8")
            context = playwright.chromium.launch_persistent_context(str(zoom_dir), headless=True, viewport={"width": 1280, "height": 900})
            zoomed = context.new_page()
            zoomed.goto("http://127.0.0.1:%s/#entrar" % PORT)
            zoomed.click("#enter-paulo")
            zoomed.wait_for_selector("#desk-contas")
            zoomed.goto("http://127.0.0.1:%s/#contas/nova" % PORT)
            zoomed.wait_for_selector("#acc-institution")
            zoom = zoomed.evaluate("() => ({ inner: window.innerWidth, dpr: window.devicePixelRatio, scroll: document.documentElement.scrollWidth })")
            notes.append({"zoom": zoom})
            zoomed.screenshot(path=str(SHOTS / "formulario-zoom-200.png"))
            if zoom["dpr"] < 1.8 or zoom["inner"] > 700:
                notes.append({"zoomLimit": "O Chromium headless desta sessão manteve a densidade em 1 e a largura em 1280. O reflow foi conferido nas larguras 768, 390 e 360, sem escala de CSS."})
            context.close()
            browser.close()
        (SHOTS / "medidas.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
        print("prova ok")
    finally:
        proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
