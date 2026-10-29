"""Produção: criador e checkout em 320/390/768, sem envio."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def gigio_covers(page, selector: str) -> bool:
    return page.evaluate(
        """(sel) => {
          const gigio = document.querySelector('.gigio-launch');
          const target = document.querySelector(sel);
          if (!gigio || !target) return false;
          const g = gigio.getBoundingClientRect();
          const t = target.getBoundingClientRect();
          return !(g.right <= t.left || t.right <= g.left || g.bottom <= t.top || t.bottom <= g.top);
        }""",
        selector,
    )


def main() -> None:
    report: dict = {"production": True, "submitted": False}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_default_timeout(45000)
        page.route("**/api/v1/storefront/orders**", lambda route: route.abort())
        page.route("**/api/v1/storefront/fidelity/**", lambda route: route.abort())

        page.goto(BASE, wait_until="domcontentloaded")
        href = page.locator("a.shelf-link[href^='/paes/']").first.get_attribute("href")
        page.goto(f"{BASE}{href}", wait_until="domcontentloaded")
        add = page.get_by_role("button", name="Adicionar à seleção")
        page.wait_for_function(
            """() => {
              const btn = [...document.querySelectorAll('button')].find((el) =>
                el.textContent?.trim() === 'Adicionar à seleção'
              );
              return Boolean(btn && !btn.disabled);
            }"""
        )
        add.click()
        page.get_by_role("heading", name="Sua seleção").wait_for()

        for width, height, tag in ((390, 844, "390"), (320, 720, "320"), (768, 900, "768")):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(f"{BASE}/#criacao", wait_until="domcontentloaded")
            page.get_by_role("button", name=re.compile("branca", re.I)).click()
            page.get_by_role("button", name=re.compile("maturada", re.I)).click()
            page.get_by_role("button", name=re.compile("escolher os sabores", re.I)).click()
            page.get_by_role("button", name=re.compile("escolher a forma", re.I)).click()
            page.get_by_role("button", name=re.compile("pão de forma", re.I)).click()
            page.get_by_role("button", name=re.compile("combinar o encontro", re.I)).click()
            page.get_by_text(re.compile("A Loja faz somente entregas")).wait_for()
            page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            report[f"gigioCoversNote{tag}"] = gigio_covers(page, ".builder-meet .fornada-note")
            report[f"gigioCoversCalendarNote{tag}"] = gigio_covers(page, ".builder-meet .bake-calendar-legend")
            page.screenshot(path=OUT / f"prod-creator-{tag}.png", full_page=True)
            page.goto(f"{BASE}/pedido/novo", wait_until="domcontentloaded")
            page.get_by_text(re.compile("será entregue no endereço indicado")).wait_for()
            page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
            report[f"pickupOnCheckout{tag}"] = page.get_by_text(re.compile(r"\bretirada\b", re.I)).count()
            page.screenshot(path=OUT / f"prod-checkout-{tag}.png", full_page=True)

        browser.close()
    (OUT / "prod-viewports.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
