"""Prova visual do laboratório isolado. Não usa a conta publicada."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\isa\documents\reviews\lancamentos-004ia5")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8108/"


def shot(page, name):
    page.screenshot(path=str(OUT / name), full_page=True)


def fill_paid(page, merchant, amount):
    page.fill("#merchant", merchant)
    page.fill("#noteDate", "2026-10-22")
    page.fill("#amountText", amount)
    page.select_option("#status", "pago")
    page.wait_for_selector("#statusDate")
    page.fill("#statusDate", "2026-10-22")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        page.click("#enter-marina")
        page.wait_for_selector("#desk-lista")
        page.click("#desk-lista")
        page.wait_for_selector("#ledger")
        shot(page, "1440-vazio.png")
        page.click("#new-lot")
        page.wait_for_selector("#review-form")
        assert page.locator(".lot-strip").count() >= 1
        fill_paid(page, "Mercado Central", "100,00")
        page.click("#save")
        page.wait_for_selector("text=Salvo")
        fill_paid(page, "Padaria", "27,90")
        page.click("#save")
        page.wait_for_selector("text=127,90", timeout=10000)
        shot(page, "1440-lote.png")
        page.click("#see-lot")
        page.wait_for_selector("text=Gastos por categoria")
        shot(page, "1440-composicao.png")
        page.click("#desk-lista")
        page.wait_for_selector("#q")
        page.fill("#q", "mercado")
        page.wait_for_timeout(300)
        page.click("#view-lots")
        page.wait_for_selector("text=Valor dos encontrados")
        body = page.locator("body").inner_text()
        assert "100,00" in body, body
        assert "127,90" in body, body
        assert "Valor dos encontrados" in body
        assert "lote completo" in body.lower()
        shot(page, "1440-busca.png")
        for width in (1280, 768, 390, 360):
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(200)
            shot(page, f"{width}.png")
        page.set_viewport_size({"width": 1440, "height": 900})
        hidden = page.locator("#isa-ai-categories")
        if hidden.count():
            assert hidden.first.is_hidden()
        browser.close()
        print("prova visual ok")


if __name__ == "__main__":
    main()
