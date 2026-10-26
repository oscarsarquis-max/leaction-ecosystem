"""Prova visual do Início integrado. Base sintética, sem a conta publicada."""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "documents" / "reviews" / "inicio-004ia6"
PORT = 8144


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


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-inicio-"))
    proc = start_server(tmp)
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:%s/#entrar" % PORT)
            page.click("#enter-paulo")
            page.wait_for_selector("text=Seu dinheiro")
            page.wait_for_selector("text=Vamos reunir suas informações")
            if page.locator("h2", has_text="O que já aconteceu").count():
                raise RuntimeError("o histórico separado voltou ao Início")
            if page.locator("text=Informe seu disponível").count():
                raise RuntimeError("o pedido de disponível repetido voltou")
            page.screenshot(path=str(SHOTS / "inicio-vazio-1280.png"), full_page=False)
            for width in (1440, 768, 390, 360):
                page.set_viewport_size({"width": width, "height": 900})
                page.screenshot(path=str(SHOTS / ("inicio-vazio-%s.png" % width)), full_page=False)
            browser.close()
            print("prova ok")
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
