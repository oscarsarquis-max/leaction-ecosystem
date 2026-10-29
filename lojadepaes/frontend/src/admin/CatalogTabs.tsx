type Props = { current: "products" | "recipes" | "gigio" | "pairings" | "accompaniments" };

export function CatalogTabs({ current }: Props) {
  return (
    <nav className="admin-subnav" aria-label="Áreas de produtos">
      <a
        href="/admin/produtos"
        className={current === "products" ? "is-current" : undefined}
        aria-current={current === "products" ? "page" : undefined}
      >
        Vitrine e cadastro
      </a>
      <a
        href="/admin/produtos/receitas"
        className={current === "recipes" ? "is-current" : undefined}
        aria-current={current === "recipes" ? "page" : undefined}
      >
        Receitas da semana
      </a>
      <a
        href="/admin/produtos/gigio"
        className={current === "gigio" ? "is-current" : undefined}
        aria-current={current === "gigio" ? "page" : undefined}
      >
        Gigio
      </a>
      <a
        href="/admin/produtos/gigio/harmonizacoes"
        className={current === "pairings" ? "is-current" : undefined}
        aria-current={current === "pairings" ? "page" : undefined}
      >
        Harmonizações
      </a>
      <a
        href="/admin/produtos/complementos"
        className={current === "accompaniments" ? "is-current" : undefined}
        aria-current={current === "accompaniments" ? "page" : undefined}
      >
        Complementos
      </a>
    </nav>
  );
}
