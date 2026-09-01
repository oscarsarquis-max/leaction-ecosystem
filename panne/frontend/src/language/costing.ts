/** Vocabulário público de custos e preços (pt-BR). */

export const COSTING_KIND_LABEL: Record<string, string> = {
  planned: "previsto",
  standard: "padrão",
  actual: "realizado",
};

export const COSTING_COMPLETENESS: Record<
  string,
  { label: string; tone: "sucesso" | "atencao" | "erro" | "info"; hint: string }
> = {
  complete: {
    label: "completo",
    tone: "sucesso",
    hint: "Todos os componentes valorizados. Total definitivo para o recorte.",
  },
  partial: {
    label: "parcial",
    tone: "atencao",
    hint: "Há lacunas. O total exibido é parcial — não trate como definitivo.",
  },
  insufficient_data: {
    label: "dados insuficientes",
    tone: "erro",
    hint: "Sem base suficiente para total. Ausência não é zero.",
  },
  invalidated: {
    label: "invalidado",
    tone: "erro",
    hint: "Cálculo invalidado. Não use para decisão de preço.",
  },
};

export const COSTING_CATEGORY_LABEL: Record<string, string> = {
  ingredient: "Ingrediente",
  packaging: "Embalagem",
  labor: "Mão de obra",
  waste: "Desperdício",
  rework: "Retrabalho",
  energy: "Energia",
  other: "Outros",
};

export const COSTING_QUALITY_LABEL: Record<string, string> = {
  current_price: "Preço vigente",
  standard_cost: "Custo padrão",
  missing: "Preço ausente",
  manual_assumption: "Premissa manual",
  operational_fact: "Fato operacional",
};

export const COSTING_GAP_LABEL: Record<string, string> = {
  preco_ausente: "Preço ausente",
  rendimento_ausente: "Rendimento vendável ausente",
  unidade_incompativel: "Unidade incompatível",
  conversao_massa_volume_proibida: "Conversão massa/volume proibida",
  moeda_incompativel: "Moeda incompatível",
};

export function costingKindLabel(kind: string | null | undefined): string {
  if (!kind) return "—";
  return COSTING_KIND_LABEL[kind] ?? kind;
}

export function costingCompleteness(code: string | null | undefined) {
  return (
    COSTING_COMPLETENESS[code ?? ""] ?? {
      label: code || "—",
      tone: "info" as const,
      hint: "Situação ainda não catalogada.",
    }
  );
}

export function categoryLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return COSTING_CATEGORY_LABEL[code] ?? code;
}

export function qualityLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return COSTING_QUALITY_LABEL[code] ?? code;
}

export function gapTitle(code: string | null | undefined): string {
  if (!code) return "Lacuna";
  return COSTING_GAP_LABEL[code] ?? code.replaceAll("_", " ");
}

export function formatMarkupFactor(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(String(value).replace(",", "."));
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}×`;
}

export function formatPercentDisplay(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(String(value).replace(",", "."));
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })} %`;
}

export const PRACTICED_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  approved: "Aprovado",
  draft: "Rascunho",
  published: "Publicado",
  inactive: "Inativo",
  superseded: "Substituído",
};

export function practicedStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return PRACTICED_STATUS_LABEL[status] ?? status;
}

export const CHANNEL_LABEL: Record<string, string> = {
  own_counter: "Balcão próprio",
  wholesale: "Atacado",
  delivery: "Entrega",
  own_delivery: "Entrega própria",
  made_to_order: "Encomenda",
  marketplace: "Praça eletrônica",
  other: "Outro",
};

export function channelLabel(channel: string | null | undefined): string {
  if (!channel) return "—";
  return CHANNEL_LABEL[channel] ?? channel;
}

export const SIMULATION_KIND_LABEL: Record<string, string> = {
  markup_factor: "Markup por fator",
  gross_margin: "Margem bruta alvo",
  contribution_margin: "Margem de contribuição alvo",
  reverse: "Reversa a partir do preço",
};

export function simulationKindLabel(kind: string | null | undefined): string {
  if (!kind) return "—";
  return SIMULATION_KIND_LABEL[kind] ?? kind;
}

export const PRICE_CRITERION_LABEL: Record<string, string> = {
  latest_observed: "Último preço observado",
  preferred_supplier: "Fornecedor preferencial",
  lowest_available: "Menor preço disponível",
};

export function priceCriterionLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return PRICE_CRITERION_LABEL[code] ?? code;
}

/** Semântica previsto × realizado por tipo de métrica. */
export type VarianceMetric = "cost" | "yield";

export function varianceSignal(
  metric: VarianceMetric,
  planned: string | number | null | undefined,
  actual: string | number | null | undefined,
): { delta: number | null; label: "favorável" | "desfavorável" | "neutro" | null } {
  if (planned == null || actual == null || planned === "" || actual === "") {
    return { delta: null, label: null };
  }
  const p = Number(String(planned).replace(",", "."));
  const a = Number(String(actual).replace(",", "."));
  if (!Number.isFinite(p) || !Number.isFinite(a)) return { delta: null, label: null };
  const delta = a - p;
  if (Math.abs(delta) < 1e-9) return { delta: 0, label: "neutro" };
  if (metric === "yield") {
    return { delta, label: delta > 0 ? "favorável" : "desfavorável" };
  }
  return { delta, label: delta < 0 ? "favorável" : "desfavorável" };
}

export function isPurchasedCalc(item: {
  subject?: { supply_mode?: string | null; product_display_name?: string | null } | null;
  cost_scope?: { mode?: string } | null;
}): boolean {
  if (item.cost_scope?.mode === "purchased") return true;
  if (item.subject?.supply_mode === "purchased") return true;
  const name = item.subject?.product_display_name ?? "";
  return /comprado/i.test(name);
}

/** Modalidade na superfície (nunca o enum técnico). */
export function supplyModeSurfaceLabel(mode: string | null | undefined): string {
  if (mode === "purchased") return "Comprado";
  if (mode === "produced") return "Produzido";
  if (mode === "mixed") return "Produzido e comprado";
  if (mode === "combo") return "Combo";
  if (!mode) return "—";
  return mode;
}

export function productComparisonScope(item: {
  completeness?: string;
  subject?: { supply_mode?: string | null; product_display_name?: string | null } | null;
  cost_scope?: {
    mode?: string;
    comparison_scope_label?: string;
    ingredients_complete?: boolean;
  } | null;
}): string {
  if (item.cost_scope?.comparison_scope_label) return item.cost_scope.comparison_scope_label;
  if (isPurchasedCalc(item)) return "Mercadoria comprada";
  if (item.completeness === "partial" || item.cost_scope?.ingredients_complete === false) {
    return "Ingredientes parciais";
  }
  return "Ingredientes — demais custos de produção não configurados";
}

/** Enums técnicos que não podem aparecer na superfície da área de custos. */
export const COSTING_SURFACE_FORBIDDEN_ENUMS =
  /\b(purchased|produced|mixed|combo|active|inactive|ingredient|packaging|labor|energy|current_price|standard_cost|missing|own_counter|wholesale|markup_factor|gross_margin|contribution_margin|latest_observed|sellable_unit|batch_total|produced_unit|insufficient_data)\b/i;

export function assertCostingSurfaceLanguage(surface: string): void {
  const match = surface.match(COSTING_SURFACE_FORBIDDEN_ENUMS);
  if (match) {
    throw new Error(`Enum técnico vazou na superfície de custos: "${match[0]}"`);
  }
}
