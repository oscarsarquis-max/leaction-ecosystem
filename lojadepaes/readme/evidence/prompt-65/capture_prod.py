from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ORIGIN = "https://lojadepaes.com.br"
EVIDENCE = Path(__file__).resolve().parent


def section_visible(page, section_id: str) -> bool:
    return page.evaluate(
        """(id) => {
          const el = document.getElementById(id);
          if (!el) return false;
          const r = el.getBoundingClientRect();
          return r.bottom > 0 && r.top < window.innerHeight;
        }""",
        section_id,
    )


def main() -> None:
    report: dict = {"destinations": [], "bundle": None}
    with sync_playwright() as api:
        browser = api.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(30000)
        page.goto(f"{ORIGIN}/", wait_until="domcontentloaded")
        html = page.content()
        match = re.search(r"/assets/index-[^\"']+\.js", html)
        report["bundle"] = match.group(0) if match else None
        page.get_by_role("link", name="Ver receita").first.click()
        page.locator("main.week-recipe-page h1").wait_for()
        report["recipe_url"] = page.url
        report["home_return"] = page.locator(".home-return a").first.get_attribute("href")
        report["menu"] = {
            name: page.get_by_role("navigation", name="Navegação principal").get_by_role("link", name=name).get_attribute("href")
            for name in ("Nossos pães", "Crie seu pão", "À nossa mesa", "Biblioteca do padeiro")
        }
        page.screenshot(path=EVIDENCE / "prod-recipe-1440.png")
        page.get_by_role("navigation", name="Navegação principal").get_by_role("link", name="Nossos pães").click()
        page.wait_for_url(lambda url: url.rstrip("/").endswith("/#paes") and "/receitas/" not in url)
        page.wait_for_function(
            """() => {
              const el = document.getElementById('paes');
              if (!el) return false;
              const r = el.getBoundingClientRect();
              return r.bottom > 0 && r.top < window.innerHeight;
            }"""
        )
        report["destinations"].append("prod-recipe-menu-paes")
        report["section_paes_visible"] = section_visible(page, "paes")
        page.goto(report["recipe_url"])
        page.locator(".home-return a").click()
        page.wait_for_function("() => location.pathname === '/'")
        report["destinations"].append("prod-return-home")
        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        recipe = mobile.new_page()
        recipe.set_default_timeout(30000)
        recipe.goto(report["recipe_url"], wait_until="domcontentloaded")
        recipe.locator(".home-return a").wait_for()
        report["mobile_return_visible"] = recipe.locator(".home-return a").is_visible()
        recipe.get_by_role("button", name="Menu").click()
        recipe.get_by_role("link", name="Crie seu pão").click()
        recipe.wait_for_url(lambda url: url.rstrip("/").endswith("/#criacao") and "/receitas/" not in url)
        report["destinations"].append("prod-mobile-criacao")
        recipe.screenshot(path=EVIDENCE / "prod-home-390.png")
        mobile.close()
        context.close()
        browser.close()
    (EVIDENCE / "prod.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
