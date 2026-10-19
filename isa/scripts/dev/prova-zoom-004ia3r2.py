"""Zoom real de 200% no Chromium. Não usa viewport reduzido nem zoom de CSS."""
import json
import math
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
SHOTS = ROOT / "documents" / "reviews" / "acabamento-004ia3r2"
PORT = 8136


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


def metrics(page):
    return page.evaluate("""() => {
      const dock = document.querySelector('.dock');
      const cards = document.querySelector('.money-cards');
      const style = cards ? getComputedStyle(cards) : null;
      return {
        inner: window.innerWidth,
        outer: window.outerWidth,
        dpr: window.devicePixelRatio,
        scale: window.visualViewport ? window.visualViewport.scale : null,
        scroll: document.documentElement.scrollWidth,
        dock: dock ? getComputedStyle(dock).display : null,
        columns: style ? style.gridTemplateColumns : null
      };
    }""")


def open_home(playwright, profile, zoom):
    args = ["--window-size=1280,1400", "--window-position=0,0", "--force-device-scale-factor=1"]
    context = playwright.chromium.launch_persistent_context(str(profile), headless=False, viewport=None, args=args)
    page = context.pages[0]
    page.goto("http://127.0.0.1:%s/#entrar" % PORT)
    page.wait_for_selector("#enter-paulo")
    page.click("#enter-paulo")
    page.wait_for_function("() => document.body.innerText.includes('Ainda não informado')")
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    reading = metrics(page)
    page.screenshot(path=str(SHOTS / ("zoom-200.png" if zoom else "zoom-100.png")))
    context.close()
    return reading


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isa-zoom-"))
    level = math.log(2) / math.log(1.2)
    proc = start_server(tmp)
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            plain = Path(tempfile.mkdtemp(prefix="isa-zoom-plain-"))
            (plain / "Default").mkdir()
            before = open_home(playwright, plain, False)
            zoomed = Path(tempfile.mkdtemp(prefix="isa-zoom-hi-"))
            (zoomed / "Default").mkdir()
            (zoomed / "Default" / "Preferences").write_text(
                json.dumps({"partition": {"default_zoom_level": {"x": level}}}),
                encoding="utf-8",
            )
            after = open_home(playwright, zoomed, True)
        print("100", before)
        print("200", after)
        if after["inner"] > before["inner"] * 0.6:
            raise RuntimeError("o zoom de 200%% não reduziu a largura útil: %s -> %s" % (before["inner"], after["inner"]))
        if after["dpr"] < 1.8:
            raise RuntimeError("a densidade não acompanhou o zoom do navegador: %s" % after)
        if after["dock"] == "none":
            raise RuntimeError("o zoom não refluuiu para a navegação compacta")
        if after["scroll"] > after["inner"] + 2:
            raise RuntimeError("rolagem horizontal no zoom: %s" % after)
        print("zoom real ok")
    finally:
        proc.kill()
        proc.wait(timeout=5)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
