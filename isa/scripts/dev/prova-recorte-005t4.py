"""Prova de tela do recorte, no laboratório isolado. Não usa a conta publicada."""

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
OUT = ROOT / "documents" / "reviews" / "recorte-005t4"
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8118
BASE = "http://127.0.0.1:%s/" % PORT


def call(method, path, body=None, person="marina"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(BASE.rstrip("/") + path, data=data, method=method)
    request.add_header("X-ISA-Lab-Person", person)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_health(proc):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE + "api/health", timeout=1).read()
            return
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("o laboratório encerrou")
            time.sleep(0.1)
    raise RuntimeError("o laboratório não respondeu")


def shot(page, name):
    page.screenshot(path=str(OUT / name), full_page=True)


def main():
    data = tempfile.mkdtemp(prefix="isa-recorte-")
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
    try:
        wait_health(proc)
        batch = call("POST", "/api/work-batches", {"name": "Obra da casa", "criterion": "outro"})["batch"]
        october = call("POST", "/api/entries", {"entry": {
            "merchant": "Mercado Central", "amountMinor": 10000, "direction": "gasto", "status": "pago",
            "statusDate": "2026-10-22", "noteDate": "2026-10-22", "nature": "consumo", "category": "Alimentação",
            "workBatchId": batch["id"],
        }})["entry"]
        august = call("POST", "/api/entries", {"entry": {
            "merchant": "Material de obra", "amountMinor": 5000, "direction": "gasto", "status": "pago",
            "statusDate": "2026-08-14", "noteDate": "2026-08-14", "nature": "consumo", "category": "Moradia",
            "workBatchId": batch["id"],
        }}, )["entry"]
        outside = call("POST", "/api/entries", {"entry": {
            "merchant": "Fora do lote", "amountMinor": 2200, "direction": "gasto", "status": "pago",
            "statusDate": "2026-09-03", "noteDate": "2026-09-03", "nature": "consumo",
        }})["entry"]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(BASE, wait_until="networkidle")
            page.click("#enter-marina")
            page.wait_for_selector("#desk-lista")
            page.click("#desk-lista")
            page.wait_for_selector("text=Mercado Central")
            page.wait_for_selector("#all-months")
            shot(page, "depois-mes-1440.png")
            page.set_viewport_size({"width": 390, "height": 800})
            page.wait_for_timeout(200)
            shot(page, "depois-mes-390.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.click("#all-months")
            page.wait_for_selector("text=Material de obra")
            page.wait_for_selector("text=Fora do lote")
            shot(page, "depois-todos-1440.png")
            page.set_viewport_size({"width": 390, "height": 800})
            page.wait_for_timeout(200)
            shot(page, "depois-todos-390.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(BASE + "#lote/" + batch["id"], wait_until="networkidle")
            page.wait_for_selector("text=Material de obra")
            page.wait_for_selector("text=Mercado Central")
            shot(page, "depois-lote-1440.png")
            page.set_viewport_size({"width": 390, "height": 800})
            page.wait_for_timeout(200)
            shot(page, "depois-lote-390.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.locator("[data-id='%s']" % august["id"]).click()
            page.wait_for_selector("text=Material de obra")
            shot(page, "depois-detalhe-lote-1440.png")
            page.goto(BASE + "#detalhe/" + outside["id"], wait_until="networkidle")
            page.wait_for_selector("text=Fora do lote")
            shot(page, "depois-detalhe-fora-1440.png")
            page.goto(BASE + "#registrar", wait_until="networkidle")
            page.click("#pick-gasto")
            page.click("#do-type")
            page.wait_for_selector("#merchant")
            page.fill("#merchant", "Mercado Central")
            page.fill("#noteDate", "2026-10-22")
            page.fill("#amountText", "100,00")
            page.click("#save")
            page.wait_for_selector("text=Possível duplicata", timeout=10000)
            shot(page, "depois-duplicata-1440.png")
            page.set_viewport_size({"width": 390, "height": 800})
            page.wait_for_timeout(200)
            shot(page, "depois-duplicata-390.png")
            browser.close()
        print("prova visual ok", october["id"])
    finally:
        proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
