"""Capturas isoladas do adendo 103A. Não abre produção e não altera pedido."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\lojadepaes\readme\evidence\prompt-103a")
CSS = Path(r"C:\Projetos\lojadepaes\frontend\src\admin\admin.css").read_text(encoding="utf-8")
ROOT = """:root{--paper:#faf8f2;--ink:#36392e;--muted:#707064;--terra:#98533c;--line:#deddd2;--sage:#eaeee3}
*{box-sizing:border-box}body{margin:0;background:#b7b3a4}
.admin-shell{background:var(--paper);color:var(--ink);font-family:'Segoe UI',sans-serif;min-height:100vh}
h1,h2,h3{font-weight:400;font-family:Georgia,serif}
"""

NODE = """
<div class="admin-cycle-stop">
  <button type="button" class="admin-cycle-step {tone}" aria-pressed="false">
    <span class="admin-cycle-dot">{count}</span>
    <span class="admin-cycle-name">{label}{caption}</span>
  </button>
</div>
"""


def cycle(history_open: bool) -> str:
    nodes = [
        ("is-open", "4", "Aberto", ""),
        ("is-accepted", "0", "Aceito", ""),
        ("is-paid", "2", "Pago", ""),
        ("is-in-production", "3", "Em produção", ""),
        ("is-delivered", "11", "Entregue", "<small>No histórico</small>"),
    ]
    track = "".join(
        NODE.format(tone=tone, count=count, label=label, caption=caption)
        for tone, count, label, caption in nodes
    )
    history = ""
    if history_open:
        history = """
        <div id="admin-history-detail" class="admin-cycle-detail">
          <h3>Histórico</h3>
          <div class="admin-cycle-lines">
            <button type="button" class="admin-cycle-line is-delivered"><span>Entregue</span><span class="admin-cycle-line-count">11</span></button>
            <button type="button" class="admin-cycle-line is-finalized"><span>Finalizado</span><span class="admin-cycle-line-count">2</span></button>
            <button type="button" class="admin-cycle-line is-cancelled"><span>Cancelado</span><span class="admin-cycle-line-count">1</span></button>
            <button type="button" class="admin-cycle-line is-rejected is-quiet"><span>Rejeitado</span><span class="admin-cycle-line-count">0</span></button>
          </div>
          <h3>Financeiro de todo o histórico</h3>
          <p class="admin-muted">18 pedido(s) classificados aqui.</p>
        </div>
        """
    chevron = "▴" if history_open else "▾"
    expanded = "true" if history_open else "false"
    return f"""
    <section class="admin-summary">
      <div class="admin-summary-head">
        <div>
          <h2>Ciclo dos pedidos</h2>
          <p class="admin-ops-now"><span class="admin-board-count">10</span><span>vigentes agora <span class="admin-muted">· Atualizado 26/10/2026 18:30, horário de Brasília.</span></span></p>
        </div>
        <button type="button" class="admin-secondary">Atualizar</button>
      </div>
      <div class="admin-cycle-track" aria-label="Etapas do pedido">{track}</div>
      <button type="button" class="admin-cycle-ready"><span>Pronto — aguardando confirmação de entrega</span><span class="admin-cycle-line-count">1</span></button>
      <div class="admin-cycle-support">
        <button type="button" class="admin-cycle-toggle" aria-expanded="false">Pendências ▾</button>
        <button type="button" class="admin-cycle-toggle" aria-expanded="false">Pagamentos dos ativos ▾</button>
      </div>
    </section>
    <main>
      <h1>Pedidos</h1>
      <table class="admin-table admin-orders-table"><thead><tr><th>Cliente</th><th>Etapa</th></tr></thead>
      <tbody><tr><td>Forno da manhã</td><td>Aberto</td></tr><tr><td>Encomenda de sábado</td><td>Pago</td></tr></tbody></table>
      <section class="admin-cycle-history">
        <button type="button" class="admin-cycle-history-toggle" aria-expanded="{expanded}">Consultar histórico {chevron}</button>
        {history}
      </section>
    </main>
    """


def page_html(history_open: bool) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{ROOT}{CSS}</style></head><body><div class='admin-shell'>{cycle(history_open)}</div></body></html>"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    widths = [1440, 1280, 390, 320]
    with sync_playwright() as play:
        browser = play.chromium.launch()
        for width in widths:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.set_content(page_html(False), wait_until="networkidle")
            metrics = page.evaluate(
                """() => {
                  const shell = document.querySelector('.admin-shell');
                  const dots = [...document.querySelectorAll('.admin-cycle-dot')].map(el => {
                    const box = el.getBoundingClientRect();
                    return {w: Math.round(box.width), h: Math.round(box.height)};
                  });
                  const track = getComputedStyle(document.querySelector('.admin-cycle-track'));
                  const list = document.querySelector('h1').getBoundingClientRect().top;
                  const history = document.querySelector('.admin-cycle-history').getBoundingClientRect().top;
                  return {
                    scroll: shell.scrollWidth > shell.clientWidth + 1,
                    dots,
                    display: track.display,
                    direction: track.flexDirection,
                    listBeforeHistory: list < history,
                    historyText: document.getElementById('admin-history-detail') === null
                  };
                }"""
            )
            page.screenshot(path=str(OUT / f"ciclo-{width}.png"), full_page=True)
            print(width, metrics)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_content(page_html(True), wait_until="networkidle")
        page.screenshot(path=str(OUT / "historico-1440.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
