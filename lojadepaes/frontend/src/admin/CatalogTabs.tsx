type Props = { current: "products" | "recipes" };

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
    </nav>
  );
}
