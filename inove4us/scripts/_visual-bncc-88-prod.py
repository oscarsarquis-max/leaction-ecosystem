# -*- coding: utf-8 -*-
"""Prompt 88: seletor BNCC com codigo visivel (producao). Locators ASCII-safe."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://inove4us.com.br"
EMAIL = "homologador@leaction.com.br"
OUT = Path(__file__).resolve().parents[1] / "var" / "evidencias-bncc-88"
OUT.mkdir(parents=True, exist_ok=True)
CODE_RE = re.compile(r"^(EF|EM)\d{2}[A-Z]{2,}\d{2}\s")


def shot(page, name: str) -> str:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def dismiss(page):
    for sel in [
        'button:has-text("Cancelar")',
        'button:has-text("Pular")',
        'button:has-text("Agora nao")',
        'button:has-text("Agora não")',
        'button:has-text("Fechar")',
        '[aria-label="Fechar"]',
    ]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=1200)
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
    email = page.locator('input[type="email"], input[name="email"]').first
    email.wait_for(state="visible", timeout=20000)
    email.fill(EMAIL)
    page.locator("button[type=submit]").first.click()
    page.wait_for_timeout(2500)
    dismiss(page)


def select_option_containing(page, label_re: str, option_re: str) -> str:
    chosen = page.evaluate(
        """({ labelRe, optionRe }) => {
          const lr = new RegExp(labelRe, 'i');
          const or = new RegExp(optionRe, 'i');
          const labels = Array.from(document.querySelectorAll('label'));
          const lab = labels.find(l => lr.test(l.innerText || ''));
          if (!lab) return { ok: false, reason: 'label_not_found' };
          const sel = lab.querySelector('select');
          if (!sel) return { ok: false, reason: 'no_select' };
          const opts = Array.from(sel.options).map(o => ({ value: o.value, text: o.textContent || '' }));
          const hit = opts.find(o => or.test(o.text) && o.value !== '');
          if (!hit) return { ok: false, reason: 'option_not_found', opts: opts.map(o => o.text).slice(0, 8) };
          sel.value = hit.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return { ok: true, text: hit.text };
        }""",
        {"labelRe": label_re, "optionRe": option_re},
    )
    if not chosen.get("ok"):
        raise RuntimeError(f"select failed {label_re}: {chosen}")
    page.wait_for_timeout(800)
    return chosen.get("text") or ""


def main() -> int:
    report = {"email": EMAIL, "tests": {}, "shots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 980}, locale="pt-BR")
        page = ctx.new_page()
        try:
            login(page)
            page.goto(f"{BASE}/dia-a-dia/nova", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            dismiss(page)
            if page.get_by_text(re.compile(r"Montar o ciclo")).count() == 0:
                page.goto(f"{BASE}/dia-a-dia", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1200)
                dismiss(page)
                page.get_by_role("link", name=re.compile(r"Planejar Nova Aula")).click()
                page.wait_for_timeout(2000)
            page.get_by_text(re.compile(r"Montar o ciclo")).first.wait_for(state="visible", timeout=25000)
            page.get_by_text(re.compile(r"Planejamento escolar")).first.wait_for(state="visible", timeout=25000)
            select_option_containing(page, r"Institui", r"Escola Teste")
            select_option_containing(page, r"odo letivo", r".+")
            select_option_containing(page, r"^[\s\S]*Curso", r"Fundamental")
            select_option_containing(page, r"Disciplina", r"Matem")
            page.wait_for_timeout(2500)

            data = page.evaluate(
                """() => {
                  const labels = Array.from(document.querySelectorAll('label'));
                  const lab = labels.find(l => /T[oó]pico da ementa/i.test(l.innerText || ''));
                  const sel = lab && lab.querySelector('select');
                  if (!sel) return { found: false };
                  const bncc = sel.querySelector('optgroup[label*="BNCC"]');
                  const texts = bncc
                    ? Array.from(bncc.querySelectorAll('option')).map(o => (o.textContent || '').trim())
                    : [];
                  sel.size = Math.min(16, Math.max(8, texts.length + 1));
                  sel.style.height = 'auto';
                  sel.style.maxHeight = '420px';
                  return { found: true, texts, selected: sel.options[sel.selectedIndex] && sel.options[sel.selectedIndex].text };
                }"""
            )
            texts = data.get("texts") or []
            missing = [t for t in texts if not CODE_RE.search(t)]
            ef01 = next((t for t in texts if t.startswith("EF06MA01")), None)
            report["tests"] = {
                "n_bncc": len(texts),
                "all_start_with_code": not missing,
                "missing_code_sample": missing[:5],
                "ef06ma01": ef01,
                "ef06ma01_code_first": bool(ef01 and ef01.startswith("EF06MA01")),
            }
            report["shots"].append(shot(page, "01-seletor-codigos"))
            if ef01:
                select_option_containing(page, r"T[oó]pico da ementa", r"EF06MA01")
                page.wait_for_timeout(400)
                report["shots"].append(shot(page, "02-ef06ma01-selecionado"))
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
    tests = report.get("tests") or {}
    ok = (
        not report.get("error")
        and tests.get("all_start_with_code")
        and tests.get("ef06ma01_code_first")
        and tests.get("n_bncc", 0) >= 30
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
