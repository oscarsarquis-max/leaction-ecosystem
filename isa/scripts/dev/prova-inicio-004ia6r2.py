"""Prova da referência 004IA6R2. Pessoa sintética, sem a conta publicada."""
import os
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

SHOTS = ROOT / "documents" / "reviews" / "inicio-004ia6r2"
PORT = 8147
REF = Path(r"C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\ISA_INICIO_REFERENCIA_004IA6R2.html")


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
        ("mov-prova", owner, None, 180000, "saida", "consumo", "2026-09-10", "Moradia", "manual", store.now()),
    )
    conn.close()


def assert_no_import(page):
    if page.locator("text=Importar").count():
        raise RuntimeError("o Início ainda oferece importação")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-r2-"))
    seed(tmp)
    proc = start_server(tmp)
    SHOTS.mkdir(parents=True, exist_ok=True)
    nav = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            if REF.is_file():
                page.goto(REF.as_uri())
                page.wait_for_selector("text=Seu dinheiro")
                page.screenshot(path=str(SHOTS / "referencia-1440.png"), full_page=False)
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-paulo")
            page.wait_for_selector("text=Seu mês completo")
            page.wait_for_selector("text=Agenda do mês")
            page.wait_for_selector("text=Ajuda da ISA")
            assert_no_import(page)
            if page.locator("text=Sua visão financeira começa pelas contas").count():
                raise RuntimeError("mês com histórico foi tratado como primeiro acesso")
            page.screenshot(path=str(SHOTS / "inicio-preenchido-1440.png"), full_page=False)
            for width in (1280, 768, 390, 360):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_selector("text=Seu dinheiro")
                assert_no_import(page)
                page.screenshot(path=str(SHOTS / ("inicio-preenchido-%s.png" % width)), full_page=False)
            page.set_viewport_size({"width": 1280, "height": 900})
            page.click("#home-next")
            page.wait_for_selector("text=Nenhum lançamento neste mês")
            if page.locator("text=Sua visão financeira começa pelas contas").count():
                raise RuntimeError("mês futuro vazio apagou a pessoa")
            page.screenshot(path=str(SHOTS / "mes-vazio-com-historico.png"), full_page=False)
            page.click("#home-current")
            page.wait_for_selector("text=Seu mês completo")
            for _ in range(20):
                mark = time.perf_counter()
                page.click("#desk-lista")
                page.wait_for_selector("text=Lançamentos")
                nav.append((time.perf_counter() - mark) * 1000)
                mark = time.perf_counter()
                page.click("#desk-inicio")
                page.wait_for_selector("text=Seu mês completo")
                nav.append((time.perf_counter() - mark) * 1000)
            page.click("#desk-contas")
            page.wait_for_selector("text=Suas contas")
            page.click("#brand-leave")
            page.click("#enter-marina")
            page.wait_for_selector("text=Sua visão financeira começa pelas contas")
            assert_no_import(page)
            page.screenshot(path=str(SHOTS / "primeiro-acesso.png"), full_page=False)
            page.keyboard.press("Control+Equal")
            scale = page.evaluate("() => ({scale: window.visualViewport && window.visualViewport.scale, h1: getComputedStyle(document.querySelector('h1')).fontSize})")
            ordered = sorted(nav)
            p50 = ordered[len(ordered) // 2]
            p95 = ordered[max(0, int(round(0.95 * (len(ordered) - 1))))]
            (SHOTS / "tempos.txt").write_text(
                "amostras=%s\np50_ms=%.0f\np95_ms=%.0f\nmax_ms=%.0f\nzoom=%s\ncondicao=laboratorio local, SQLite, pessoa sintetica, 20 idas e voltas Inicio/Lancamentos\n" % (len(nav), p50, p95, ordered[-1], scale),
                encoding="utf-8",
            )
            browser.close()
            print("prova ok", round(p50), round(p95), scale)
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
