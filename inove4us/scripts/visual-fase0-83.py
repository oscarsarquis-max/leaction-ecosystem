"""Teste visual Fase 0 em produção: 🧩 na frente do card + rascunho Dia a Dia.

Salva screenshots em inove4us/var/evidencias-fase0-83/.
Não imprime senhas. Login via /acesso check-email granted.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import TimeoutError as PwTimeout
from playwright.sync_api import sync_playwright

BASE = "https://inove4us.com.br"
EMAIL = "inovador@inove4us.com.br"
OUT = Path(__file__).resolve().parents[1] / "var" / "evidencias-fase0-83"
OUT.mkdir(parents=True, exist_ok=True)
MARKER = f"rascunho-80-{uuid.uuid4().hex[:6]}"


def shot(page, name: str):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def dismiss_modals(page):
    for sel in [
        'button:has-text("Cancelar")',
        'button:has-text("Pular")',
        'button:has-text("Agora não")',
        'button:has-text("Fechar")',
        '[aria-label="Fechar"]',
    ]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=2000)
                page.wait_for_timeout(300)
        except Exception:
            pass
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)


def login(page):
    page.goto(f"{BASE}/acesso", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(800)
    dismiss_modals(page)
    if page.locator("text=Olá").count() or "/mesa-do-inovador" in page.url or page.locator('button:has-text("Sair")').count():
        if "/acesso" in page.url:
            page.goto(f"{BASE}/mesa-do-inovador", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(800)
        return
    email = page.locator('input[type="email"], input[name="email"]').first
    email.wait_for(state="visible", timeout=20000)
    email.fill(EMAIL)
    page.locator('button[type="submit"]').first.click()
    page.wait_for_url(lambda url: "/acesso" not in url, timeout=30000)
    page.wait_for_timeout(1200)
    dismiss_modals(page)


def z_stack_report(page) -> dict:
    return page.evaluate(
        """() => {
          const btn = document.querySelector('button[title="Adaptação inclusiva (PEI)"]');
          const menu = document.querySelector('[role="menu"]');
          if (!btn || !menu) return { ok: false, reason: 'menu ou botão ausente' };
          const br = btn.getBoundingClientRect();
          const mr = menu.getBoundingClientRect();
          const stacked = [];
          const cx = mr.left + Math.min(40, mr.width / 2);
          const cy = mr.top + 24;
          let n = document.elementFromPoint(cx, cy);
          let hops = 0;
          while (n && hops < 12) {
            stacked.push({
              tag: n.tagName,
              z: getComputedStyle(n).zIndex,
              cls: (n.className || '').toString().slice(0, 80),
            });
            n = n.parentElement;
            hops += 1;
          }
          const menuStyle = getComputedStyle(menu);
          return {
            ok: true,
            menu_z: menuStyle.zIndex,
            menu_position: menuStyle.position,
            menu_rect: { top: mr.top, left: mr.left, w: mr.width, h: mr.height },
            btn_rect: { top: br.top, left: br.left, w: br.width, h: br.height },
            top_at_menu: stacked[0] || null,
            menu_contains_top: menu.contains(document.elementFromPoint(cx, cy)),
          };
        }"""
    )


def main() -> int:
    report = {"email": EMAIL, "shots": [], "tests": {}}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(OUT / "chrome-profile"),
            headless=True,
            viewport={"width": 1400, "height": 900},
            locale="pt-BR",
        )
        page = ctx.new_page()
        try:
            login(page)
            report["shots"].append(shot(page, "01-apos-login"))

            run76 = False
            import requests

            if run76:
            s.post(f"{BASE}/api/auth/check-email", json={"email": EMAIL}, timeout=20)
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            # reuse browser cookie jar
            for c in ctx.cookies():
                s.cookies.set(c["name"], c["value"], domain=c.get("domain") or "inove4us.com.br")
            r = s.post(
                f"{BASE}/api/desafios",
                json={
                    "titulo": f"[QA-Fase0] visual-76-{MARKER}",
                    "plan_data": {
                        "missao": "teste visual 76",
                        "plano": {
                            "tarefas_kanban": [
                                {
                                    "id": f"c-{MARKER}",
                                    "titulo": "Card visual 76 na coluna",
                                    "coluna": "para_fazer",
                                }
                            ]
                        },
                    },
                },
                timeout=20,
            )
            body = r.json() or {}
            did = body.get("desafio_id") or (body.get("desafio") or {}).get("id")
            if did:
                s.put(
                    f"{BASE}/api/desafios/{did}",
                    json={
                        "kanban_state": {
                            "tarefas": [
                                {
                                    "id": f"c-{MARKER}",
                                    "titulo": "Card visual 76 na coluna",
                                    "coluna": "para_fazer",
                                }
                            ]
                        }
                    },
                    timeout=20,
                )
            report["desafio_id"] = did
            page.goto(f"{BASE}/desafios/{did}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            dismiss_modals(page)
            report["shots"].append(shot(page, "02-desafio-antes-menu"))
            pei_btn = page.locator('button[title="Adaptação inclusiva (PEI)"]').first
            pei_btn.wait_for(state="visible", timeout=15000)
            pei_btn.click()
            page.wait_for_timeout(400)
            page.locator('[role="menu"], button:has-text("TDAH")').first.wait_for(state="visible", timeout=8000)
            stack = z_stack_report(page)
            report["tests"]["76_menu_frente"] = stack
            report["shots"].append(shot(page, "03-menu-pei-aberto"))
            page.locator('[role="menuitem"]:has-text("TDAH")').first.click()
            page.wait_for_timeout(15000)
            report["shots"].append(shot(page, "04-subcard-apos-tdah"))
            sub_visible = page.locator("text=Adaptação PEI").count() > 0 or page.locator("text=TDAH").count() > 0
            report["tests"]["76_subcard_visivel"] = bool(sub_visible)
            # fechar aba de verdade e reabrir
            page.close()
            page2 = ctx.new_page()
            page2.goto(f"{BASE}/desafios/{did}", wait_until="domcontentloaded", timeout=60000)
            page2.wait_for_timeout(1500)
            dismiss_modals(page2)
            report["shots"].append(shot(page2, "05-desafio-reaberto"))
            report["tests"]["76_reaberto_puzzle"] = page2.locator(
                'button[title="Adaptação inclusiva (PEI)"]'
            ).count() > 0
            report["tests"]["76_reaberto_subcard"] = page2.locator("text=Adaptação PEI").count() > 0
            page2.close()

            # --- 80: rascunho dia a dia ---
            page3 = ctx.new_page()
            login(page3)
            page3.goto(f"{BASE}/dia-a-dia/nova", wait_until="networkidle", timeout=60000)
            page3.wait_for_timeout(1500)
            dismiss_modals(page3)
            report["shots"].append(shot(page3, "06-dia-a-dia-nova-crua"))
            report["tests"]["80_heading"] = page3.locator("text=Montar o ciclo").count() > 0
            report["tests"]["80_n_textarea"] = page3.locator("textarea").count()
            report["tests"]["80_n_input"] = page3.locator("input").count()
            # preencher acolhida + conteúdo sem tema
            tas = page3.locator("textarea")
            if tas.count() >= 1:
                tas.nth(0).fill(f"Acolhida {MARKER}")
            if tas.count() >= 2:
                tas.nth(1).fill(f"Conteudo {MARKER}")
            page3.wait_for_timeout(1200)
            report["shots"].append(shot(page3, "06-rascunho-sem-tema"))
            ls = page3.evaluate(
                """() => {
                  const keys = Object.keys(localStorage).filter(k => k.includes('dia-a-dia.rascunho'));
                  const sample = keys[0] ? localStorage.getItem(keys[0]) : null;
                  return { keys, sample };
                }"""
            )
            report["tests"]["80_localstorage"] = {
                "keys": ls.get("keys"),
                "contem_marker": MARKER in (ls.get("sample") or ""),
            }
            page3.close()
            page4 = ctx.new_page()
            page4.goto(f"{BASE}/dia-a-dia/nova", wait_until="networkidle", timeout=60000)
            page4.wait_for_timeout(1500)
            dismiss_modals(page4)
            vals = []
            for i in range(page4.locator("textarea").count()):
                try:
                    vals.append(page4.locator("textarea").nth(i).input_value())
                except Exception:
                    vals.append(page4.locator("textarea").nth(i).inner_text())
            report["tests"]["80_textarea_vals"] = [v[:120] for v in vals]
            report["tests"]["80_reabriu_rascunho"] = any(MARKER in (v or "") for v in vals)
            report["shots"].append(shot(page4, "07-dia-a-dia-reaberto"))
            tema = page4.locator('input[placeholder*="Termodinâmica"], input').filter(
                has_text=""
            )
            tema_input = page4.locator("span.field-label:has-text('Tema da aula')").locator("xpath=../input")
            if tema_input.count():
                tema_input.first.fill(f"Tema real {MARKER}")
            else:
                # first text input that isn't date
                for i in range(page4.locator("input").count()):
                    inp = page4.locator("input").nth(i)
                    typ = inp.get_attribute("type") or "text"
                    if typ in ("text", "search", ""):
                        ph = (inp.get_attribute("placeholder") or "")
                        if "Termodinâmica" in ph or "tema" in ph.lower() or i == 0:
                            inp.fill(f"Tema real {MARKER}")
                            break
            page4.wait_for_timeout(2500)
            banner = page4.locator("text=plano gratuito").count() or page4.locator("text=Profissional").count()
            report["shots"].append(shot(page4, "08-apos-preencher-tema"))
            report["tests"]["80_url_apos_tema"] = page4.url
            report["tests"]["80_materializou"] = "/dia-a-dia/" in page4.url and "/nova" not in page4.url
            report["tests"]["80_quota_banner"] = bool(banner)
            report["shots"].append(shot(page4, "09-aula-materializada"))
        except Exception as exc:
            report["error"] = f"{type(exc).__name__}: {exc}"
            try:
                report["shots"].append(shot(page, "99-erro"))
            except Exception:
                pass
        finally:
            ctx.close()

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    t76 = report.get("tests") or {}
    ok76 = bool(t76.get("76_menu_frente", {}).get("menu_contains_top")) and t76.get("76_reaberto_subcard")
    ok80 = bool(t76.get("80_reabriu_rascunho"))
    return 0 if ok76 and ok80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
