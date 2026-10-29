"""Captura isolada do painel de notificação. Não abre produção nem envia push."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\lojadepaes\readme\evidence\prompt-102b")
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
:root{--paper:#faf8f2;--ink:#36392e;--muted:#707064;--terra:#98533c;--line:#deddd2}
*{box-sizing:border-box}body{margin:0;background:#b7b3a4;color:var(--ink);font-family:'Segoe UI',sans-serif}
.admin-primary,.admin-secondary{border-radius:3px;padding:12px 16px;font-size:14px;min-height:44px}
.admin-primary{background:var(--terra);color:#fff;border:0}
.admin-secondary{background:transparent;border:1px solid var(--line)}
.admin-actions{display:flex;flex-wrap:wrap;gap:10px}
.admin-muted{color:var(--muted);font-size:14px}
.admin-push{box-sizing:border-box;width:min(1100px,100%);margin:0 auto;padding:16px 20px 0;background:var(--paper);min-height:100vh}
.admin-push h2{font-weight:400;font-size:22px;margin:0 0 8px}
.admin-push p{margin:0 0 10px;line-height:1.5}
.admin-push summary{min-height:44px;display:flex;align-items:center}
@media(max-width:720px){.admin-push{padding:12px 16px 0}}
</style></head><body>
<section class="admin-push">
  <h2>Notificações neste aparelho</h2>
  <p>Disponível para ativar. A permissão só é pedida depois do clique.</p>
  <button class="admin-primary" type="button">Ativar notificações neste aparelho</button>
  <details open><summary>Como ativar no Android e no iPhone</summary>
  <p>No Android compatível, toque em Ativar e permita o aviso.</p>
  <p>No iPhone ou iPad, adicione a Loja à Tela de Início, abra pelo ícone e então ative.</p>
  </details>
</section></body></html>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as api:
        browser = api.chromium.launch()
        for width in (1280, 390, 320):
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.set_content(HTML)
            box = page.locator("h2").bounding_box()
            scroll = page.evaluate(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            print(width, "title_left", round(box["x"], 1) if box else None, "scroll", scroll)
            page.screenshot(path=str(OUT / f"push-{width}.png"))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
