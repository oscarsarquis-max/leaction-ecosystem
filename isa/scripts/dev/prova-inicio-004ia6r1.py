"""Prova do Início depois da regressão. Pessoa sintética de laboratório, sem a conta publicada."""
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))
import store

SHOTS = ROOT / "documents" / "reviews" / "inicio-004ia6r1"
PORT = 8146


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


def seed(data):
    os.environ["ISA_ENV"] = "lab"
    conn = store.connect(str(data / "isa.sqlite"))
    owner = "pessoa-paulo"
    bb = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
    poup = store.save_account(conn, owner, {"name": "Poupança", "currency": "BRL", "kind": "poupanca", "institution": "CAIXA ECONOMICA FEDERAL"})
    store.save_availability(conn, owner, {"accountId": bb["id"], "amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 0, "source": "declarada"})
    store.save_availability(conn, owner, {"accountId": poup["id"], "amountCents": 20000, "asOf": "2026-10-16", "protectedCents": 20000, "source": "declarada"})
    store.add_commitment(conn, owner, {"label": "Conta do dia 20", "totalCents": 45000, "dueOn": "2026-10-20", "accountId": bb["id"]})
    store.add_inflow(conn, owner, {"label": "Recebimento", "amountCents": 150000, "dueOn": "2026-10-30", "state": "confirmada", "accountId": bb["id"]})
    conn.execute(
        "INSERT INTO movement (id, owner_id, occurrence_id, amount_cents, direction, nature, booked_on, label, source, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("mov-prova", owner, None, 180000, "saida", "consumo", "2026-10-10", "Moradia", "manual", store.now()),
    )
    conn.close()


def useful(page):
    page.wait_for_selector("text=Situação do dinheiro")
    page.wait_for_selector("text=Seu mês completo")
    page.wait_for_selector("text=Agenda do mês")
    page.wait_for_selector("text=Ajuda da ISA")
    page.wait_for_selector("text=O dinheiro chega?")
    page.wait_for_selector("text=Evolução")
    if page.locator("text=Nenhum valor foi gravado").count():
        raise RuntimeError("a mensagem da regressão voltou")
    if page.locator("text=Não foi possível carregar suas informações").count():
        raise RuntimeError("a consulta falhou na montagem")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-inicio-r1-"))
    seed(tmp)
    proc = start_server(tmp)
    SHOTS.mkdir(parents=True, exist_ok=True)
    samples = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            started = time.perf_counter()
            page.click("#enter-paulo")
            useful(page)
            samples.append((time.perf_counter() - started) * 1000)
            if page.locator(".home-actions").count():
                raise RuntimeError("importar voltou ao cabeçalho do Início")
            page.screenshot(path=str(SHOTS / "inicio-preenchido-1440.png"), full_page=False)
            for width in (1280, 768, 390, 360):
                page.set_viewport_size({"width": width, "height": 900})
                useful(page)
                page.screenshot(path=str(SHOTS / ("inicio-preenchido-%s.png" % width)), full_page=False)
            page.set_viewport_size({"width": 1280, "height": 900})
            page.click("#home-next")
            page.wait_for_selector("text=novembro de 2026")
            urls = []

            def track(route):
                urls.append(route.request.url)
                if len(urls) == 1:
                    route.abort()
                else:
                    route.continue_()

            page.route("**/api/home**", track)
            page.click("#home-prev")
            page.wait_for_selector("text=Não conseguimos atualizar suas informações agora")
            page.click("#money-retry")
            page.wait_for_selector("text=Situação do dinheiro")
            if any("PointerEvent" in item or "object" in item for item in urls):
                raise RuntimeError("a repetição enviou o evento: %s" % urls)
            if not any("month=2026-10" in item for item in urls):
                raise RuntimeError("a repetição não manteve outubro: %s" % urls)
            page.unroute("**/api/home**")
            page.click("#desk-lista")
            page.wait_for_selector("text=Lançamentos")
            page.click("#desk-inicio")
            useful(page)
            page.click("#brand-leave")
            page.click("#enter-marina")
            page.wait_for_selector("text=Vamos reunir suas informações")
            if page.locator("text=R$ 1.200,00").count() or page.locator("text=R$ 1.200,00").count():
                raise RuntimeError("o saldo da outra pessoa apareceu")
            page.click("#brand-leave")
            page.click("#enter-paulo")
            useful(page)
            delayed = {"hit": False}

            def slow_ai(route):
                delayed["hit"] = True
                time.sleep(1.2)
                route.continue_()

            page.route("**/api/insights/today", slow_ai)
            for _ in range(6):
                mark = time.perf_counter()
                page.reload()
                useful(page)
                samples.append((time.perf_counter() - mark) * 1000)
            page.keyboard.press("Control+Equal")
            page.keyboard.press("Control+Equal")
            scale = page.evaluate("() => (window.visualViewport && window.visualViewport.scale) || 1")
            (SHOTS / "zoom.txt").write_text("visualViewport.scale=%s\n" % scale, encoding="utf-8")
            ordered = sorted(samples)
            p50 = ordered[len(ordered) // 2]
            p95 = ordered[max(0, int(round(0.95 * (len(ordered) - 1))))]
            (SHOTS / "tempos.txt").write_text(
                "amostras_ms=%s\np50_ms=%.0f\np95_ms=%.0f\nia_atrasada=%s\ncondicao=laboratorio local, pessoa sintetica, IA com espera de 1,2s na rota\n" % (["%.0f" % item for item in samples], p50, p95, delayed["hit"]),
                encoding="utf-8",
            )
            browser.close()
            print("prova ok", "p50", round(p50), "p95", round(p95), "zoom", scale)
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
