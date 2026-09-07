# -*- coding: utf-8 -*-
"""Prompt 86: duas listas + cache conteudo + metodologia sem IA (producao)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://inove4us.com.br"
EMAIL = "homologador@leaction.com.br"
OUT = Path(__file__).resolve().parents[1] / "var" / "evidencias-bncc-86"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name: str) -> str:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def dismiss(page):
    for sel in ['button:has-text("Cancelar")', 'button:has-text("Pular")', 'button:has-text("Fechar")']:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=1000)
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(800)
    dismiss(page)
    if page.locator('button:has-text("Sair")').count():
        return
    page.locator('input[type="email"], input[name="email"]').first.fill(EMAIL)
    page.locator("button[type=submit]").first.click()
    page.wait_for_timeout(2500)
    dismiss(page)


def pick_select(page, label_re, option_re):
    chosen = page.evaluate(
        """({ labelRe, optionRe }) => {
          const lr = new RegExp(labelRe, 'i');
          const or = new RegExp(optionRe, 'i');
          const lab = Array.from(document.querySelectorAll('label')).find(l => lr.test(l.innerText || ''));
          const sel = lab && lab.querySelector('select');
          if (!sel) return { ok: false };
          const hit = Array.from(sel.options).find(o => or.test(o.textContent || '') && o.value);
          if (!hit) return { ok: false, opts: Array.from(sel.options).map(o => o.textContent) };
          sel.value = hit.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return { ok: true, text: hit.textContent };
        }""",
        {"labelRe": label_re, "optionRe": option_re},
    )
    if not chosen.get("ok"):
        raise RuntimeError(f"select fail {label_re} {chosen}")
    page.wait_for_timeout(700)
    return chosen.get("text")


def main() -> int:
    report = {"email": EMAIL, "tests": {}, "shots": [], "network": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 980}, locale="pt-BR")
        page = ctx.new_page()

        def on_resp(resp):
            u = resp.url
            if "/api/daily/" in u and any(x in u for x in ("conteudo", "metodologia", "dinamicas", "bncc")):
                try:
                    body = resp.json()
                except Exception:
                    body = {}
                report["network"].append(
                    {
                        "url": u.split("?")[0],
                        "status": resp.status,
                        "ia_called": body.get("ia_called"),
                        "cached": body.get("cached"),
                        "fonte": body.get("fonte"),
                    }
                )

        page.on("response", on_resp)
        try:
            login(page)
            page.goto(f"{BASE}/dia-a-dia/nova", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            dismiss(page)
            if page.get_by_text(re.compile(r"Montar o ciclo")).count() == 0:
                page.goto(f"{BASE}/dia-a-dia", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1200)
                page.get_by_role("link", name=re.compile(r"Planejar Nova Aula")).click()
                page.wait_for_timeout(2000)
            page.get_by_text(re.compile(r"Montar o ciclo")).first.wait_for(timeout=25000)
            pick_select(page, r"Institui", r"Escola Teste")
            pick_select(page, r"odo letivo", r".+")
            pick_select(page, r"^[\s\S]*Curso", r"Fundamental")
            pick_select(page, r"Disciplina", r"Matem")
            page.wait_for_timeout(2000)
            body = page.inner_text("body")
            report["tests"]["duas_listas"] = "BNCC (catálogo)" in body or "BNCC (catalogo)" in body
            report["tests"]["ementa_lista"] = "Ementa da escola" in body
            report["tests"]["sem_alerta_conflito"] = "conflito" not in body.lower()
            report["shots"].append(shot(page, "01-duas-listas"))

            page.get_by_text(re.compile(r"EF06MA01")).first.click()
            page.wait_for_timeout(8000)
            report["tests"]["campo_conteudo"] = page.get_by_text(re.compile(r"Conteúdo sugerido")).count() > 0
            report["shots"].append(shot(page, "02-conteudo-sugerido"))

            met = page.locator("select").filter(has_text=re.compile(r"metodologia|Minute|Dinâmica", re.I))
            # fallback: last min-h-11 select in dinamica block
            selects = page.locator("select")
            n = selects.count()
            if n:
                selects.nth(n - 1).select_option(index=1)
            page.wait_for_timeout(2000)
            report["shots"].append(shot(page, "03-metodologia"))
            ia_met = [x for x in report["network"] if x["url"].endswith("/metodologia")]
            report["tests"]["metodologia_sem_ia"] = all(x.get("ia_called") is False for x in ia_met) and bool(ia_met)
            conteudos = [x for x in report["network"] if x["url"].endswith("/conteudo-sugerido")]
            report["tests"]["primeira_ia"] = any(x.get("ia_called") is True and x.get("cached") is False for x in conteudos) or any(
                x.get("cached") is True for x in conteudos
            )
            report["url"] = page.url
        except Exception as exc:
            report["error"] = f"{type(exc).__name__}: {exc}"
            try:
                report["shots"].append(shot(page, "99-erro"))
            except Exception:
                pass
        finally:
            ctx.close()
            browser.close()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report.get("error") and report["tests"].get("duas_listas") else 1


if __name__ == "__main__":
    raise SystemExit(main())
