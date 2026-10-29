"""Captura isolada da margem da agenda. Não abre produção nem envia mensagem."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\lojadepaes\readme\evidence\prompt-102a")
CSS = Path(r"C:\Projetos\lojadepaes\frontend\src\admin\admin.css").read_text(encoding="utf-8")
AGENDA = CSS[CSS.index(".admin-agenda{") :]
BEFORE = AGENDA.replace(
    ".admin-agenda{box-sizing:border-box;width:min(1100px,100%);margin:0 auto 18px;padding:16px 20px 0;min-width:0}",
    ".admin-agenda{margin:0 0 18px;min-width:0}",
).replace(
    "@media(max-width:720px){\n  .admin-agenda{padding:12px 16px 0}\n}\n",
    "",
)

BODY = """
<section class="admin-agenda" aria-labelledby="admin-agenda-title">
  <div class="admin-agenda-head"><h2 id="admin-agenda-title">Agenda de produção</h2><button type="button">Hoje</button></div>
  <div class="admin-agenda-layout">
    <div class="admin-agenda-calendar">
      <div class="admin-agenda-nav"><button type="button">‹</button><p>outubro 2026</p><button type="button">›</button></div>
      <div class="admin-agenda-grid">
        <span>seg</span><span>ter</span><span>qua</span><span>qui</span><span>sex</span><span>sáb</span><span>dom</span>
        {days}
      </div>
      <p class="admin-agenda-legend">Pedido usa a data da fornada combinada. Solicitação pendente não é reserva.</p>
    </div>
    <div class="admin-agenda-side">
      <h3>Em aberto</h3>
      <ul class="admin-agenda-list"><li><p>LPF891F9E5D1 · cliente · 1× pão · Histórico</p><button type="button">Abrir pedido</button></li></ul>
    </div>
  </div>
</section>
<main><p>Pedidos</p></main>
"""

DAYS = "".join(
    f'<button type="button" class="admin-agenda-day{" is-today" if n == 24 else ""}">{n}</button>'
    for n in range(1, 32)
)


def page_html(css: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root{{--paper:#faf8f2;--ink:#36392e;--muted:#707064;--terra:#98533c;--line:#deddd2;--sage:#eaeee3}}
*{{box-sizing:border-box}}body{{margin:0;background:#b7b3a4}}
.admin-shell{{background:var(--paper);color:var(--ink);font-family:'Segoe UI',sans-serif;min-height:100vh}}
.admin-shell>main{{max-width:1100px;margin:0 auto;padding:28px 20px;background:#fffdf9}}
h2,h3{{font-weight:400}}
{css}
</style></head><body><div class="admin-shell">{BODY.format(days=DAYS)}</div></body></html>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    widths = (1280, 390, 320)
    with sync_playwright() as api:
        browser = api.chromium.launch()
        for label, css in (("before", BEFORE), ("after", AGENDA)):
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.set_content(page_html(css))
                box = page.locator("#admin-agenda-title").bounding_box()
                section = page.locator(".admin-agenda").bounding_box()
                side = page.locator(".admin-agenda-side").bounding_box()
                scroll = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                print(
                    label,
                    width,
                    "title_left",
                    round(box["x"], 1) if box else None,
                    "section_right_gap",
                    round(width - (section["x"] + section["width"]), 1) if section else None,
                    "side_right",
                    round(side["x"] + side["width"], 1) if side else None,
                    "horizontal_scroll",
                    scroll,
                )
                page.screenshot(path=str(OUT / f"agenda-{label}-{width}.png"), full_page=False)
                page.close()
        browser.close()


if __name__ == "__main__":
    main()
