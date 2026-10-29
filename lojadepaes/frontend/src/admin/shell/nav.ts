export type NavItem = {
  id: string;
  label: string;
  href?: string;
  soon?: boolean;
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Operação",
    items: [{ id: "pedidos", label: "Pedidos", href: "/admin/pedidos" }],
  },
  {
    label: "Produção",
    items: [{ id: "agenda", label: "Dias, tetos e fechamentos", href: "/admin/agenda" }],
  },
  {
    label: "Catálogo",
    items: [
      { id: "produtos", label: "Produtos", href: "/admin/produtos" },
      { id: "receitas", label: "Receitas da semana", href: "/admin/produtos/receitas" },
    ],
  },
  {
    label: "Conteúdo",
    items: [
      { id: "gigio", label: "Gigio", href: "/admin/produtos/gigio" },
      { id: "harmonizacoes", label: "Harmonizações", href: "/admin/produtos/gigio/harmonizacoes" },
      { id: "complementos", label: "Complementos", href: "/admin/produtos/complementos" },
    ],
  },
  {
    label: "Clientes",
    items: [{ id: "fidelidade", label: "Fidelidade", href: "/admin/fidelidade" }],
  },
  {
    label: "Marketplace",
    items: [
      { id: "parceiros", label: "Parceiros", soon: true },
      { id: "repasses", label: "Repasses", soon: true },
    ],
  },
];

export function activeNavId(path: string): string | null {
  const current = path.replace(/\/+$/, "") || "/";
  if (current === "/admin" || current.startsWith("/admin/pedidos")) {
    return "pedidos";
  }
  if (current.startsWith("/admin/agenda")) {
    return "agenda";
  }
  if (current.startsWith("/admin/produtos/receitas")) {
    return "receitas";
  }
  if (current.startsWith("/admin/produtos/gigio/harmonizacoes")) {
    return "harmonizacoes";
  }
  if (current.startsWith("/admin/produtos/gigio")) {
    return "gigio";
  }
  if (current.startsWith("/admin/produtos/complementos")) {
    return "complementos";
  }
  if (current.startsWith("/admin/produtos")) {
    return "produtos";
  }
  if (current.startsWith("/admin/fidelidade")) {
    return "fidelidade";
  }
  return null;
}

export function trailFor(path: string): { group: string; page: string } {
  const id = activeNavId(path);
  for (const group of NAV_GROUPS) {
    const item = group.items.find((entry) => entry.id === id);
    if (item) {
      return { group: group.label, page: item.label };
    }
  }
  return { group: "Operação", page: "Pedidos" };
}
