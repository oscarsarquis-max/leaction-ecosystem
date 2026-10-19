"""Prova isolada da jornada de planejamento. Não usa a conta publicada."""
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
SHOTS = ROOT / "documents" / "reviews" / "planejar-004ia2"
PORT = 8134


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
    page.screenshot(path=str(SHOTS / name), full_page=True)


def assert_reachable(page):
    box = page.locator("#q1 button.primary, #q2 button.primary, #q3 button.primary").first
    box.scroll_into_view_if_needed()
    metrics = page.evaluate("""() => {
      const button = document.querySelector('#q1 button.primary, #q2 button.primary, #q3 button.primary');
      const dock = document.querySelector('.dock');
      const b = button.getBoundingClientRect();
      const d = dock.getBoundingClientRect();
      return { overlap: b.bottom > d.top + 1 && b.top < d.bottom, scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth, buttonTop: b.top, dockTop: d.top };
    }""")
    if metrics["scrollWidth"] > metrics["innerWidth"] + 1:
        raise RuntimeError("rolagem horizontal: %s" % metrics)
    if metrics["overlap"]:
        raise RuntimeError("ação coberta pelo menu: %s" % metrics)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-plan-"))
    proc = start_server(tmp)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.wait_for_selector("#enter-paulo")
            page.click("#enter-paulo")
            page.wait_for_selector("a[href='#planejar/disponivel/voltar']")
            page.wait_for_function("() => document.body.innerText.includes('Informe seu disponível')")
            if page.locator("#isa-ai-card").count():
                raise RuntimeError("o cartão da IA está acima dos números")
            page.goto("http://127.0.0.1:%s/#planejar/disponivel" % PORT)
            page.wait_for_selector("#plan-title")
            page.wait_for_function("() => (document.querySelector('#plan-title') || {}).textContent && document.querySelector('#plan-title').textContent.indexOf('dispon') >= 0")
            above = page.evaluate("""() => {
              const title = document.querySelector('#plan-title');
              const card = document.querySelector('#isa-ai-card');
              if (!card) return false;
              return card.getBoundingClientRect().top < title.getBoundingClientRect().top;
            }""")
            if above:
                raise RuntimeError("o cartão da IA está acima do formulário")
            if page.locator("#q1-amount").get_attribute("placeholder") != "Informe o valor":
                raise RuntimeError("placeholder numérico indevido")
            shot(page, "disponivel-390.png")
            assert_reachable(page)
            page.click("#q1 button.primary")
            page.wait_for_selector("#q1-amount-error")
            if "zero" not in page.locator("#q1-amount-error").inner_text():
                raise RuntimeError("erro de campo vazio ausente")
            shot(page, "erro-390.png")
            page.route("**/api/availability", lambda route: route.abort())
            page.fill("#q1-amount", "1.200,50")
            page.locator("#q1 .plan-choice button[data-choice='nao']").click()
            page.click("#q1 button.primary")
            page.wait_for_selector("#save-state.note")
            if "Salvo" in page.locator("#save-state").inner_text():
                raise RuntimeError("falha de rede confirmou gravação")
            if page.locator("#q1-amount").input_value() != "1.200,50":
                raise RuntimeError("falha de rede apagou o valor")
            page.unroute("**/api/availability")
            page.fill("#q1-amount", "0,00")
            page.click("#q1 button.primary")
            page.wait_for_selector("#plan-title")
            page.wait_for_function("() => (document.querySelector('#plan-title') || {}).textContent && document.querySelector('#plan-title').textContent.indexOf('receber') >= 0")
            shot(page, "entrada-390.png")
            page.goto("http://127.0.0.1:%s/#planejar/disponivel" % PORT)
            page.wait_for_function("() => document.querySelector('#q1-amount') && document.querySelector('#q1-amount').value === '0,00'")
            page.fill("#q1-amount", "1.200,50")
            page.click("#q1 button.primary")
            page.wait_for_function("() => (document.querySelector('#plan-title') || {}).textContent && document.querySelector('#plan-title').textContent.indexOf('receber') >= 0")
            page.fill("#q2-label", "Pagamento")
            page.fill("#q2-amount", "800,00")
            page.click("#q2 button.primary")
            page.wait_for_selector("#q3-label")
            page.fill("#q3-label", "Aluguel")
            page.fill("#q3-amount", "500,00")
            page.click("#q3 button.primary")
            page.wait_for_selector("#q3-next")
            assert_reachable(page)
            page.click("#q3-next")
            page.wait_for_function("() => document.body.innerText.includes('Aluguel') && document.body.innerText.includes('1.200,50')")
            page.set_viewport_size({"width": 1280, "height": 800})
            page.wait_for_timeout(300)
            shot(page, "resumo-1280.png")
            count = page.evaluate("""async () => {
              const response = await fetch('/api/home', {headers:{'X-ISA-Lab-Person':'paulo'}});
              const data = await response.json();
              return {inflows: data.inflows.length, commitments: data.commitments.length, amount: data.guide.availability.amountCents};
            }""")
            if count["inflows"] != 1 or count["commitments"] != 1 or count["amount"] != 120050:
                raise RuntimeError("dados isolados inesperados: %s" % count)
            browser.close()
            print("prova da jornada ok")
    finally:
        proc.kill()
        proc.wait(timeout=5)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
