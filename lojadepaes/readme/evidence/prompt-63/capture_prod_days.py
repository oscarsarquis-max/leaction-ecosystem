"""Produção: comparar dias de fornada home x Criador, sem envio."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def labels(page, root: str) -> list[str]:
    return page.evaluate(
        """(sel) => {
          const scope = document.querySelector(sel) || document;
          return [...scope.querySelectorAll('.bake-day')]
            .filter((el) => el.querySelector('svg'))
            .map((el) => el.getAttribute('aria-label') || '')
            .filter(Boolean);
        }""",
        root,
    )


def keys(items: list[str]) -> list[str]:
    return [item.split(":")[0].strip() for item in items]


def main() -> None:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        page.goto(BASE, wait_until="domcontentloaded")
        page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
        home = labels(page, ".bake-calendar--shelf")
        page.goto(f"{BASE}/#criacao", wait_until="domcontentloaded")
        page.get_by_role("button", name=re.compile("branca", re.I)).click()
        page.get_by_role("button", name=re.compile("maturada", re.I)).click()
        page.get_by_role("button", name=re.compile("escolher os sabores", re.I)).click()
        page.get_by_role("button", name=re.compile("escolher a forma", re.I)).click()
        page.get_by_role("button", name=re.compile("pão de forma", re.I)).click()
        page.get_by_role("button", name=re.compile("combinar o encontro", re.I)).click()
        page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
        creator = labels(page, ".builder-meet .bake-calendar")
        browser.close()
    report = {
        "homeDays": home,
        "creatorDays": creator,
        "sameProductionDays": keys(home) == keys(creator),
        "bundle": "/assets/index-DECrXnns.js",
    }
    (OUT / "prod-days.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
