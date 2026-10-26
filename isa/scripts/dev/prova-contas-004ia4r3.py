"""Prova visual do catálogo STR, do cadastro e da hierarquia. Base sintética."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "documents" / "reviews" / "contas-004ia4r3"
PORT = 8143


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


def headings(page):
    return page.evaluate(
        """() => {
          const read = (selector) => {
            const node = document.querySelector(selector);
            if (!node) return null;
            const style = getComputedStyle(node);
            return { tag: node.tagName, size: style.fontSize, weight: style.fontWeight, text: node.textContent.trim().slice(0, 90) };
          };
          return {
            h1: read("h1"),
            h2: read("h2"),
            h3: read("h3"),
            scroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
            width: document.documentElement.clientWidth,
          };
        }"""
    )


def enter(page):
    page.goto("http://127.0.0.1:%s/#entrar" % PORT)
    page.click("#enter-paulo")
    page.wait_for_selector("text=Seu dinheiro")


def visit(page, target, name, notes):
    page.evaluate("(hash) => { location.hash = hash; }", target)
    page.wait_for_timeout(400)
    item = headings(page)
    item["route"] = target
    notes.append(item)
    shot(page, name)
    if not item["h1"]:
        raise RuntimeError("sem H1 em " + target)
    return item


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-contas-r3-"))
    proc = start_server(tmp)
    notes = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            enter(page)
            routes = [
                ("#inicio", "titulo-inicio-1280.png"),
                ("#lancamentos", "titulo-lancamentos-1280.png"),
                ("#lotes", "titulo-lotes-1280.png"),
                ("#registrar", "titulo-registrar-1280.png"),
                ("#conferir", "titulo-conferir-1280.png"),
                ("#importar", "titulo-importar-1280.png"),
                ("#planejar", "titulo-planejar-1280.png"),
                ("#perfil", "titulo-perfil-1280.png"),
                ("#contas", "lista-vazia-1280.png"),
            ]
            for target, name in routes:
                visit(page, target, name, notes)
            page.click("text=Adicionar conta")
            page.wait_for_selector("#acc-institution")
            page.fill("#acc-institution", "xyzbancoinexistente")
            page.wait_for_selector("text=Não encontramos esta instituição na lista")
            page.click("#ask-catalog")
            page.wait_for_selector("text=Busca registrada")
            shot(page, "catalogo-ausente-1280.png")
            page.fill("#acc-institution", "077")
            page.wait_for_selector("#bank-listbox [role=option]")
            first = page.locator("#bank-listbox [role=option]").first.inner_text()
            if not first.startswith("077 —"):
                raise RuntimeError("código 077 não veio primeiro: " + first)
            page.locator("#bank-listbox [role=option]").first.click()
            page.fill("#acc-number", "0012345-6")
            page.select_option("#acc-kind", "corrente")
            page.fill("#acc-agency", "0123-4")
            page.fill("#acc-agency-name", "Agência Centro")
            page.fill("#contact-name-0", "Ana")
            page.click("#add-contact")
            shot(page, "formulario-preenchido-1280.png")
            page.click("#account-save")
            page.wait_for_selector("#add-account")
            shot(page, "lista-preenchida-1280.png")
            page.click("text=Abrir conta")
            page.wait_for_selector("text=Dados e contatos")
            shot(page, "conta-dados-1280.png")
            page.click("text=Editar dados")
            page.wait_for_selector("#acc-agency-name")
            if page.locator("#acc-agency-name").input_value() != "Agência Centro":
                raise RuntimeError("nome da agência não voltou na edição")
            page.reload()
            page.wait_for_selector("#acc-agency-name")
            if page.locator("#acc-agency-name").input_value() != "Agência Centro":
                raise RuntimeError("nome da agência não voltou depois de recarregar")
            shot(page, "editar-1280.png")
            for width in (1440, 768, 390, 360):
                page.set_viewport_size({"width": width, "height": 900})
                page.fill("#acc-institution", "Banco do Brasil")
                page.wait_for_selector("#bank-listbox [role=option]")
                shot(page, "formulario-dropdown-%s.png" % width)
                item = headings(page)
                item["route"] = "formulario-" + str(width)
                notes.append(item)
                if not item["scroll"]:
                    raise RuntimeError("rolagem horizontal em " + str(width))
            page.set_viewport_size({"width": 390, "height": 800})
            for target, name in (("#inicio", "titulo-inicio-390.png"), ("#lancamentos", "titulo-lancamentos-390.png"), ("#planejar", "titulo-planejar-390.png"), ("#perfil", "titulo-perfil-390.png"), ("#importar", "titulo-importar-390.png")):
                visit(page, target, name, notes)
            browser.close()
            zoom = {"applied": False, "reason": ""}
            try:
                headed = playwright.chromium.launch(channel="chrome", headless=False, args=["--window-size=1280,900"])
                zoom_page = headed.new_page()
                zoom_page.goto("http://127.0.0.1:%s/#entrar" % PORT)
                before = zoom_page.evaluate("() => ({ inner: window.innerWidth, dpr: window.devicePixelRatio, scale: window.visualViewport ? window.visualViewport.scale : null })")
                zoom_page.keyboard.press("Control+Equal")
                zoom_page.keyboard.press("Control+Equal")
                zoom_page.keyboard.press("Control+Equal")
                zoom_page.keyboard.press("Control+Equal")
                zoom_page.wait_for_timeout(500)
                after = zoom_page.evaluate("() => ({ inner: window.innerWidth, dpr: window.devicePixelRatio, scale: window.visualViewport ? window.visualViewport.scale : null })")
                zoom = {"applied": after != before, "before": before, "after": after, "browser": "chrome", "window": "1280x900", "keys": "Control+Equal x4"}
                if not zoom["applied"]:
                    zoom["reason"] = "O Chrome com janela não alterou innerWidth, devicePixelRatio nem visualViewport.scale depois de Control+Equal. Zoom de página de 200% não ficou comprovado."
                headed.close()
            except Exception as exc:
                zoom = {"applied": False, "reason": "Não foi possível abrir o Chrome com janela: " + type(exc).__name__ + " " + str(exc)}
            notes.append({"zoom": zoom})
            (SHOTS / "medidas.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
            if any(item.get("h1") and item["h1"]["size"] not in ("28px", "25px") for item in notes if item.get("h1")):
                raise RuntimeError("H1 fora de 28px ou 25px")
            print("prova ok")
            print(json.dumps(zoom, ensure_ascii=False))
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
