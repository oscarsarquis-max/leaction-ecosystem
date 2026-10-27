"""Prova da casca visual no laboratório. Não usa a conta publicada."""

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
OUT = ROOT / "documents" / "reviews" / "base-visual-006a"
OUT.mkdir(parents=True, exist_ok=True)
REF = Path(r"C:\Projetos\claude\2026-10-15-interface-gestao-financeira\isa\desenho-005\referencia\html")
PORT = 8126
BASE = "http://127.0.0.1:%s/" % PORT
ROUTES = [
    ("entrar", "#entrar"),
    ("inicio", "#inicio"),
    ("lancamentos", "#lancamentos"),
    ("planejar", "#planejar"),
    ("contas", "#contas"),
    ("perfil", "#perfil"),
    ("registrar", "#registrar"),
    ("importar", "#importar"),
    ("conferir", "#conferir"),
    ("pendencias", "#pendencias"),
    ("origem", "#origem"),
]


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(BASE.rstrip("/") + path, data=data, method=method)
    request.add_header("X-ISA-Lab-Person", "marina")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_health(proc):
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE + "api/health", timeout=1).read()
            return
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(proc.stdout.read().decode("utf-8", "replace") if proc.stdout else "laboratorio encerrou")
            time.sleep(0.1)
    raise RuntimeError("laboratorio nao respondeu")


def overflow(page):
    return page.evaluate("""() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
      extra: document.documentElement.scrollWidth - document.documentElement.clientWidth
    })""")


def small_targets(page):
    return page.evaluate("""() => {
      const nodes = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
      const bad = [];
      nodes.forEach((node) => {
        const box = node.getBoundingClientRect();
        if (box.width < 1 || box.height < 1) return;
        if (box.height >= 44 && box.width >= 44) return;
        if (box.height >= 44 && box.width >= 24) return;
        const label = (node.getAttribute('aria-label') || node.textContent || node.id || node.tagName).trim().slice(0, 40);
        bad.push({ label, w: Math.round(box.width), h: Math.round(box.height) });
      });
      return bad.slice(0, 12);
    }""")


def click_ms(page, script):
    return page.evaluate(script)


def compare(left, right):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return {"error": "sem Pillow"}
    a = Image.open(left).convert("RGB")
    b = Image.open(right).convert("RGB")
    width = min(a.width, b.width)
    height = min(a.height, b.height)
    a = a.crop((0, 0, width, height))
    b = b.crop((0, 0, width, height))
    diff = ImageChops.difference(a, b)
    changed = 0
    pixels = diff.load()
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != (0, 0, 0):
                changed += 1
    side = Image.new("RGB", (width * 2 + 8, height), (244, 245, 248))
    side.paste(a, (0, 0))
    side.paste(b, (width + 8, 0))
    name = Path(left).stem + "-lado.png"
    side.save(OUT / name)
    return {"width": width, "height": height, "changed": changed, "ratio": round(changed / max(1, width * height), 4), "side": name}


def shot_pair(app, ref, name):
    app_path = OUT / (name + "-app.png")
    ref_path = OUT / (name + "-ref.png")
    app.screenshot(path=str(app_path))
    ref.screenshot(path=str(ref_path))
    result = compare(app_path, ref_path)
    result["name"] = name
    return result


def main():
    data = tempfile.mkdtemp(prefix="isa-casca-")
    env = os.environ.copy()
    env.update({
        "ISA_ENV": "lab",
        "ISA_DATA": data,
        "ISA_BACKUP_ROOT": os.path.join(data, "backups"),
        "ISA_PORT": str(PORT),
        "ISA_ERASURE_LEDGER": os.path.join(data, "erasure.jsonl"),
    })
    os.makedirs(env["ISA_BACKUP_ROOT"], exist_ok=True)
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "serve.py")], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    report = {"routes": [], "overflow": [], "targets": [], "clicks": [], "load": [], "diff": [], "zoom": "", "importar": ""}
    try:
        wait_health(proc)
        created = call("POST", "/api/entries", {"entry": {
            "merchant": "Mercado Central", "amountMinor": 10000, "direction": "gasto", "status": "pago",
            "statusDate": "2026-10-22", "noteDate": "2026-10-22", "nature": "consumo", "category": "Alimentação",
        }})["entry"]
        batch = call("POST", "/api/work-batches", {"name": "Obra da casa", "criterion": "outro"})["batch"]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            def watch(target):
                rows = []
                target.on("response", lambda response: rows.append({
                    "url": response.url.split("?")[0].replace(BASE, "/"),
                    "cache": response.headers.get("cache-control", ""),
                    "bytes": int(response.headers.get("content-length") or 0),
                }))
                return rows
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            first = watch(page)
            page.goto(BASE, wait_until="networkidle")
            report["load"].append({"pass": "primeira", "requests": len(first), "bytes": sum(item["bytes"] for item in first), "sample": first[:12]})
            second = watch(page)
            page.reload(wait_until="networkidle")
            report["load"].append({"pass": "segunda", "requests": len(second), "bytes": sum(item["bytes"] for item in second), "immutable": sum(1 for item in second if "immutable" in item["cache"]), "nostore": [item["url"] for item in second if "no-store" in item["cache"]]})
            page.click("#enter-marina")
            page.wait_for_selector("#desk-inicio")
            routes = list(ROUTES) + [("detalhe", "#detalhe/" + created["id"]), ("lote", "#lote/" + batch["id"])]
            for name, route in routes:
                page.goto(BASE + route, wait_until="domcontentloaded")
                page.wait_for_timeout(400)
                for width in (1440, 390, 360, 768):
                    page.set_viewport_size({"width": width, "height": 900})
                    page.wait_for_timeout(150)
                    if width in (1440, 390):
                        page.screenshot(path=str(OUT / ("%s-%s.png" % (name, width))), full_page=True)
                    extra = overflow(page)
                    if extra["extra"] > 1:
                        report["overflow"].append({"route": name, "width": width, "extra": extra["extra"]})
                    if width == 390:
                        bad = small_targets(page)
                        if bad:
                            report["targets"].append({"route": name, "items": bad})
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(BASE + "#inicio", wait_until="domcontentloaded")
            page.wait_for_selector(".month-title")
            text = page.locator("#money-home").inner_text()
            report["importar"] = "Importar" in text
            report["clicks"].append(click_ms(page, """() => {
              const node = document.querySelector('.month-title');
              const before = node.textContent;
              const t0 = performance.now();
              document.getElementById('home-next').click();
              return { kind: 'mes', ms: Math.round((performance.now() - t0) * 10) / 10, changed: node.textContent !== before, after: node.textContent };
            }"""))
            page.wait_for_timeout(300)
            report["clicks"].append(click_ms(page, """() => {
              const node = document.getElementById('desk-lista');
              const t0 = performance.now();
              node.click();
              const current = document.getElementById('desk-lista').getAttribute('aria-current');
              return { kind: 'aba', ms: Math.round((performance.now() - t0) * 10) / 10, current: current };
            }"""))
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(BASE + "#inicio", wait_until="domcontentloaded")
            page.wait_for_selector("header.shell")
            ref = browser.new_page(viewport={"width": 1440, "height": 900})
            ref.goto((REF / "Inicio.html").as_uri(), wait_until="domcontentloaded")
            report["diff"].append(shot_pair(page.locator("header.shell"), ref.locator("header.dshell").first, "faixa-1440"))
            report["diff"].append(shot_pair(page.locator("nav.brand-nav"), ref.locator("nav.dshell").first, "nav-1440"))
            report["diff"].append(shot_pair(page.locator(".monthbar"), ref.locator("main > div").first, "mes-1440"))
            report["diff"].append(shot_pair(page.locator(".money-calendar .cal"), ref.locator(".cal").first, "calendario-1440"))
            page.set_viewport_size({"width": 390, "height": 844})
            refm = browser.new_page(viewport={"width": 390, "height": 844})
            refm.goto((REF / "MInicio.html").as_uri(), wait_until="domcontentloaded")
            report["diff"].append(shot_pair(page.locator(".brand-bar"), refm.locator("header").first, "faixa-390"))
            report["diff"].append(shot_pair(page.locator(".dock"), refm.locator("nav").first, "barra-390"))
            try:
                client = page.context.new_cdp_session(page)
                client.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
                page.wait_for_timeout(200)
                zoomed = overflow(page)
                report["zoom"] = "cdp-2 " + json.dumps(zoomed)
            except Exception as exc:
                page.evaluate("() => { document.body.style.zoom = '2'; }")
                page.wait_for_timeout(200)
                report["zoom"] = "css-zoom-2 " + json.dumps(overflow(page)) + " " + type(exc).__name__
            browser.close()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
