"""Produção: navegação e validação sem envio de pedido."""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "https://lojadepaes.com.br"


def production_labels(page, root: str) -> list[str]:
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


def day_keys(labels: list[str]) -> list[str]:
    return [label.split(":")[0].strip() for label in labels]


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
    report: dict = {"production": True, "submitted": False, "blockedPosts": []}
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)

        def block_mutations(route):
            report["blockedPosts"].append(route.request.url)
            route.abort()

        page.route("**/api/v1/storefront/orders**", block_mutations)
        page.route("**/api/v1/storefront/fidelity/**", block_mutations)
        page.route("**/api/v1/date-requests**", block_mutations)

        health = page.request.get(f"{BASE}/api/v1/health")
        ready = page.request.get(f"{BASE}/api/v1/ready")
        report["health"] = health.status
        report["ready"] = ready.status
        report["readyBody"] = ready.json() if ready.ok else ready.text()[:200]

        page.goto(BASE, wait_until="domcontentloaded")
        page.get_by_role("heading", name="Escolha sua fornada").wait_for()
        page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
        report["bundle"] = page.evaluate(
            """() => [...document.querySelectorAll('script[src*="/assets/index-"]')].map(el => el.src.split('/').pop())[0]"""
        )
        home_days = production_labels(page, ".bake-calendar--shelf")
        report["homeDays"] = home_days
        page.screenshot(path=OUT / "prod-home-1440.png", full_page=True)

        page.goto(f"{BASE}/#criacao", wait_until="domcontentloaded")
        page.get_by_role("heading", name="Criador de Pães").wait_for()
        page.get_by_role("button", name=re.compile("branca", re.I)).click()
        page.get_by_role("button", name=re.compile("maturada", re.I)).click()
        page.get_by_role("button", name=re.compile("escolher os sabores", re.I)).click()
        page.get_by_role("button", name=re.compile("escolher a forma", re.I)).click()
        page.get_by_role("button", name=re.compile("pão de forma", re.I)).click()
        page.get_by_role("button", name=re.compile("combinar o encontro", re.I)).click()
        page.get_by_text(re.compile("A Loja faz somente entregas")).wait_for()
        report["pickupInviteOnStep4"] = page.get_by_text(re.compile("retirada é a modalidade", re.I)).count()
        page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
        creator_days = production_labels(page, ".builder-meet .bake-calendar")
        report["creatorDays"] = creator_days
        report["sameProductionDays"] = day_keys(creator_days) == day_keys(home_days)
        qty = page.get_by_role("spinbutton", name="Quantidade", exact=True)
        box = qty.bounding_box()
        report["quantityBox"] = box
        page.screenshot(path=OUT / "prod-creator-1440.png", full_page=True)

        page.goto(BASE, wait_until="domcontentloaded")
        href = page.locator('a.shelf-link[href^="/paes/"]').first.get_attribute("href")
        report["productHref"] = href
        page.goto(f"{BASE}{href}", wait_until="domcontentloaded")
        add = page.get_by_role("button", name="Adicionar à seleção")
        add.wait_for()
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
        page.goto(f"{BASE}/pedido/novo", wait_until="domcontentloaded")
        page.get_by_text(re.compile("será entregue no endereço indicado")).wait_for()
        page.get_by_text("Consultando as fornadas…").wait_for(state="hidden")
        report["pickupOnCheckout"] = page.get_by_text(re.compile("retirada", re.I)).count()
        report["hasPreferredTime"] = page.get_by_label("Horário preferido para entrega").count()
        report["hasAddressGroup"] = page.get_by_role("group", name="Endereço de entrega").count()
        page.screenshot(path=OUT / "prod-checkout-1440.png", full_page=True)

        page.get_by_label("Nome de quem pede").fill("Visitante de prova")
        page.get_by_label("E-mail para acompanhar o pedido").fill("prova-nao-enviar@example.test")
        open_day = page.locator("button.bake-day:not([disabled])").first
        if open_day.count():
            open_day.click()
            page.wait_for_function(
                """() => {
                  const btn = [...document.querySelectorAll('button.primary')].find((el) =>
                    /enviar pedido/i.test(el.textContent || '')
                  );
                  return btn && !btn.disabled;
                }"""
            )
        send = page.get_by_role("button", name="Enviar pedido")
        report["sendEnabled"] = send.is_enabled()
        if send.is_enabled():
            send.click()
            page.get_by_role("alert").wait_for()
            report["clientValidation"] = page.get_by_role("alert").all_inner_texts()
        else:
            report["clientValidation"] = ["botão permaneceu desabilitado; validação de endereço comprovada no isolado"]
        report["blockedPostsAfterAttempt"] = list(report["blockedPosts"])

        page.get_by_role("button", name="Conversar com Gigio").click()
        page.get_by_label("Mensagem para o Gigio").wait_for()
        page.wait_for_function(
            """() => {
              const box = document.querySelector('[aria-label="Mensagem para o Gigio"]');
              return box && !box.disabled;
            }"""
        )
        before = page.locator(".gigio-msg.is-assistant").count()
        page.get_by_label("Mensagem para o Gigio").fill("Vocês fazem retirada?")
        page.locator(".gigio-form button[type='submit']").click()
        page.wait_for_function(
            """(n) => document.querySelectorAll('.gigio-msg.is-assistant').length > n""",
            arg=before,
            timeout=90000,
        )
        page.wait_for_function(
            """() => !document.body.innerText.includes('Gigio está consultando')""",
            timeout=90000,
        )
        reply = page.locator(".gigio-msg.is-assistant").last.inner_text()
        report["gigioPickup"] = reply[:800]
        report["gigioMentionsDeliveryOnly"] = bool(
            re.search(r"somente entregas|não (oferece|faz|há) retirada|não trabalha com retirada", reply, re.I)
        )
        report["gigioHasPersonalEmail"] = page.get_by_text(re.compile(r"oscar@", re.I)).count()
        page.screenshot(path=OUT / "prod-gigio-retirada.png")

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
            page.screenshot(path=OUT / f"prod-creator-{tag}.png", full_page=True)
            page.goto(f"{BASE}/pedido/novo", wait_until="domcontentloaded")
            page.get_by_text(re.compile("será entregue no endereço indicado")).wait_for()
            page.screenshot(path=OUT / f"prod-checkout-{tag}.png", full_page=True)

        browser.close()

    (OUT / "prod.txt").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
