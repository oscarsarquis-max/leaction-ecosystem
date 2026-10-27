"""Prova da correção da casca no laboratório. Não usa a conta publicada."""

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
OUT = ROOT / "documents" / "reviews" / "correcao-casca-006a-r1"
OUT.mkdir(parents=True, exist_ok=True)
REF = Path(r"C:\Projetos\claude\2026-10-15-interface-gestao-financeira\isa\desenho-005\referencia\html")
PORT = 8127
BASE = "http://127.0.0.1:%s/" % PORT
ROUTES = [
    ("inicio", "#inicio"),
    ("lancamentos", "#lancamentos"),
    ("planejar", "#planejar"),
    ("contas", "#contas"),
    ("perfil", "#perfil"),
    ("registrar", "#registrar"),
    ("importar", "#importar"),
    ("conferir", "#conferir"),
    ("pendencias", "#pendencias"),
]


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


def registrar(page):
    return page.evaluate("""() => {
      const hits = [];
      document.querySelectorAll('a, button').forEach((node) => {
        const text = (node.textContent || '').replace(/\\s+/g, ' ').trim();
        const label = node.getAttribute('aria-label') || '';
        const marked = node.id === 'desk-registrar' || node.id === 'nav-registrar' || text === '+ Registrar' || label === 'Registrar';
        if (!marked) return;
        const style = getComputedStyle(node);
        const box = node.getBoundingClientRect();
        if (style.display === 'none' || style.visibility === 'hidden' || box.width < 1 || box.height < 1) return;
        hits.push(node.id || text);
      });
      return hits;
    }""")


def hoje(page):
    return page.evaluate("""() => {
      const lines = (document.body.innerText.match(/Hoje,[^\\n]+/g) || []);
      const days = [...document.querySelectorAll('.is-today')].map((node) => (node.textContent || '').trim().slice(0, 2));
      return { lines: lines, days: days, reference: window.isaReferenceDate || '' };
    }""")


def boxes(page, script):
    return page.evaluate(script)


def paint(image, regions, color):
    pixels = image.load()
    width, height = image.size
    for region in regions:
        x0 = max(0, int(region["x"]))
        y0 = max(0, int(region["y"]))
        x1 = min(width, int(region["x"] + region["w"]))
        y1 = min(height, int(region["y"] + region["h"]))
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[x, y] = color


def compare(left, right, masks_left, masks_right, name):
    from PIL import Image, ImageChops
    app = Image.open(left).convert("RGB")
    ref = Image.open(right).convert("RGB")
    width = min(app.width, ref.width)
    height = min(app.height, ref.height)
    app = app.crop((0, 0, width, height))
    ref = ref.crop((0, 0, width, height))
    paint(app, masks_left, app.getpixel((2, 2)))
    paint(ref, masks_right, ref.getpixel((2, 2)))
    diff = ImageChops.difference(app, ref)
    changed = 0
    heat = Image.new("RGB", (width, height), (255, 255, 255))
    source = diff.load()
    hot = heat.load()
    for y in range(height):
        for x in range(width):
            if source[x, y] != (0, 0, 0):
                changed += 1
                hot[x, y] = (220, 38, 38)
    side = Image.new("RGB", (width * 2 + 8, height), (244, 245, 248))
    side.paste(app, (0, 0))
    side.paste(ref, (width + 8, 0))
    side.save(OUT / (name + "-lado.png"))
    heat.save(OUT / (name + "-diff.png"))
    return {
        "name": name,
        "width": width,
        "height": height,
        "changed": changed,
        "ratio": round(changed / max(1, width * height), 4),
    }


def shot(page, clip, path):
    page.screenshot(path=str(path), clip=clip)


def main():
    data = tempfile.mkdtemp(prefix="isa-casca-r1-")
    env = os.environ.copy()
    env.pop("ISA_REFERENCE_DATE", None)
    env.update({
        "ISA_ENV": "lab",
        "ISA_DATA": data,
        "ISA_BACKUP_ROOT": os.path.join(data, "backups"),
        "ISA_PORT": str(PORT),
        "ISA_ERASURE_LEDGER": os.path.join(data, "erasure.jsonl"),
    })
    os.makedirs(env["ISA_BACKUP_ROOT"], exist_ok=True)
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "serve.py")], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    report = {"registrar": [], "hoje": [], "overflow": [], "diff": [], "marca": {}}
    try:
        wait_health(proc)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            page.goto(BASE, wait_until="networkidle")
            page.click("#enter-marina")
            page.wait_for_selector("#desk-inicio")
            page.goto(BASE + "#inicio", wait_until="networkidle")
            page.wait_for_selector(".brand-mark img")
            page.wait_for_timeout(400)
            report["marca"]["desktop"] = page.evaluate("""() => {
              const box = document.querySelector('.brand-mark img').getBoundingClientRect();
              return { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) };
            }""")
            for name, route in ROUTES:
                page.goto(BASE + route, wait_until="domcontentloaded")
                page.wait_for_timeout(250)
                for width in (1440, 390, 360, 768):
                    page.set_viewport_size({"width": width, "height": 900})
                    page.wait_for_timeout(80)
                    extra = overflow(page)
                    if extra["extra"] > 1:
                        report["overflow"].append({"route": name, "width": width, "extra": extra["extra"]})
                    if width in (1440, 390):
                        report["registrar"].append({"route": name, "width": width, "visible": registrar(page)})
                        if name in ("inicio", "lancamentos", "planejar"):
                            page.screenshot(path=str(OUT / ("%s-%s.png" % (name, width))), full_page=False)
                if name == "inicio":
                    page.set_viewport_size({"width": 1440, "height": 900})
                    page.wait_for_timeout(200)
                    report["hoje"].append({"width": 1440, **hoje(page)})
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(200)
                    report["hoje"].append({"width": 390, **hoje(page)})
                    report["marca"]["mobile"] = page.evaluate("""() => {
                      const box = document.querySelector('.brand-mark img').getBoundingClientRect();
                      const bar = document.querySelector('.brand-bar').getBoundingClientRect();
                      return { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height), barH: Math.round(bar.height) };
                    }""")

            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(BASE + "#inicio", wait_until="domcontentloaded")
            page.wait_for_selector("header.shell")
            page.wait_for_timeout(200)
            ref = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            ref.goto((REF / "Inicio.html").as_uri(), wait_until="domcontentloaded")
            ref.wait_for_timeout(200)
            report["marca"]["referencia"] = ref.evaluate("""() => {
              const block = document.querySelector('header.dshell div div');
              const box = block.getBoundingClientRect();
              return { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) };
            }""")

            def clip_of(target, selector):
                return target.evaluate("""(selector) => {
                  const node = document.querySelector(selector);
                  const box = node.getBoundingClientRect();
                  return { x: box.x, y: box.y, width: box.width, height: box.height };
                }""", selector)

            def mask_of(target, selector, kind):
                return target.evaluate("""([selector, kind]) => {
                  const root = document.querySelector(selector).getBoundingClientRect();
                  const regions = [];
                  const add = (node, inset) => {
                    if (!node) return;
                    const box = node.getBoundingClientRect();
                    regions.push({ x: box.x - root.x + inset, y: box.y - root.y + inset, w: box.width - inset * 2, h: box.height - inset * 2 });
                  };
                  if (kind === 'desk') {
                    add(document.querySelector('#brand-person') || [...document.querySelectorAll('header.dshell span')].find((node) => (node.textContent || '').includes('Marina')), 0);
                    add(document.querySelector(selector + ' select'), 3);
                  }
                  if (kind === 'mobile') add(document.querySelector('select'), 3);
                  return regions;
                }""", [selector, kind])

            app_bar = clip_of(page, ".brand-bar")
            ref_bar = clip_of(ref, "header.dshell")
            shot(page, app_bar, OUT / "faixa-1440-app.png")
            shot(ref, ref_bar, OUT / "faixa-1440-ref.png")
            report["diff"].append(compare(
                OUT / "faixa-1440-app.png", OUT / "faixa-1440-ref.png",
                mask_of(page, ".brand-bar", "desk"), mask_of(ref, "header.dshell", "desk"),
                "faixa-1440",
            ))
            app_nav = clip_of(page, "nav.brand-nav")
            ref_nav = clip_of(ref, "nav.dshell")
            shot(page, app_nav, OUT / "nav-1440-app.png")
            shot(ref, ref_nav, OUT / "nav-1440-ref.png")
            report["diff"].append(compare(OUT / "nav-1440-app.png", OUT / "nav-1440-ref.png", [], [], "nav-1440"))

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(150)
            refm = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            refm.goto((REF / "MInicio.html").as_uri(), wait_until="domcontentloaded")
            refm.wait_for_timeout(200)
            report["marca"]["referencia390"] = refm.evaluate("""() => {
              const block = document.querySelector('header div');
              const box = block.getBoundingClientRect();
              return { x: Math.round(box.x), w: Math.round(box.width), h: Math.round(box.height) };
            }""")
            app_mobile = page.evaluate("""() => {
              const bar = document.querySelector('.brand-bar').getBoundingClientRect();
              return { x: bar.x, y: bar.y, width: bar.width, height: bar.height };
            }""")
            ref_mobile = refm.evaluate("""() => {
              const header = document.querySelector('header').getBoundingClientRect();
              const label = document.querySelector('label').getBoundingClientRect();
              return { x: 0, y: header.y, width: 390, height: label.bottom - header.y };
            }""")
            shot(page, app_mobile, OUT / "faixa-390-app.png")
            shot(refm, ref_mobile, OUT / "faixa-390-ref.png")
            report["diff"].append(compare(
                OUT / "faixa-390-app.png", OUT / "faixa-390-ref.png",
                mask_of(page, ".brand-bar", "mobile"),
                refm.evaluate("""() => {
                  const header = document.querySelector('header').getBoundingClientRect();
                  const select = document.querySelector('select').getBoundingClientRect();
                  return [{ x: select.x + 3, y: select.y - header.y + 3, w: select.width - 6, h: select.height - 6 }];
                }"""),
                "faixa-390",
            ))
            app_dock = clip_of(page, ".dock")
            ref_dock = clip_of(refm, "nav")
            shot(page, app_dock, OUT / "barra-390-app.png")
            shot(refm, ref_dock, OUT / "barra-390-ref.png")
            report["diff"].append(compare(OUT / "barra-390-app.png", OUT / "barra-390-ref.png", [], [], "barra-390"))
            browser.close()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
