import { formatDecimal } from "../format";

/** Situação do produto. */
export const PRODUCT_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  inactive: "Inativo",
};

/** Finalidade: o que o produto representa na operação. */
export const PRODUCT_PURPOSE_LABEL: Record<string, string> = {
  final: "Produto final",
  intermediate: "Preparo intermediário",
};

/** Como o produto chega à operação. */
export const PRODUCT_SUPPLY_MODE_LABEL: Record<string, string> = {
  produced: "Produzido na casa",
  purchased: "Comprado pronto",
  mixed: "Produzido e comprado",
  combo: "Combo de produtos",
};

/** Modalidades sem operação completa nesta fase. */
export const SUPPLY_MODES_IN_PREPARATION = ["mixed", "combo"];

export const SUPPLY_MODE_PREPARATION_NOTE =
  "Modalidade em preparação: produção, recebimento e composição ainda não estão completos nesta fase.";

export function productStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return PRODUCT_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function productPurposeLabel(purpose: string | null | undefined): string {
  if (!purpose) return "—";
  return PRODUCT_PURPOSE_LABEL[purpose] ?? "Finalidade ainda não catalogada";
}

export function isSupplyModeInPreparation(mode: string | null | undefined): boolean {
  return Boolean(mode) && SUPPLY_MODES_IN_PREPARATION.includes(mode as string);
}

/** Rótulo humano da modalidade; mixed/combo saem marcados como em preparação. */
export function productSupplyModeLabel(mode: string | null | undefined): string {
  if (!mode) return "—";
  const label = PRODUCT_SUPPLY_MODE_LABEL[mode];
  if (!label) return "Modalidade ainda não catalogada";
  return isSupplyModeInPreparation(mode) ? `${label} (em preparação)` : label;
}

export function productStatusTone(
  status: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (status === "active") return "sucesso";
  if (status === "inactive") return "neutro";
  return "info";
}

export function productSupplyModeTone(
  mode: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (isSupplyModeInPreparation(mode)) return "atencao";
  return "info";
}

/**
 * Situação da receita do produto. A API já entrega a frase pronta;
 * o cálculo local só cobre listagens antigas sem o campo.
 */
export function productRecipeStatusLabel(product: {
  recipe_status_label?: string | null;
  has_published_recipe?: boolean;
  supply_mode?: string | null;
}): string {
  const given = product.recipe_status_label?.trim();
  if (given) return given;
  if (product.supply_mode === "purchased") return "Não se aplica";
  if (isSupplyModeInPreparation(product.supply_mode)) return "Modalidade em preparação";
  return product.has_published_recipe ? "Com receita vigente" : "Sem receita vigente";
}

export function productRecipeTone(product: {
  has_published_recipe?: boolean;
  supply_mode?: string | null;
}): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (product.supply_mode === "purchased") return "neutro";
  if (isSupplyModeInPreparation(product.supply_mode)) return "atencao";
  return product.has_published_recipe ? "sucesso" : "atencao";
}

export function productFamilyLabel(
  family: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  const name = family?.display_name?.trim();
  if (!name) return "Sem família";
  return name;
}

export function productUnitLabel(
  unit: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  const name = unit?.display_name?.trim() || unit?.code?.trim();
  return name || "Não informada";
}

/** Conteúdo líquido humano; sem unidade, mostra só o número formatado. */
export function productNetContentLabel(
  value: string | null | undefined,
  unit: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  if (value == null || value === "") return "Não informado";
  const amount = formatDecimal(value);
  const symbol = unit?.code?.trim() || unit?.display_name?.trim();
  return symbol ? `${amount} ${symbol}` : amount;
}

export function productShelfLifeLabel(days: number | null | undefined): string {
  if (days == null) return "Não informada";
  if (days === 0) return "Sem prazo padrão";
  return days === 1 ? "1 dia" : `${days} dias`;
}

/** Resumo da etapa Produtos no fluxo, em linguagem de operação. */
export function productsSummarySentence(summary: {
  total?: number;
  active: number;
  produced_without_recipe: number;
  purchased: number;
  intermediate: number;
}): string {
  if ((summary.total ?? summary.active) === 0) {
    return "Nenhum produto cadastrado ainda. Cadastre o primeiro produto para iniciar esta etapa.";
  }
  const primary = `${summary.active} produto(s) ativo(s)`;
  const secondary = [
    `${summary.produced_without_recipe} produzido(s) sem receita vigente`,
    `${summary.purchased} comprado(s) pronto(s)`,
    `${summary.intermediate} preparo(s) intermediário(s)`,
  ].join(" · ");
  return `${primary}. Detalhe: ${secondary}.`;
}
