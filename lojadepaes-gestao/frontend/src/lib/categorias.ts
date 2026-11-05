/** As categorias de ingrediente (a mesma lista fixa do servidor). "Outros" é o padrão. */
export const CATEGORIAS = [
  "Farinhas",
  "Fermentos",
  "Açúcares e mel",
  "Gorduras",
  "Laticínios",
  "Ovos",
  "Sal e temperos",
  "Sementes e grãos",
  "Frutas secas e oleaginosas",
  "Chocolates e cacau",
  "Frios e embutidos",
  "Líquidos",
  "Preparos da casa",
  "Outros",
] as const;

export const CATEGORIA_PADRAO = "Outros";

export const UNIDADES_BASE: { valor: string; rotulo: string }[] = [
  { valor: "g", rotulo: "Massa (g)" },
  { valor: "ml", rotulo: "Volume (ml)" },
  { valor: "un", rotulo: "Unidade (un)" },
];
