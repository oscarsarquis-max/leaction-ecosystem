"""Prova isolada do Início. Não usa a conta publicada."""
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
SHOTS = ROOT / "documents" / "reviews" / "inicio-004ia3"
PORT = 8135


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


def shot(page, name, full=True):
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=full)


def seed(page, person, body):
    result = page.evaluate("""async ({person, body}) => {
      const headers = {'Content-Type':'application/json','X-ISA-Lab-Person': person};
      const send = (method, path, payload) => fetch(path, {method, headers, body: payload ? JSON.stringify(payload) : undefined}).then(r => r.json());
      if (body.availability) await send('PUT', '/api/availability', body.availability);
      for (const item of body.inflows || []) await send('POST', '/api/inflows', item);
      for (const item of body.commitments || []) await send('POST', '/api/commitments', item);
      const home = await send('GET', '/api/home');
      const jobs = await send('GET', '/api/home');
      return {situation: home.overview.situation.kind, payables: home.overview.payables.cents, jobs: jobs.overview.reading || null, insights: (home.overview.insights || []).map(item => item.title + ' ' + (item.estimate && item.estimate.extraCents != null ? item.estimate.extraCents : ''))};
    }""", {"person": person, "body": body})
    return result


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-inicio-"))
    proc = start_server(tmp)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.wait_for_selector("#enter-paulo")
            before = page.evaluate("() => ({nav: !!document.querySelector('.brand-nav'), dock: !!document.querySelector('.dock')})")
            if before["nav"] or before["dock"]:
                raise RuntimeError("menu interno antes do login: %s" % before)
            page.click("#enter-paulo")
            page.wait_for_selector("a[href='#planejar/disponivel/voltar']")
            page.wait_for_function("() => document.body.innerText.includes('Disponível') && document.body.innerText.includes('Ainda não informado') && document.body.innerText.includes('Informar valor')")
            if "R$ 0,00" in page.locator("#money-home").inner_text():
                raise RuntimeError("conta nova mostrou zero")
            bar = page.evaluate("""() => {
              const bar = document.querySelector('.brand-bar');
              const img = document.querySelector('.brand-mark img');
              const style = getComputedStyle(bar);
              const image = getComputedStyle(img);
              return {background: style.backgroundColor, radius: image.borderRadius, dock: getComputedStyle(document.querySelector('.dock')).display, desk: getComputedStyle(document.querySelector('.brand-nav')).display};
            }""")
            if bar["background"] != "rgb(24, 0, 173)":
                raise RuntimeError("barra fora da cor da marca: %s" % bar)
            if bar["radius"] not in ("0px", "0"):
                raise RuntimeError("logo com recorte: %s" % bar)
            if bar["desk"] != "none" or bar["dock"] == "none":
                raise RuntimeError("navegação mobile inesperada: %s" % bar)
            shot(page, "incompleto-390.png", full=False)
            page.set_viewport_size({"width": 1280, "height": 800})
            page.wait_for_timeout(200)
            desk = page.evaluate("""() => ({desk: getComputedStyle(document.querySelector('.brand-nav')).display, dock: getComputedStyle(document.querySelector('.dock')).display})""")
            if desk["desk"] == "none" or desk["dock"] != "none":
                raise RuntimeError("navegação desktop inesperada: %s" % desk)
            shot(page, "incompleto-1280.png")
            page.set_viewport_size({"width": 640, "height": 800})
            stacked = page.evaluate("""() => getComputedStyle(document.querySelector('.money-layout')).gridTemplateColumns""")
            if stacked and " " in stacked and "none" not in stacked:
                raise RuntimeError("zoom de layout não reorganizou: %s" % stacked)
            wide = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")
            if wide:
                raise RuntimeError("conteúdo mais largo que a janela no viewport de 200%")
            page.set_viewport_size({"width": 390, "height": 844})
            page.click("a[href='#planejar/disponivel/voltar']")
            page.wait_for_function("() => (document.querySelector('#plan-title') || {}).textContent && document.querySelector('#plan-title').textContent.indexOf('dispon') >= 0")
            page.fill("#q1-amount", "1.500,00")
            page.fill("#q1-date", "2026-10-16")
            page.locator("#q1 .plan-choice button[data-choice='sim']").click()
            page.fill("#q1-floor", "200,00")
            page.click("#q1 button.primary")
            page.wait_for_function("() => document.body.innerText.includes('1.500,00') && document.body.innerText.includes('Disponível')")
            shot(page, "parcial-390.png", full=False)
            covered = seed(page, "marina", {
                "availability": {"amountCents": 250000, "asOf": "2026-10-16", "protectedCents": 0, "source": "declarada"},
                "inflows": [{"label": "Pagamento", "amountCents": 180000, "dueOn": "2026-11-05", "state": "confirmada"}],
                "commitments": [{"label": "Aluguel", "totalCents": 90000, "dueOn": "2026-10-20"}],
            })
            if covered["situation"] != "covers":
                raise RuntimeError("cobertura inesperada: %s" % covered)
            short = seed(page, "paulo", {
                "inflows": [{"label": "Pagamento", "amountCents": 200000, "dueOn": "2026-11-05", "state": "confirmada"}],
                "commitments": [
                    {"label": "Condomínio", "totalCents": 100000, "dueOn": "2026-10-01", "conditions": {"kind": "fatura", "principalCents": 100000, "fineCents": 2000, "interest": {"regime": "simples", "period": "month", "rateBps": 100}}},
                    {"label": "Internet", "totalCents": 9000, "dueOn": "2026-10-10"},
                    {"label": "Escola", "totalCents": 180000, "dueOn": "2026-10-18"},
                ],
            })
            if short["situation"] != "shortfall":
                raise RuntimeError("falta inesperada: %s" % short)
            if short["jobs"] is not None:
                raise RuntimeError("abrir os dados gravou leitura de IA")
            page.reload()
            page.wait_for_function("() => document.body.innerText.includes('Faltam') && document.body.innerText.includes('encargos estimados serão')")
            if "R$ 30,00" not in page.locator("#money-home").inner_text() and "R$ 30,00" not in page.locator("#money-home").inner_text():
                raise RuntimeError("encargo sem valor absoluto: %s" % page.locator(".insight").first.inner_text())
            page.locator(".cal-day").nth(17).click()
            page.wait_for_selector("#day-list li, #day-list p")
            page.locator(".cal-day").first.focus()
            if page.evaluate("() => document.activeElement.className.indexOf('cal-day') < 0"):
                raise RuntimeError("dia sem foco")
            with page.expect_response(lambda response: response.url.endswith("/api/home") and response.request.method == "GET"):
                page.locator("[data-dismiss]").first.click()
            page.locator(".money-situation .primary").scroll_into_view_if_needed()
            covered_action = page.evaluate("""() => {
              const button = document.querySelector('.money-situation .primary');
              const dock = document.querySelector('.dock');
              const b = button.getBoundingClientRect();
              const d = dock.getBoundingClientRect();
              return b.bottom > d.top + 1 && b.top < d.bottom;
            }""")
            if covered_action:
                raise RuntimeError("ação principal coberta pelo menu")
            page.evaluate("() => window.scrollTo(0, 0)")
            shot(page, "falta-390.png", full=False)
            page.set_viewport_size({"width": 1280, "height": 800})
            page.wait_for_timeout(200)
            shot(page, "falta-1280.png")
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-marina")
            page.wait_for_function("() => document.body.innerText.includes('cabem até') && !document.body.innerText.includes('Condomínio')")
            shot(page, "suficiente-1280.png")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(200)
            shot(page, "suficiente-390.png", full=False)
            page.set_viewport_size({"width": 360, "height": 740})
            page.wait_for_timeout(200)
            narrow = page.evaluate("""() => {
              const bar = document.querySelector('.brand-bar');
              const img = document.querySelector('.brand-mark img');
              const box = img.getBoundingClientRect();
              return {scroll: document.documentElement.scrollWidth > window.innerWidth + 1, bar: bar.scrollWidth > bar.clientWidth + 1, width: box.width, height: box.height, letters: getComputedStyle(document.querySelector('.cal-key') || document.body).letterSpacing};
            }""")
            if narrow["scroll"] or narrow["bar"]:
                raise RuntimeError("marca ou menu estouram em 360: %s" % narrow)
            shot(page, "marca-360.png", full=False)
            browser.close()
            print("prova do início ok")
    finally:
        proc.kill()
        proc.wait(timeout=5)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
