export type NavItem = {
  id: string;
  label: string;
  href?: string;
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

// Só "Hoje" funciona nesta etapa. Os demais aparecem como "em breve" (sem link).
export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Dia a dia",
    items: [{ id: "hoje", label: "Hoje", href: "/" }],
  },
  {
    label: "Cadastro",
    items: [
      { id: "estoque", label: "Estoque" },
      { id: "ingredientes", label: "Ingredientes" },
      { id: "receitas", label: "Receitas" },
    ],
  },
  {
    label: "Produção e custo",
    items: [
      { id: "producao", label: "Produção" },
      { id: "custos", label: "Custos" },
    ],
  },
];

export function activeNavId(_path: string): string {
  return "hoje";
}

export function trailFor(path: string): { group: string; page: string } {
  const id = activeNavId(path);
  for (const group of NAV_GROUPS) {
    const item = group.items.find((entry) => entry.id === id);
    if (item) {
      return { group: group.label, page: item.label };
    }
  }
  return { group: "Dia a dia", page: "Hoje" };
}
