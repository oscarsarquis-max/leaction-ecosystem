# -*- coding: utf-8 -*-
"""Prompt 87: seletor BNCC no Dia a Dia (producao). Locators ASCII-safe."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://inove4us.com.br"
EMAIL = "homologador@leaction.com.br"
OUT = Path(__file__).resolve().parents[1] / "var" / "evidencias-bncc-87"
OUT.mkdir(parents=True, exist_ok=True)

EF06CI04_TEXTO = (
    "Associar a producao de medicamentos e outros materiais sinteticos ao "
    "desenvolvimento cientifico e tecnologico, reconhecendo beneficios e "
    "avaliando impactos socioambientais."
)
# Official (with accents) — compared after NFKD strip in Python below
EF06CI04_TEXTO_OFFICIAL = (
    "Associar a produção de medicamentos e outros materiais sintéticos ao "
    "desenvolvimento científico e tecnológico, reconhecendo benefícios e "
    "avaliando impactos socioambientais."
)
EMENTA_MARK = "Ementa fict"


def fold(s: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)
    ).lower()


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
    """Pick a <select> whose wrapping label matches label_re; choose option matching option_re."""
    chosen = page.evaluate(
        """({ labelRe, optionRe }) => {
          const lr = new RegExp(labelRe, 'i');
          const or = new RegExp(optionRe, 'i');
          const labels = Array.from(document.querySelectorAll('label'));
          const lab = labels.find(l => lr.test(l.innerText || ''));
          if (!lab) return { ok: false, reason: 'label_not_found', labels: labels.map(l => (l.innerText||'').slice(0,80)) };
          const sel = lab.querySelector('select');
          if (!sel) return { ok: false, reason: 'no_select' };
          const opts = Array.from(sel.options).map(o => ({ value: o.value, text: o.textContent || '' }));
          const hit = opts.find(o => or.test(o.text) && o.value !== '');
          if (!hit) return { ok: false, reason: 'option_not_found', opts: opts.map(o => o.text) };
          sel.value = hit.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return { ok: true, text: hit.text, n_opts: opts.length };
        }""",
        {"labelRe": label_re, "optionRe": option_re},
    )
    if not chosen.get("ok"):
        raise RuntimeError(f"select failed {label_re}: {chosen}")
    page.wait_for_timeout(900)
    return chosen.get("text") or ""


def main() -> int:
    report = {"email": EMAIL, "tests": {}, "shots": [], "bncc_requests": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="pt-BR")
        page = ctx.new_page()

        def on_response(resp):
            if "/api/daily/bncc-temas" in resp.url:
                try:
                    body = resp.json()
                except Exception:
                    body = {"_raw_status": resp.status}
                report["bncc_requests"].append(
                    {
                        "url": resp.url,
                        "status": resp.status,
                        "count": body.get("count"),
                        "n": len(body.get("items") or []),
                    }
                )

        page.on("response", on_response)
        try:
            login(page)
            page.goto(f"{BASE}/dia-a-dia/nova", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            dismiss(page)
            if page.get_by_text(re.compile(r"Montar o ciclo")).count() == 0:
                page.goto(f"{BASE}/dia-a-dia", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1500)
                dismiss(page)
                page.get_by_role("link", name=re.compile(r"Planejar Nova Aula")).click()
                page.wait_for_timeout(2000)
            page.get_by_text(re.compile(r"Montar o ciclo")).first.wait_for(
                state="visible", timeout=25000
            )
            report["url"] = page.url
            report["tests"]["heading"] = page.get_by_text(re.compile(r"Montar o ciclo")).count()
            page.get_by_text(re.compile(r"Planejamento escolar")).first.wait_for(
                state="visible", timeout=25000
            )
            report["shots"].append(shot(page, "01-nova-antes-vinculo"))

            report["tests"]["instituicao"] = select_option_containing(
                page, r"Institui", r"Escola Teste"
            )
            page.wait_for_timeout(1000)
            report["tests"]["periodo"] = select_option_containing(page, r"Per[ií]odo letivo", r".+")
            page.wait_for_timeout(1000)
            report["tests"]["curso"] = select_option_containing(page, r"^[\s\S]*Curso", r"Fundamental")
            page.wait_for_timeout(1000)
            report["tests"]["disciplina"] = select_option_containing(page, r"Disciplina", r"Matem")
            page.wait_for_timeout(2500)

            groups = page.evaluate(
                """() => {
                  const labels = Array.from(document.querySelectorAll('label'));
                  const lab = labels.find(l => /T[oó]pico da ementa/i.test(l.innerText || ''));
                  if (!lab) {
                    return {
                      found: false,
                      labels: labels.map(l => (l.innerText || '').split('\\n')[0]).slice(0, 20),
                      emptyHint: (document.body.innerText || '').includes('Sem catálogo')
                        || (document.body.innerText || '').includes('Sem catalogo'),
                    };
                  }
                  const sel = lab.querySelector('select');
                  return {
                    found: true,
                    groups: Array.from(sel.querySelectorAll('optgroup')).map(g => ({
                      label: g.label,
                      n: g.querySelectorAll('option').length,
                      sample: Array.from(g.querySelectorAll('option')).slice(0, 4).map(o => o.textContent),
                    })),
                    n_options: sel.options.length,
                    texts: Array.from(sel.options).map(o => o.textContent),
                  };
                }"""
            )
            report["tests"]["seletor"] = {
                k: v for k, v in groups.items() if k != "texts"
            }
            report["tests"]["seletor_n_texts"] = len(groups.get("texts") or [])
            report["shots"].append(shot(page, "02-seletor-matematica"))

            texts = groups.get("texts") or []
            glabels = [g.get("label") for g in (groups.get("groups") or [])]
            report["tests"]["bncc_optgroup"] = any("BNCC" in (g or "") for g in glabels)
            report["tests"]["ementa_optgroup"] = any("Ementa" in (g or "") for g in glabels)
            report["tests"]["ef06ma01_in_select"] = any("EF06MA01" in t for t in texts)
            report["tests"]["ementa_livre"] = any(EMENTA_MARK.lower() in fold(t) for t in texts)
            report["tests"]["n_bncc_options"] = next(
                (g["n"] for g in (groups.get("groups") or []) if "BNCC" in (g.get("label") or "")),
                0,
            )
            report["tests"]["bncc_sample"] = next(
                (g.get("sample") for g in (groups.get("groups") or []) if "BNCC" in (g.get("label") or "")),
                [],
            )

            api = page.evaluate(
                """async () => {
                  const q = (d, a) => '/api/daily/bncc-temas?disciplina=' + encodeURIComponent(d) + '&curso_ano=' + encodeURIComponent(a);
                  const mat = await fetch(q('Matemática', '6º ano'), { credentials: 'include' }).then(r => r.json());
                  const cie = await fetch(q('Ciências', '6º ano'), { credentials: 'include' }).then(r => r.json());
                  const ef = (cie.items || []).find(i => i.habilidade_codigo === 'EF06CI04');
                  const ma = (mat.items || []).find(i => i.habilidade_codigo === 'EF06MA01');
                  return {
                    mat_count: mat.count,
                    cie_count: cie.count,
                    ef06ci04: ef || null,
                    ef06ma01: ma || null,
                  };
                }"""
            )
            ef = api.get("ef06ci04") or {}
            report["tests"]["api"] = {
                "mat_count": api.get("mat_count"),
                "cie_count": api.get("cie_count"),
                "ef06ci04_tema": ef.get("tema"),
                "ef06ci04_codigo": ef.get("habilidade_codigo"),
                "ef06ci04_texto": ef.get("texto_oficial"),
                "ef06ci04_match": fold(ef.get("texto_oficial") or "") == fold(EF06CI04_TEXTO_OFFICIAL)
                and (ef.get("tema") or "") == "Matéria e energia",
                "ef06ma01_tema": (api.get("ef06ma01") or {}).get("tema"),
            }

            if report["tests"]["ef06ma01_in_select"]:
                select_option_containing(page, r"T[oó]pico da ementa", r"EF06MA01")
                page.wait_for_timeout(500)
                report["shots"].append(shot(page, "03-tema-ef06ma01"))
        except Exception as exc:
            report["error"] = f"{type(exc).__name__}: {exc}"
            try:
                report["body_snip"] = page.inner_text("body")[:1500]
            except Exception:
                pass
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
    api = tests.get("api") or {}
    ok = (
        not report.get("error")
        and tests.get("bncc_optgroup")
        and tests.get("n_bncc_options", 0) > 0
        and tests.get("ementa_optgroup")
        and tests.get("ementa_livre")
        and api.get("ef06ci04_match")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
