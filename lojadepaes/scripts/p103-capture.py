"""Capturas isoladas do prompt 103. Não abre produção, não altera receita e não envia push."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Projetos\lojadepaes\readme\evidence\prompt-103")
CSS = Path(r"C:\Projetos\lojadepaes\frontend\src\admin\admin.css").read_text(encoding="utf-8")
ROOT = """:root{--paper:#faf8f2;--ink:#36392e;--muted:#707064;--terra:#98533c;--line:#deddd2;--sage:#eaeee3}
*{box-sizing:border-box}body{margin:0;background:#b7b3a4}
.admin-shell{background:var(--paper);color:var(--ink);font-family:'Segoe UI',sans-serif;min-height:100vh}
h1,h2,h3{font-weight:400;font-family:Georgia,serif}
"""

LONG = "Bocadillo de calamares, pimentão e maionese de açafrão com pão crocante da semana"
TITLES = [
    ("Publicada", "Destaque da semana", "Retirar destaque", LONG),
    ("Publicada", "—", "Destacar", "Sopa de tomate assado com manjericão e azeite"),
    ("Publicada", "—", "Destacar", "Sardinhas grelhadas com homus e limão"),
    ("Publicada", "—", "Destacar", "Pan con Tomate"),
]


def recipe_rows(actions_class: str) -> str:
    rows = []
    for state, feature, action, title in TITLES:
        rows.append(
            f"""<tr>
              <td data-label="Título">{title}</td>
              <td data-label="Estado"><span class="admin-recipe-pill">{state}</span></td>
              <td data-label="Destaque"><span class="admin-recipe-pill">{feature}</span></td>
              <td data-label="Ações"><div class="{actions_class}">
                <button type="button" class="admin-link">Editar</button>
                <button type="button" class="admin-secondary">{action}</button>
                <button type="button" class="admin-text">Arquivar</button>
              </div></td>
            </tr>"""
        )
    return "".join(rows)


def step(label: str, count: str, tone: str = "") -> str:
    quiet = " is-quiet" if count == "0" else ""
    return (
        f'<li><button type="button" class="admin-board-step{tone}{quiet}">'
        f'<span class="admin-board-count">{count}</span>'
        f'<span class="admin-board-label">{label}</span></button></li>'
    )


def summary() -> str:
    stages = "".join(
        [
            step("Aberto", "0", " is-open"),
            step("Aceito", "1", " is-accepted"),
            step("Pago", "2", " is-paid"),
            step("Em produção", "1", " is-in-production"),
        ]
    )
    pendings = "".join(
        [
            step("Endereço de entrega incompleto", "1").replace("admin-board-step", "admin-board-step is-live", 1),
            step("Aviso na fila de envio", "0"),
            step("Falha no aviso ao cliente", "0"),
            step("Aviso não disparado", "0"),
            step("Data ultrapassada", "0"),
            step("Adaptação em aberto", "0"),
        ]
    )
    work = "".join(
        [
            step("Aguardando no fluxo", "1"),
            step("Em processamento no fluxo", "0"),
            step("Quitados no fluxo", "3"),
            step("Falha no fluxo", "0"),
        ]
    )
    history = "".join(
        [
            step("Entregue", "4", " is-delivered"),
            step("Finalizado", "1", " is-finalized"),
            step("Cancelado", "2", " is-cancelled"),
            step("Rejeitado", "0", " is-rejected"),
        ]
    )
    finance = "".join(
        [
            step("Aguardando pagamento", "1"),
            step("Em processamento", "0"),
            step("Pagos", "6"),
            step("Falha de pagamento", "0"),
            step("Sem cobrança iniciada", "0"),
            step("Sem valor a pagar", "1"),
            step("Estornados", "0"),
            step("Estorno parcial", "0"),
            step("Estado desconhecido", "0"),
            step("Cobrança cancelada", "0"),
            step("Cancelado sem pagamento regular", "0"),
        ]
    )
    return f"""
<section class="admin-summary">
  <div class="admin-summary-head">
    <div>
      <h2>Resumo dos pedidos</h2>
      <p class="admin-ops-now"><span class="admin-board-count">4</span><span>vigentes agora <span class="admin-muted">· Atualizado 26/10/2026 18:00, horário de Brasília.</span></span></p>
    </div>
    <button type="button" class="admin-secondary">Atualizar</button>
  </div>
  <section class="admin-board admin-ops-flow">
    <h3>Fluxo operacional</h3>
    <ul class="admin-board-steps" aria-label="Etapas vigentes">{stages}</ul>
    <div class="admin-ops-exception">
      <h3>Pronto sem entrega confirmada <span class="admin-muted">entra no total vigente</span></h3>
      <ul class="admin-board-steps">{step("Pronto — aguardando confirmação de entrega", "1", " is-ready-legacy")}</ul>
    </div>
  </section>
  <section class="admin-board admin-ops-pending">
    <h3>Pendências e comunicação</h3>
    <ul class="admin-board-steps">{pendings}</ul>
  </section>
  <section class="admin-board admin-ops-workpay">
    <h3>Pagamento dos vigentes</h3>
    <ul class="admin-board-steps">{work}</ul>
    <p class="admin-muted">Soma deste recorte: 4.</p>
  </section>
  <section class="admin-board admin-ops-history">
    <div><h3>Histórico <span class="admin-muted">(7, fora do total vigente)</span></h3><ul class="admin-board-steps">{history}</ul></div>
    <div><h3>Financeiro de todo o histórico</h3><p class="admin-muted">12 pedido(s) classificados aqui.</p><ul class="admin-board-steps">{finance}</ul></div>
    <div class="admin-ops-tests"><h3>Testes fora da operação</h3><button type="button" class="admin-board-step is-live"><span class="admin-board-count">6</span><span class="admin-board-label">Testes fora da operação</span></button></div>
  </section>
  <details><summary>Critérios deste resumo</summary><p>Situação atual de todos os registros.</p></details>
</section>
"""


def recipes(actions_class: str, table_class: str) -> str:
    return f"""
<main>
  <section class="admin-page admin-recipes">
    <header class="admin-page-head">
      <div>
        <p class="admin-eyebrow">Catálogo</p>
        <h1>Receitas da semana</h1>
        <p class="admin-lead">Conteúdo editorial de uso dos pães.</p>
      </div>
      <button type="button" class="admin-primary">Nova receita</button>
    </header>
    <div class="admin-table-wrap">
      <table class="{table_class}">
        <thead><tr><th>Título</th><th>Estado</th><th>Destaque</th><th>Ações</th></tr></thead>
        <tbody>{recipe_rows(actions_class)}</tbody>
      </table>
    </div>
  </section>
</main>
"""


def products() -> str:
    return """
<main>
  <section class="admin-page">
    <header class="admin-page-head"><div><h1>Produtos</h1></div></header>
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>Foto</th><th>Nome</th><th>Estado</th><th>Vitrine</th><th>Disponibilidade</th><th>Preço</th><th>Ações</th></tr></thead>
        <tbody><tr>
          <td data-label="Foto">—</td>
          <td data-label="Nome">Focaccia</td>
          <td data-label="Estado">Publicado</td>
          <td data-label="Vitrine">Fora da vitrine</td>
          <td data-label="Disponibilidade">Disponível</td>
          <td data-label="Preço">R$ 18,00</td>
          <td data-label="Ações"><button type="button" class="admin-link">Editar</button></td>
        </tr></tbody>
      </table>
    </div>
  </section>
</main>
"""


def shell(inner: str, extra_css: str = "") -> str:
    header = """
<header class="admin-top">
  <a class="admin-brand">Loja de Pães</a>
  <nav class="admin-nav"><a>Pedidos</a><a>Produtos</a><a>Agenda</a><a>Fidelidade</a></nav>
  <div class="admin-top-account"><button type="button" class="admin-notices-toggle">Notificações neste aparelho</button></div>
</header>
"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{ROOT}{CSS}{extra_css}</style></head>
<body><div class="admin-shell">{header}{inner}</div></body></html>"""


def measure(page, width: int, label: str) -> None:
    scroll = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
    title = page.locator("h1").first.bounding_box()
    table = page.locator("table").first.bounding_box() if page.locator("table").count() else None
    row = page.locator("tbody tr").first.bounding_box() if page.locator("tbody tr").count() else None
    summary = page.locator(".admin-summary").count()
    print(
        label,
        width,
        "scroll",
        scroll,
        "summary",
        summary,
        "h1_x",
        round(title["x"], 1) if title else None,
        "table_x",
        round(table["x"], 1) if table else None,
        "row_h",
        round(row["height"], 1) if row else None,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {
        "receitas-before": shell(
            summary() + recipes("admin-actions", "admin-table"),
            ".admin-summary{width:100%;max-width:none}",
        ),
        "receitas-after": shell(recipes("admin-recipe-actions", "admin-table admin-recipes-table")),
        "pedidos": shell(summary() + "<main><section class='admin-page'><h1>Pedidos</h1></section></main>"),
        "produtos": shell(products()),
    }
    widths = (1440, 1280, 768, 390, 320)
    with sync_playwright() as api:
        browser = api.chromium.launch()
        for label, html in pages.items():
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.set_content(html)
                measure(page, width, label)
                page.screenshot(path=str(OUT / f"{label}-{width}.png"), full_page=label == "pedidos")
                page.close()
        browser.close()


if __name__ == "__main__":
    main()
